from ..simulation.generators.passenger_journey import generate_passenger_journey
from ..simulation.generators.flight_journey import generate_flight_journey
from ..simulation.generators.flight_factory import create_random_flight
from ..simulation.generators.passenger_factory import generate_passengers
from ..simulation.engine import SimulationEngine
from ..simulation.clock import SimulationClock
from datetime import datetime


def show_passengers(passengers):
    print("\n" + "=" * 60)
    print(f"{'Pasajero':<25} {'Estado':<20} {'Checked In':<12} {'Boarded':<10}")
    print("=" * 60)
    for p in passengers:
        print(
            f"{p.first_name + ' ' + p.last_name:<25} "
            f"{p.state.value:<20} "
            f"{'Yes' if p.checked_in else 'No':<12} "
            f"{'Yes' if p.boarded else 'No':<10}"
        )
    print("=" * 60)


def main():
    flight = create_random_flight()
    passengers = generate_passengers(10)

    all_events = []
    all_events.extend(generate_flight_journey(flight, passengers))

    for passenger in passengers:
        all_events.extend(generate_passenger_journey(passenger, flight))

    all_events.sort(key=lambda e: e.event_time)

    engine = SimulationEngine(
        clock=SimulationClock(current_time=datetime(2026, 7, 13, 0, 0, 0))
    )
    engine.load_events(all_events)
    engine.run()

    show_passengers(passengers)


if __name__ == "__main__":
    main()
