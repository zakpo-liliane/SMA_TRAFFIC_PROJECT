class MessageBus:
    def __init__(self):
        self.messages = []
        self.total_sent = 0
        self.history = []

    def send(self, msg):
        self.messages.append(msg)
        self.total_sent += 1
        self.history.append(msg)

    def receive(self, agent_id):
        received = [m for m in self.messages if m.receiver == agent_id]
        self.messages = [m for m in self.messages if m.receiver != agent_id]
        return received

    def pending_count(self):
        return len(self.messages)
