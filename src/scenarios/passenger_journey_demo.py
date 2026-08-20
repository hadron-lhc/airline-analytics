from datetime import datetime

from ..loaders.airport_layout_loader import load_airport_layout
from ..simulation.passenger_journey import PassengerJourney
from ..simulation.generators.passenger_factory import create_random_passenger


def main():
    passenger = create_random_passenger()

    airport = load_airport_layout("LAX")

    journey = PassengerJourney()

    events = journey.run(
        passenger=passenger,
        airport_layout=airport,
        start_time=datetime(2026, 1, 1, 8, 0, 0),
        gate_code="gate_C1",
    )

    print(f"Passenger: {passenger.first_name} {passenger.last_name}")
    print(f"Events: {len(events)}")
    print()

    for event in events:
        print(f"{event.event_time.strftime('%H:%M:%S')} {event.event_type.name}")


if __name__ == "__main__":
    main()
