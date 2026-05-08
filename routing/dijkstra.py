import networkx as nx
import traci


class TrafficRouter:
    """Builds a directed graph from the active SUMO network and runs Dijkstra."""

    def __init__(self):
        self.graph = nx.DiGraph()
        self.refresh()

    def refresh(self):
        self.graph.clear()
        for edge_id in traci.edge.getIDList():
            if edge_id.startswith(":"):
                continue

            self.graph.add_node(edge_id)
            weight = self._edge_weight(edge_id)
            outgoing = self._outgoing_edges(edge_id)
            for next_edge in outgoing:
                self.graph.add_edge(edge_id, next_edge, weight=weight)

    def shortest_path(self, start, end):
        if start == end:
            return [start]
        self.refresh()
        return nx.dijkstra_path(self.graph, start, end, weight="weight")

    def _edge_weight(self, edge_id):
        travel_time = traci.edge.getTraveltime(edge_id)
        if travel_time and travel_time > 0:
            return travel_time

        lane_count = traci.edge.getLaneNumber(edge_id)
        if lane_count == 0:
            return 1.0
        lane_id = f"{edge_id}_0"
        length = traci.lane.getLength(lane_id)
        speed = traci.lane.getMaxSpeed(lane_id) or 1.0
        return max(1.0, length / speed)

    def _outgoing_edges(self, edge_id):
        next_edges = set()
        lane_count = traci.edge.getLaneNumber(edge_id)
        for lane_index in range(lane_count):
            lane_id = f"{edge_id}_{lane_index}"
            for link in traci.lane.getLinks(lane_id):
                if not link:
                    continue
                outgoing_lane = link[0]
                if outgoing_lane.startswith(":"):
                    continue
                next_edge = outgoing_lane.rsplit("_", 1)[0]
                if next_edge != edge_id:
                    next_edges.add(next_edge)
        return sorted(next_edges)
