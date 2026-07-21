from ..simulation.generators.passenger_journey import generate_passenger_journey
from ..simulation.generators.flight_journey import generate_flight_journey
from ..simulation.generators.flight_factory import create_random_flight
from ..simulation.generators.passenger_factory import generate_passengers
from ..simulation.generators.booking_factory import generate_bookings
from ..simulation.engine import SimulationEngine
from ..simulation.clock import SimulationClock
from ..simulation.logger import SimulationLogger
from datetime import datetime


def show_passengers(passengers):
    print("\n" + "=" * 60)
    print(
        f"{'Pasajero':<25} {'Estado':<20} {'Gate':<10} {'Checked In':<12} {'Boarded':<10}"
    )
    print("=" * 60)
    for p in passengers:
        gate_str = p.current_gate.gate_code if p.current_gate else "None"
        checked_in = (
            p.checked_in
            or (p.current_booking and p.current_booking.checked_in)
        )
        boarded = (
            p.boarded
            or (p.current_booking and p.current_booking.boarded)
        )
        print(
            f"{p.first_name + ' ' + p.last_name:<25} "
            f"{p.state.value:<20} "
            f"{gate_str:<10} "
            f"{'Yes' if checked_in else 'No':<12} "
            f"{'Yes' if boarded else 'No':<10}"
        )
    print("=" * 60)


def main():
    flight = create_random_flight()
    passengers = generate_passengers(10)

    bookings = generate_bookings(passengers, [flight])

    all_events = []
    all_events.extend(generate_flight_journey(flight))

    for booking in bookings:
        all_events.extend(generate_passenger_journey(booking))

    all_events.sort(key=lambda e: e.event_time)

    engine = SimulationEngine(
        clock=SimulationClock(current_time=datetime(2026, 7, 13, 0, 0, 0)),
        logger=SimulationLogger(),
    )
    engine.load_events(all_events)
    engine.run()

    show_passengers(passengers)


if __name__ == "__main__":
    main()
