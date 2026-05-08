import traci

from agents.base_agent import BaseAgent
from coordination.green_wave import GreenWaveCoordinator
from learning.qlearning_tls import QLearningTLS
from routing.contract_net import ContractNet


class IntersectionAgent(BaseAgent):
    def __init__(self, tls_id, message_bus=None, coordinator=None, neighbors=None):
        super().__init__(f"intersection:{tls_id}", message_bus)
        self.tls_id = tls_id
        self.lanes = self.get_controlled_lanes()
        self.qlearn = QLearningTLS()
        self.contract_net = ContractNet()
        self.coordinator = coordinator or GreenWaveCoordinator()
        self.neighbor_ids = neighbors or []
        self.previous_state = None
        self.previous_action = None
        self.last_switch_step = -999
        self.last_selected_phase = None
        self.pending_proposals = {}
        self.phase_plan = self._build_phase_plan()
        self.desires = ["reduce_waiting_time", "maximize_flow", "coordinate_neighbors"]

        for neighbor_id in self.neighbor_ids:
            self.coordinator.register_neighbor(self.tls_id, neighbor_id)

    def get_controlled_lanes(self):
        lanes = set()
        for link_group in traci.trafficlight.getControlledLinks(self.tls_id):
            for link in link_group:
                if link:
                    lanes.add(link[0])
        return sorted(lanes)

    def count_vehicles(self):
        return {lane: traci.lane.getLastStepVehicleNumber(lane) for lane in self.lanes}

    def count_halted_vehicles(self):
        return {lane: traci.lane.getLastStepHaltingNumber(lane) for lane in self.lanes}

    def get_queue_length(self):
        return sum(traci.lane.getLastStepHaltingNumber(lane) for lane in self.lanes)

    def compute_congestion(self, counts):
        return sum(counts.values())

    def congestion_level(self, congestion):
        if congestion < 3:
            return "LOW"
        if congestion < 10:
            return "MEDIUM"
        return "HIGH"

    def decide_phase_duration(self, congestion):
        state = self.qlearn.get_state(congestion)
        action = self.qlearn.choose_action(state)
        if self.previous_state is not None:
            reward = -congestion
            self.qlearn.update(self.previous_state, self.previous_action, reward, state)
        self.previous_state = state
        self.previous_action = action
        return {
            0: 8,
            1: 10,
            2: 12,
            3: 15,
            4: 18,
            5: 22,
            6: 28,
            7: 35,
            8: 45,
        }.get(action, 15)

    def update_beliefs(self):
        counts = self.count_vehicles()
        halted_counts = self.count_halted_vehicles()
        queue_length = self.get_queue_length()
        current_phase = traci.trafficlight.getPhase(self.tls_id)
        messages = self.receive_acl()
        self.pending_proposals = {}
        priority_requests = []
        neighbor_alerts = []

        for message in messages:
            if message.performative == "cfp":
                self.send_acl(
                    message.sender,
                    "propose",
                    {
                        "intersection": self.tls_id,
                        **self.contract_net.make_proposal(queue_length),
                    },
                )
            elif message.performative == "propose":
                self.pending_proposals[message.sender] = message.content
            elif message.performative == "request":
                priority_requests.append(message.content)
            elif message.performative == "inform":
                neighbor_alerts.append(message.content)

        congestion = self.compute_congestion(counts)
        congestion_level = self.congestion_level(congestion)
        self.coordinator.record_congestion(self.tls_id, congestion_level)
        self.beliefs = {
            "lane_counts": counts,
            "halted_counts": halted_counts,
            "queue_length": queue_length,
            "congestion": congestion,
            "congestion_level": congestion_level,
            "messages": messages,
            "priority_requests": priority_requests,
            "neighbor_alerts": neighbor_alerts,
            "current_phase": current_phase,
        }

    def deliberate(self):
        congestion = self.beliefs["congestion"]
        duration = self.decide_phase_duration(congestion)
        priority_neighbor = None
        if self.neighbor_ids:
            self.contract_net.call_for_proposal(self, self._neighbor_proxies())
            priority_neighbor = self.contract_net.select_winner(self.pending_proposals)

        phase_scores = self._score_candidate_phases()
        target_phase = max(phase_scores, key=phase_scores.get) if phase_scores else self.beliefs["current_phase"]
        neighbor_alert_weight = sum(
            2 if alert.get("congestion_level") == "HIGH" else 1
            for alert in self.beliefs["neighbor_alerts"]
        )

        if self.beliefs["priority_requests"]:
            target_phase = self._priority_phase(target_phase)
            duration = max(duration, 24)
        elif self.beliefs["congestion_level"] == "HIGH":
            duration = max(duration, 20)
        if priority_neighbor or neighbor_alert_weight:
            duration = min(50, duration + neighbor_alert_weight + (2 if priority_neighbor else 0))

        self.intentions = [{
            "phase_duration": max(8, min(50, duration)),
            "priority_neighbor": priority_neighbor,
            "inform_level": self.beliefs["congestion_level"],
            "target_phase": target_phase,
            "phase_scores": phase_scores,
        }]

    def act(self):
        intention = self.intentions[0]
        selected_plan = self.phase_plan.get(intention["target_phase"], {})
        self.apply_phase_decision(intention["target_phase"], intention["phase_duration"])
        self.coordinator.record_decision(
            self.tls_id,
            intention["target_phase"],
            selected_plan.get("green_lanes", []),
        )
        self.broadcast_congestion(intention["inform_level"])
        self.broadcast_neighbor_status(intention["inform_level"], intention["phase_duration"])

    def apply_phase_decision(self, target_phase, duration):
        current_step = int(traci.simulation.getTime())
        current_phase = traci.trafficlight.getPhase(self.tls_id)
        if target_phase is not None and current_phase != target_phase:
            if current_step - self.last_switch_step >= 8:
                traci.trafficlight.setPhase(self.tls_id, target_phase)
                self.last_switch_step = current_step
                self.last_selected_phase = target_phase
                print(f"[TLS {self.tls_id}] bascule intelligente vers phase {target_phase}")
        traci.trafficlight.setPhaseDuration(self.tls_id, duration)

    def broadcast_congestion(self, level):
        for vehicle_id in traci.vehicle.getIDList():
            lane_id = traci.vehicle.getLaneID(vehicle_id)
            if lane_id in self.lanes:
                self.send_acl(
                    f"vehicle:{vehicle_id}",
                    "inform",
                    {
                        "intersection": self.tls_id,
                        "congestion_level": level,
                        "queue_length": self.beliefs["queue_length"],
                    },
                )

    def broadcast_neighbor_status(self, level, duration):
        target_phase = self.intentions[0]["target_phase"] if self.intentions else None
        preferred_lanes = self.phase_plan.get(target_phase, {}).get("green_lanes", [])
        for neighbor_id in self.neighbor_ids:
            self.send_acl(
                f"intersection:{neighbor_id}",
                "inform",
                {
                    "intersection": self.tls_id,
                    "congestion_level": level,
                    "queue_length": self.beliefs["queue_length"],
                    "suggested_duration": duration,
                    "target_phase": target_phase,
                    "preferred_lanes": preferred_lanes,
                },
            )

    def _build_phase_plan(self):
        controlled_links = traci.trafficlight.getControlledLinks(self.tls_id)
        program = traci.trafficlight.getAllProgramLogics(self.tls_id)[0]
        phase_plan = {}
        for phase_index, phase in enumerate(program.phases):
            state = phase.state
            if "y" in state.lower():
                continue
            green_lanes = set()
            exit_lanes = set()
            for signal_index, signal_state in enumerate(state):
                if signal_state not in ("G", "g"):
                    continue
                if signal_index >= len(controlled_links):
                    continue
                for link in controlled_links[signal_index]:
                    if not link:
                        continue
                    green_lanes.add(link[0])
                    if len(link) > 1 and link[1]:
                        exit_lanes.add(link[1])
            if green_lanes:
                phase_plan[phase_index] = {
                    "green_lanes": sorted(green_lanes),
                    "exit_lanes": sorted(exit_lanes),
                    "state": state,
                }
        return phase_plan

    def _score_candidate_phases(self):
        halted = self.beliefs["halted_counts"]
        counts = self.beliefs["lane_counts"]
        current_phase = self.beliefs["current_phase"]
        scores = {}
        neighbor_pressure = self.coordinator.neighbor_pressure(self.tls_id)
        high_neighbor_alerts = [
            alert for alert in self.beliefs["neighbor_alerts"]
            if alert.get("congestion_level") == "HIGH"
        ]

        for phase_index, plan in self.phase_plan.items():
            green_lanes = plan["green_lanes"]
            local_pressure = sum((halted.get(lane, 0) * 2.5) + counts.get(lane, 0) for lane in green_lanes)
            downstream_relief = 0.0
            for lane in plan["exit_lanes"]:
                try:
                    downstream_relief += max(0.0, 8.0 - traci.lane.getLastStepVehicleNumber(lane)) * 0.25
                except traci.TraCIException:
                    continue
            coordination_bonus = self.coordinator.coordination_bonus(self.tls_id, green_lanes)
            alert_bonus = 0.0
            for alert in high_neighbor_alerts:
                preferred_lanes = set(alert.get("preferred_lanes", []))
                if preferred_lanes.intersection(green_lanes):
                    alert_bonus += 1.5
                else:
                    alert_bonus += 0.3
            stay_bonus = 1.2 if phase_index == current_phase else 0.0
            scores[phase_index] = local_pressure + downstream_relief + coordination_bonus + alert_bonus + stay_bonus + neighbor_pressure
        return scores

    def _priority_phase(self, fallback_phase):
        best_phase = fallback_phase
        best_score = -1.0
        priority_lanes = []
        for request in self.beliefs["priority_requests"]:
            lane_id = request.get("lane_id")
            if lane_id:
                priority_lanes.append(lane_id)

        if not priority_lanes:
            return fallback_phase

        for phase_index, plan in self.phase_plan.items():
            green_lanes = plan["green_lanes"]
            score = sum(1 for lane in priority_lanes if lane in green_lanes)
            if score > best_score:
                best_score = score
                best_phase = phase_index
        return best_phase

    def _neighbor_proxies(self):
        return [_NeighborProxy(neighbor_id) for neighbor_id in self.neighbor_ids]


class _NeighborProxy:
    def __init__(self, tls_id):
        self.id = f"intersection:{tls_id}"
        self.tls_id = tls_id

    def get_queue_length(self):
        lanes = traci.trafficlight.getControlledLanes(self.tls_id)
        return sum(traci.lane.getLastStepHaltingNumber(lane) for lane in lanes)
