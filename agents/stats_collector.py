class StatsCollector:
    def __init__(self):
        self.total_queue = 0.0
        self.total_wait = 0.0
        self.steps = 0
        self.max_queue = 0.0

    def update(self, avg_wait, avg_queue):
        self.total_wait += avg_wait
        self.total_queue += avg_queue
        self.steps += 1
        self.max_queue = max(self.max_queue, avg_queue)

    def summary(self):
        if self.steps == 0:
            return {
                "mean_wait": 0.0,
                "mean_queue": 0.0,
                "max_queue": 0.0,
            }
        return {
            "mean_wait": self.total_wait / self.steps,
            "mean_queue": self.total_queue / self.steps,
            "max_queue": self.max_queue,
        }
