import csv
import os

import traci


class PerformanceMonitor:
    def __init__(self):
        self.rows = []
        self.departed_at = {}
        self.completed_trip_times = []

    def collect_step(self, step, intersections, message_bus):
        vehicles = traci.vehicle.getIDList()

        for vehicle_id in traci.simulation.getDepartedIDList():
            self.departed_at[vehicle_id] = step

        for vehicle_id in traci.simulation.getArrivedIDList():
            departed_at = self.departed_at.pop(vehicle_id, None)
            if departed_at is not None:
                self.completed_trip_times.append(step - departed_at)

        total_wait = sum(traci.vehicle.getWaitingTime(vehicle_id) for vehicle_id in vehicles)
        avg_wait = total_wait / len(vehicles) if vehicles else 0.0

        queue_lengths = [agent.get_queue_length() for agent in intersections]
        avg_queue = sum(queue_lengths) / len(queue_lengths) if queue_lengths else 0.0
        avg_trip_time = (
            sum(self.completed_trip_times) / len(self.completed_trip_times)
            if self.completed_trip_times else 0.0
        )

        self.rows.append({
            "step": step,
            "avg_waiting_time": round(avg_wait, 3),
            "avg_queue_length": round(avg_queue, 3),
            "avg_trip_time": round(avg_trip_time, 3),
            "vehicles_in_network": len(vehicles),
            "arrived": traci.simulation.getArrivedNumber(),
            "messages_exchanged": message_bus.total_sent,
        })

    def save_csv(self, filename):
        os.makedirs("results", exist_ok=True)
        fieldnames = [
            "step",
            "avg_waiting_time",
            "avg_queue_length",
            "avg_trip_time",
            "vehicles_in_network",
            "arrived",
            "messages_exchanged",
        ]

        with open(os.path.join("results", filename), "w", newline="", encoding="utf-8") as file_obj:
            writer = csv.DictWriter(file_obj, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.rows)
