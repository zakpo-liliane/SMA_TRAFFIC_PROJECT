from core.simulation_manager import SimulationManager


def run():
    sim = SimulationManager(use_gui=True, max_steps=300)
    sim.start()
    sim.run()


if __name__ == "__main__":
    run()
