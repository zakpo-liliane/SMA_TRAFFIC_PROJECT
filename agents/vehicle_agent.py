import traci

from agents.base_agent import BaseAgent
from routing.dynamic_routing import DynamicRouter


class VehicleAgent(BaseAgent):
    def __init__(self, vehicle_id, message_bus=None):
        super().__init__(f"vehicle:{vehicle_id}", message_bus)
        self.vehicle_id = vehicle_id
        self.router = DynamicRouter()
        self.congestion_threshold = 10
        self.destination_edge = None
        self.initial_route_planned = False
        self.desires = ["reach_destination", "avoid_congestion"]

    def is_active(self):
        return self.vehicle_id in traci.vehicle.getIDList()

    def update_beliefs(self):
        if not self.is_active():
            self.beliefs = {"active": False}
            return

        messages = self.receive_acl()
        self.beliefs = {
            "active": True,
            "edge": traci.vehicle.getRoadID(self.vehicle_id),
            "lane": traci.vehicle.getLaneID(self.vehicle_id),
            "waiting_time": traci.vehicle.getWaitingTime(self.vehicle_id),
            "speed": traci.vehicle.getSpeed(self.vehicle_id),
            "edge_vehicle_count": 0,
            "received_messages": messages,
            "reroute_requested": False,
            "speed_action": "maintain",
        }

        route = traci.vehicle.getRoute(self.vehicle_id)
        if route:
            self.destination_edge = route[-1]
            self.beliefs["destination_edge"] = self.destination_edge

        edge = self.beliefs["edge"]
        if edge and not edge.startswith(":"):
            self.beliefs["edge_vehicle_count"] = traci.edge.getLastStepVehicleNumber(edge)

        for message in messages:
            if message.performative == "inform":
                if message.content.get("congestion_level") == "HIGH":
                    self.beliefs["reroute_requested"] = True
                    self.beliefs["speed_action"] = "brake"
                elif message.content.get("congestion_level") == "LOW":
                    self.beliefs["speed_action"] = "accelerate"

    def deliberate(self):
        if not self.beliefs.get("active"):
            self.intentions = ["idle"]
            return

        if not self.initial_route_planned and self.destination_edge:
            self.intentions = ["plan_route"]
            return

        should_reroute = (
            self.beliefs["reroute_requested"]
            or self.beliefs["edge_vehicle_count"] > self.congestion_threshold
        )
        if should_reroute:
            self.intentions = ["reroute"]
        elif self.beliefs["speed_action"] == "brake" or self.beliefs["waiting_time"] > 5:
            self.intentions = ["brake"]
        elif self.beliefs["speed_action"] == "accelerate":
            self.intentions = ["accelerate"]
        else:
            self.intentions = ["continue"]

    def act(self):
        if not self.beliefs.get("active"):
            return
        if not self.intentions:
            return

        action = self.intentions[0]
        if action == "plan_route" and self.destination_edge:
            self.router.set_shortest_path(self.vehicle_id, self.destination_edge)
            self.initial_route_planned = True
        elif action == "reroute":
            self.router.reroute_vehicle(self.vehicle_id, self.destination_edge)
            self._apply_speed("brake")
        elif action == "brake":
            self._apply_speed("brake")
        elif action == "accelerate":
            self._apply_speed("accelerate")

    def _apply_speed(self, mode):
        try:
            current_speed = traci.vehicle.getSpeed(self.vehicle_id)
            allowed_speed = traci.vehicle.getAllowedSpeed(self.vehicle_id)
            if mode == "accelerate":
                target_speed = min(allowed_speed, max(current_speed + 2.0, 5.0))
                traci.vehicle.slowDown(self.vehicle_id, target_speed, 3)
            elif mode == "brake":
                target_speed = max(1.0, current_speed * 0.5)
                traci.vehicle.slowDown(self.vehicle_id, target_speed, 3)
        except traci.TraCIException:
            return
