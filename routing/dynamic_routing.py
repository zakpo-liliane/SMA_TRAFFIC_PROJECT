import traci

from routing.dijkstra import TrafficRouter


class DynamicRouter:
    def __init__(self):
        self.router = TrafficRouter()

    def compute_path(self, start_edge, destination_edge):
        try:
            return self.router.shortest_path(start_edge, destination_edge)
        except Exception:
            return []

    def set_shortest_path(self, veh_id, destination_edge):
        try:
            current_edge = traci.vehicle.getRoadID(veh_id)
            if not current_edge or current_edge.startswith(":"):
                return False
            path = self.compute_path(current_edge, destination_edge)
            if len(path) >= 2:
                traci.vehicle.setRoute(veh_id, path)
                return True
            return False
        except traci.TraCIException:
            return False

    def reroute_vehicle(self, veh_id, destination_edge=None):
        try:
            if destination_edge:
                return self.set_shortest_path(veh_id, destination_edge)
            traci.vehicle.rerouteTraveltime(veh_id)
            return True
        except traci.TraCIException:
            return False
