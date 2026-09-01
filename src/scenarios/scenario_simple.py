from ..simulation.world_factory import generate_world
from ..simulation.runner import run_simulation


def main():
    world = generate_world(
        n_airports=12,
        n_flights=10,
        n_passengers=200,
    )

    result = run_simulation(world)

    result.save_events("data/output/simulation.json")


if __name__ == "__main__":
    main()
