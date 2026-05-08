import traci

from agents.base_agent import BaseAgent


class CrisisAgent(BaseAgent):
    def __init__(self, message_bus=None):
        super().__init__("crisis_manager", message_bus)
        self.priority_types = {"ambulance", "bus", "sotra_bus"}
        self.desires = ["prioritize_emergency_traffic"]

    def update_beliefs(self):
        priority_vehicle = None
        for vehicle_id in traci.vehicle.getIDList():
            if traci.vehicle.getTypeID(vehicle_id) in self.priority_types:
                priority_vehicle = vehicle_id
                break
        self.beliefs = {"priority_vehicle": priority_vehicle}

    def deliberate(self):
        self.intentions = ["green_wave"] if self.beliefs["priority_vehicle"] else ["idle"]

    def act(self):
        vehicle_id = self.beliefs["priority_vehicle"]
        if not vehicle_id:
            return

        vehicle_lane = traci.vehicle.getLaneID(vehicle_id)
        for tls_id in traci.trafficlight.getIDList():
            controlled_lanes = traci.trafficlight.getControlledLanes(tls_id)
            if vehicle_lane in controlled_lanes:
                self.send_acl(
                    f"intersection:{tls_id}",
                    "request",
                    {
                        "reason": "priority_vehicle",
                        "vehicle_id": vehicle_id,
                        "lane_id": vehicle_lane,
                    },
                )
