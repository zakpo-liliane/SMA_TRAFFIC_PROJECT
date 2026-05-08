import csv


class Metrics:
    def __init__(self, csv_path="results/simulation.csv"):
        self.csv_path = csv_path

    def load_rows(self):
        with open(self.csv_path, encoding="utf-8") as file_obj:
            return list(csv.DictReader(file_obj))

    def summary(self):
        rows = self.load_rows()
        if not rows:
            return {}

        return {
            "avg_waiting_time": sum(float(row["avg_waiting_time"]) for row in rows) / len(rows),
            "avg_queue_length": sum(float(row["avg_queue_length"]) for row in rows) / len(rows),
            "avg_trip_time": max(float(row["avg_trip_time"]) for row in rows),
            "messages_exchanged": int(rows[-1]["messages_exchanged"]),
        }
