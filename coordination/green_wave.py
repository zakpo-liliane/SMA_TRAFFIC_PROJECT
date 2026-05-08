class GreenWaveCoordinator:
    """Lightweight neighborhood coordinator for green-wave style alignment."""

    def __init__(self):
        self.neighbors = {}
        self.last_decisions = {}
        self.last_congestion_levels = {}

    def register_neighbor(self, tls_a, tls_b):
        self.neighbors.setdefault(tls_a, set()).add(tls_b)
        self.neighbors.setdefault(tls_b, set()).add(tls_a)

    def get_neighbors(self, tls_id):
        return sorted(self.neighbors.get(tls_id, set()))

    def record_decision(self, tls_id, phase_index, green_lanes):
        self.last_decisions[tls_id] = {
            "phase_index": phase_index,
            "green_lanes": set(green_lanes),
        }

    def record_congestion(self, tls_id, level):
        self.last_congestion_levels[tls_id] = level

    def coordination_bonus(self, tls_id, green_lanes):
        bonus = 0.0
        green_lanes = set(green_lanes)
        for neighbor in self.neighbors.get(tls_id, set()):
            neighbor_state = self.last_decisions.get(neighbor)
            if not neighbor_state:
                continue
            shared_lanes = green_lanes.intersection(neighbor_state["green_lanes"])
            if shared_lanes:
                bonus += 1.5 * len(shared_lanes)
            elif neighbor_state["phase_index"] is not None:
                bonus += 0.4
        return bonus

    def neighbor_pressure(self, tls_id):
        score = 0.0
        for neighbor in self.neighbors.get(tls_id, set()):
            level = self.last_congestion_levels.get(neighbor)
            if level == "HIGH":
                score += 2.0
            elif level == "MEDIUM":
                score += 1.0
        return score
