import random

import traci


class TrafficGenerator:
    def rush_hour(self, step):
        if 100 < step < 600 and step % 4 == 0:
            route_ids = list(traci.route.getIDList())
            if not route_ids:
                return None
            route_id = random.choice(route_ids)
            vehicle_id = f"rush_{step}_{random.randint(0, 999)}"
            traci.vehicle.add(vehID=vehicle_id, routeID=route_id)
            return vehicle_id
        return None
