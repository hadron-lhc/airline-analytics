from ..simulation.world_factory import generate_world
from ..simulation.runner import run_simulation
from ..simulation.logger import SimulationLogger


def main():
    world = generate_world(n_flights=5, passengers_per_flight=100)
    result = run_simulation(world, logger=SimulationLogger())
    path = result.save_events("data/exports/simulation_2026_07_13.json")
    print(f"\nEvents saved to {path}")
    return result


if __name__ == "__main__":
    main()
