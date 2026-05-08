import csv

import matplotlib.pyplot as plt


def load_rows(csv_path):
    with open(csv_path, encoding="utf-8") as file_obj:
        return list(csv.DictReader(file_obj))


def plot_results(csv_path):
    rows = load_rows(csv_path)
    if not rows:
        raise ValueError("Aucune donnée à afficher.")

    steps = [int(row["step"]) for row in rows]
    avg_wait = [float(row["avg_waiting_time"]) for row in rows]
    avg_queue = [float(row["avg_queue_length"]) for row in rows]
    avg_trip = [float(row["avg_trip_time"]) for row in rows]
    messages = [int(row["messages_exchanged"]) for row in rows]

    plt.figure()
    plt.plot(steps, avg_wait)
    plt.title("Temps d'attente moyen")
    plt.xlabel("Step")
    plt.ylabel("Secondes")
    plt.grid()

    plt.figure()
    plt.plot(steps, avg_queue)
    plt.title("Longueur moyenne des files")
    plt.xlabel("Step")
    plt.ylabel("Véhicules")
    plt.grid()

    plt.figure()
    plt.plot(steps, avg_trip)
    plt.title("Temps de trajet moyen")
    plt.xlabel("Step")
    plt.ylabel("Secondes")
    plt.grid()

    plt.figure()
    plt.plot(steps, messages)
    plt.title("Messages échangés")
    plt.xlabel("Step")
    plt.ylabel("Messages cumulés")
    plt.grid()

    plt.show()
