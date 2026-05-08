import os

import traci

from agents.crisis_agent import CrisisAgent
from agents.intersection_agent import IntersectionAgent
from agents.vehicle_agent import VehicleAgent
from communication.message_bus import MessageBus
from coordination.green_wave import GreenWaveCoordinator
from database.postgres_logger import PostgresLogger
from metrics.performance_monitor import PerformanceMonitor
from scenarios.abidjan_peak import PeakTrafficScenario
from scenarios.incident_pont_de_gaulle import IncidentPontDeGaulleScenario


class SimulationManager:
    def __init__(self, use_gui=False, max_steps=300):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.sumo_config = os.path.join(base_dir, "sumo", "abidjan.sumocfg")
        self.gui_settings = os.path.join(base_dir, "sumo", "abidjan.gui.xml")
        self.use_gui = use_gui
        self.max_steps = max_steps

        os.makedirs("logs", exist_ok=True)

        self.message_bus = MessageBus()
        self.coordinator = GreenWaveCoordinator()
        self.monitor = PerformanceMonitor()
        self.logger = PostgresLogger()

        self.intersections = []
        self.vehicles = {}
        self.crisis = CrisisAgent(self.message_bus)
        self.scenarios = [
            PeakTrafficScenario(),
            IncidentPontDeGaulleScenario(),
        ]
        self._logged_message_count = 0

    def start(self):
        binary = "sumo-gui" if self.use_gui else "sumo"
        sumo_cmd = [binary, "-c", self.sumo_config, "--log", "logs/sumo.log"]
        if self.use_gui:
            sumo_cmd.extend(["-g", self.gui_settings])
        traci.start(sumo_cmd)

        tls_ids = list(traci.trafficlight.getIDList())
        neighbor_map = self._build_neighbor_map(tls_ids)

        for tls_id in tls_ids:
            self.intersections.append(
                IntersectionAgent(
                    tls_id,
                    message_bus=self.message_bus,
                    coordinator=self.coordinator,
                    neighbors=neighbor_map.get(tls_id, []),
                )
            )

    def run(self):
        step = 0
        while step < self.max_steps and traci.simulation.getMinExpectedNumber() > 0:
            for scenario in self.scenarios:
                event = scenario.apply(step)
                if event:
                    self.logger.log_event(step, event["type"], event)

            self._register_new_vehicle_agents()

            for intersection in self.intersections:
                intersection.step()

            for vehicle_id, agent in list(self.vehicles.items()):
                if agent.is_active():
                    agent.step()
                else:
                    self.vehicles.pop(vehicle_id, None)

            self.crisis.step()
            self.monitor.collect_step(step, self.intersections, self.message_bus)
            self._log_new_messages()
            self._log_latest_metrics(step)
            self._log_agent_states(step)

            traci.simulationStep()
            step += 1

        traci.close()
        self.logger.close()
        self.monitor.save_csv("simulation.csv")

    def _register_new_vehicle_agents(self):
        for vehicle_id in traci.vehicle.getIDList():
            if vehicle_id not in self.vehicles:
                self.vehicles[vehicle_id] = VehicleAgent(vehicle_id, self.message_bus)

    def _build_neighbor_map(self, tls_ids):
        neighbor_map = {tls_id: [] for tls_id in tls_ids}
        positions = {tls_id: traci.junction.getPosition(tls_id) for tls_id in tls_ids}
        for tls_id in tls_ids:
            distances = []
            x1, y1 = positions[tls_id]
            for other_tls in tls_ids:
                if other_tls == tls_id:
                    continue
                x2, y2 = positions[other_tls]
                distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
                distances.append((distance, other_tls))
            distances.sort(key=lambda item: item[0])
            neighbor_map[tls_id] = [other_tls for _, other_tls in distances[:2]]
        return neighbor_map

    def _log_latest_metrics(self, step):
        if not self.monitor.rows:
            return

        latest = self.monitor.rows[-1]
        self.logger.log_metrics(
            step=step,
            vehicle_count=latest["vehicles_in_network"],
            avg_wait=latest["avg_waiting_time"],
            avg_queue=latest["avg_queue_length"],
            avg_trip_time=latest["avg_trip_time"],
            messages_exchanged=latest["messages_exchanged"],
        )

    def _log_new_messages(self):
        while self._logged_message_count < len(self.message_bus.history):
            message = self.message_bus.history[self._logged_message_count]
            self.logger.log_message(
                sender=message.sender,
                receiver=message.receiver,
                performative=message.performative,
                content=message.content,
            )
            self._logged_message_count += 1

    def _log_agent_states(self, step):
        for intersection in self.intersections:
            self.logger.log_agent_state(
                step,
                intersection.id,
                "intersection",
                {
                    "tls_id": intersection.tls_id,
                    "queue_length": intersection.beliefs.get("queue_length", 0),
                    "congestion": intersection.beliefs.get("congestion", 0),
                    "target_phase": intersection.intentions[0]["target_phase"] if intersection.intentions else None,
                    "phase_duration": intersection.intentions[0]["phase_duration"] if intersection.intentions else None,
                },
            )

        for vehicle_id, agent in list(self.vehicles.items())[:20]:
            self.logger.log_agent_state(
                step,
                agent.id,
                "vehicle",
                {
                    "vehicle_id": vehicle_id,
                    "edge": agent.beliefs.get("edge"),
                    "destination_edge": agent.destination_edge,
                    "waiting_time": agent.beliefs.get("waiting_time", 0),
                    "intention": agent.intentions[0] if agent.intentions else None,
                },
            )

        self.logger.log_agent_state(
            step,
            self.crisis.id,
            "crisis",
            {
                "priority_vehicle": self.crisis.beliefs.get("priority_vehicle"),
            },
        )
