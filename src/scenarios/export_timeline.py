from datetime import datetime

from ..simulation.world_factory import generate_world
from ..simulation.runner import run_simulation


def main():
    world = generate_world(
        n_airports=2,
        n_flights=2,
        n_passengers=60,
        simulation_date=datetime(2026, 7, 13),
    )

    result = run_simulation(world)

    path = result.save_events("data/exports/simulation_2026_07_13.json")

    events = result.to_event_dicts()
    per_type: dict[str, int] = {}
    for event in events:
        per_type[event["event"]] = per_type.get(event["event"], 0) + 1

    print(f"Timeline saved to {path}")
    print(f"Total events: {len(events)}")
    for event_type, count in sorted(per_type.items()):
        print(f"  {event_type:<24} {count}")

    return result


if __name__ == "__main__":
    main()