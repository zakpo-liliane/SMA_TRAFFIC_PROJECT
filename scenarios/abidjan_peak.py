import traci


class PeakTrafficScenario:
    """Injects a morning peak from Yopougon toward Plateau exits."""

    def __init__(self):
        self.route_ids = {
            "to_hkb": ["WY", "YP", "PH"],
            "to_de_gaulle": ["WY", "YP", "PD"],
            "abobo_to_hkb": ["AY", "YP", "PH"],
            "abobo_to_de_gaulle": ["AY", "YP", "PD"],
        }
        self._routes_created = False

    def setup(self):
        if self._routes_created:
            return
        for route_id, edges in self.route_ids.items():
            if route_id not in traci.route.getIDList():
                traci.route.add(route_id, edges)
        self._routes_created = True

    def apply(self, step):
        self.setup()
        if 60 <= step <= 820 and step % 5 == 0:
            if step % 30 == 0:
                route_id = "abobo_to_de_gaulle"
            elif step % 15 == 0:
                route_id = "abobo_to_hkb"
            elif step % 20 == 0:
                route_id = "to_de_gaulle"
            else:
                route_id = "to_hkb" if step % 2 == 0 else "to_de_gaulle"
            vehicle_id = f"peak_{step}_{route_id}"
            if vehicle_id not in traci.vehicle.getIDList():
                traci.vehicle.add(vehicle_id, route_id, typeID="car")
                return {
                    "type": "peak_injection",
                    "vehicle_id": vehicle_id,
                    "route_id": route_id,
                    "step": step,
                }
        return None
