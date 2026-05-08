class ContractNet:
    """Tiny FIPA-style Contract Net helper."""

    def call_for_proposal(self, agent, neighbors):
        for neighbor in neighbors:
            agent.send_acl(
                neighbor.id,
                "cfp",
                {
                    "reason": "priority_request",
                    "queue_length": agent.get_queue_length(),
                    "intersection": agent.tls_id,
                },
            )

    def make_proposal(self, queue_length):
        return {
            "queue_length": queue_length,
            "score": max(1, 100 - queue_length),
        }

    def select_winner(self, proposals):
        if not proposals:
            return None
        return min(
            proposals.items(),
            key=lambda item: item[1].get("queue_length", 10**9),
        )[0]
