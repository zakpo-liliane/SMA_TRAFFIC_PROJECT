from communication.acl_message import ACLMessage


class BaseAgent:
    """Small BDI-style base class used by all project agents."""

    def __init__(self, agent_id, message_bus=None):
        self.id = agent_id
        self.message_bus = message_bus
        self.beliefs = {}
        self.desires = []
        self.intentions = []

    def update_beliefs(self):
        """Refresh the agent perception."""

    def deliberate(self):
        """Build intentions from current beliefs and desires."""

    def act(self):
        """Execute the current intention."""

    def step(self):
        self.update_beliefs()
        self.deliberate()
        self.act()

    def send_acl(self, receiver, performative, content):
        if self.message_bus is None:
            return
        message = ACLMessage(
            performative=performative,
            sender=self.id,
            receiver=receiver,
            content=content,
        )
        self.message_bus.send(message)

    def receive_acl(self):
        if self.message_bus is None:
            return []
        return self.message_bus.receive(self.id)
