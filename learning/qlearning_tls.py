import random


class QLearningTLS:

    def __init__(self):

        self.q_table = {}

        self.alpha = 0.1     # taux apprentissage
        self.gamma = 0.9     # facteur futur
        self.epsilon = 0.1   # exploration

        # actions possibles (indices)
        self.actions = list(range(9))

    # ---------------------------------
    # état basé sur congestion
    # ---------------------------------
    def get_state(self, congestion):

        if congestion < 3:
            return "LOW"
        elif congestion < 10:
            return "MEDIUM"
        else:
            return "HIGH"

    # ---------------------------------
    # choisir action (epsilon-greedy)
    # ---------------------------------
    def choose_action(self, state):

        if state not in self.q_table:
            self.q_table[state] = [0.0] * len(self.actions)

        # exploration
        if random.random() < self.epsilon:
            return random.choice(self.actions)

        # exploitation
        return self.q_table[state].index(max(self.q_table[state]))

    # ---------------------------------
    # MISE A JOUR Q-LEARNING REELLE
    # ---------------------------------
    def update(self, state, action, reward, next_state):

        # initialiser états si nouveaux
        if state not in self.q_table:
            self.q_table[state] = [0.0] * len(self.actions)

        if next_state not in self.q_table:
            self.q_table[next_state] = [0.0] * len(self.actions)

        old_value = self.q_table[state][action]
        next_max = max(self.q_table[next_state])

        # formule Q-learning
        new_value = old_value + self.alpha * (
            reward + self.gamma * next_max - old_value
        )

        self.q_table[state][action] = new_value