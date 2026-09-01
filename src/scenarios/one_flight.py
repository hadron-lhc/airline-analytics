from ..simulation.generators.flight_factory import create_random_flight
from ..simulation.generators.passenger_factory import generate_passengers
from ..simulation.generators.booking_factory import generate_bookings
from ..simulation.simulation_runner import SimulationRunner
from ..simulation.replay import SimulationReplay


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

    runner = SimulationRunner()
    result = runner.run(bookings)

    replay = SimulationReplay(result)
    while replay.has_next():
        replay.step()

    print(f"\nEvents generated: {len(result.events)}")

    show_passengers(replay.current_world.passengers)


if __name__ == "__main__":
    main()
