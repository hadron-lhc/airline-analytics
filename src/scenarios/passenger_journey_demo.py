from ..loaders.airport_layout_loader import load_airport_layout
from ..simulation.generators.passenger_journey import PassengerJourney
from ..simulation.generators.passenger_factory import create_random_passenger
from ..simulation.generators.flight_factory import create_random_flight
from ..simulation.generators.booking_factory import generate_booking


def main():
    passenger = create_random_passenger()
    flight = create_random_flight()

    booking = generate_booking(passenger, flight)

    airport = load_airport_layout(flight.origin_airport.iata_code)

    journey = PassengerJourney()

    events = journey.run(
        booking=booking,
        airport_layout=airport,
    )

    print(f"Passenger: {passenger.first_name} {passenger.last_name}")
    print(f"Flight:    {flight.flight_number}")
    print(f"Events:    {len(events)}")
    print()

    for event in events:
        print(f"{event.event_time.strftime('%H:%M:%S')} {event.event_type.name}")


if __name__ == "__main__":
    main()
