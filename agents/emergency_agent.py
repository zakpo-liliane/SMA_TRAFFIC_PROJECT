from agents.crisis_agent import CrisisAgent


class EmergencyAgent(CrisisAgent):
    """Backward-compatible alias around the crisis manager."""

    def __init__(self, message_bus=None):
        super().__init__(message_bus=message_bus)
