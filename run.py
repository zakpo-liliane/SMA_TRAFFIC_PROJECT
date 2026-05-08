from core.simulation_manager import SimulationManager


sim = SimulationManager(use_gui=False, max_steps=300)
sim.start()
sim.run()
