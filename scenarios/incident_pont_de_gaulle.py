import traci


class IncidentPontDeGaulleScenario:
    """Creates a local incident and nudges traffic toward Pont HKB."""

    def __init__(self, incident_step=300):
        self.incident_step = incident_step
        self.incident_vehicle_id = None
        self.triggered = False

    def apply(self, step):
        if self.triggered or step < self.incident_step:
            return None

        for vehicle_id in traci.vehicle.getIDList():
            route = traci.vehicle.getRoute(vehicle_id)
            if "PD" in route:
                traci.vehicle.slowDown(vehicle_id, 0.0, 120)
                traci.vehicle.setColor(vehicle_id, (255, 0, 0, 255))
                self.incident_vehicle_id = vehicle_id
                self.triggered = True
                return {
                    "type": "incident_pont_de_gaulle",
                    "vehicle_id": vehicle_id,
                    "step": step,
                }
        return None
