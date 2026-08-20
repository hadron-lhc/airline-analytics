from ..simulation.generators.passenger_factory import create_random_passenger
from ..simulation.passenger_movement import PassengerMovement
from ..loaders.airport_layout_loader import load_airport_layout
from ..enums.world_enums import StressEvent


def main():
    passenger = create_random_passenger()

    movement = PassengerMovement()

    airport = load_airport_layout("LAX")

    entrance = airport.get_location("entrance")
    check_in = airport.get_location("check_in")
    security = airport.get_location("security")
    gate = airport.get_location("gate_C1")

    print("-" * 50)
    print(f"Passenger: {passenger.first_name} {passenger.last_name}")
    print(f"Stress resilience: {passenger.traits.stress_resilience:.2f}")
    print(f"Base walking speed: {passenger.walking_speed:.2f} m/s")
    print(f"Initial stress: {passenger.current_stress:.2f}")
    print("-" * 50)

    routes = [
        (
            entrance,
            check_in,
            StressEvent.TIME_PRESSURE,
        ),
        (
            check_in,
            security,
            StressEvent.RUNNING_LATE,
        ),
        (
            security,
            gate,
            StressEvent.REACHED_GATE,
        ),
    ]

    for origin, destination, event in routes:
        result = movement.move(
            passenger,
            origin,
            destination,
            stress_event=event,
        )

        print(f"{event.name}")
        print(f"Route: {origin.code} → {destination.code}")
        print(f"Stress: {result.initial_stress:.2f} → {result.final_stress:.2f}")
        print(f"Speed: {result.walking_speed:.2f} m/s")
        print(f"Walking time: {result.walking_time / 60:.2f} minutes")
        print()


if __name__ == "__main__":
    main()
