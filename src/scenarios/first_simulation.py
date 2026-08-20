from collections import defaultdict

from ..simulation.simulation_runner import SimulationRunner
from ..simulation.generators.passenger_factory import generate_passengers
from ..simulation.generators.flight_factory import generate_flights
from ..simulation.generators.booking_factory import generate_bookings
from ..world.passenger import Passenger
from ..world.flight import Flight


def main():
    print("=" * 70)
    print("FIRST AIRLINE SIMULATION")
    print("=" * 70)

    # --------------------------------------------------
    # GENERATE WORLD DATA
    # --------------------------------------------------

    passengers = generate_passengers(100)
    flights = generate_flights(5)
    bookings = generate_bookings(passengers, flights)

    print(f"Passengers: {len(passengers)}")
    print(f"Flights:    {len(flights)}")
    print(f"Bookings:   {len(bookings)}")

    # --------------------------------------------------
    # RUN SIMULATION
    # --------------------------------------------------

    runner = SimulationRunner()

    result = runner.run(bookings)

    print(f"Events:     {len(result.events)}")
    print(f"Duration:   {result.duration}")

    # --------------------------------------------------
    # GLOBAL TIMELINE
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("FLIGHT SUMMARY")
    print("=" * 70)

    # --------------------------------------------------
    # GROUP EVENTS BY FLIGHT
    # --------------------------------------------------

    flight_events = defaultdict(list)

    for event in result.events:
        flight = event.payload.get("flight")

        if flight is not None:
            flight_number = flight.flight_number
        elif isinstance(event.entity, Flight):
            flight_number = event.entity.flight_number
        else:
            continue

        flight_events[flight_number].append(event)

    # --------------------------------------------------
    # SUMMARY PER FLIGHT
    # --------------------------------------------------

    for flight in sorted(flights, key=lambda f: f.scheduled_departure):
        events = flight_events.get(flight.flight_number, [])

        passenger_count = sum(
            1
            for booking in bookings
            if booking.flight.flight_number == flight.flight_number
        )

        print()
        print("-" * 70)
        print(
            f"{flight.flight_number} "
            f"{flight.origin_airport.iata_code} → "
            f"{flight.destination_airport.iata_code}"
        )
        print("-" * 70)

        print(f"Departure: {flight.scheduled_departure.strftime('%Y-%m-%d %H:%M:%S')}")

        print(f"Arrival:   {flight.scheduled_arrival.strftime('%Y-%m-%d %H:%M:%S')}")

        print(f"Gate:      {flight.gate.gate_code}")
        print(f"Passengers: {passenger_count}")

        # --------------------------------------------------
        # FLIGHT MILESTONES
        # --------------------------------------------------

        print()
        print("Flight milestones:")

        for event in events:
            if isinstance(event.entity, Flight):
                print(
                    f"  {event.event_time.strftime('%H:%M:%S')} "
                    f"{event.event_type.value}"
                )

        # --------------------------------------------------
        # PASSENGER EVENTS
        # --------------------------------------------------

        passenger_events = [
            event for event in events if isinstance(event.entity, Passenger)
        ]

        print()
        print(f"Passenger events: {len(passenger_events)}")

        if passenger_events:
            first_event = min(
                passenger_events,
                key=lambda event: event.event_time,
            )

            last_event = max(
                passenger_events,
                key=lambda event: event.event_time,
            )

            print(
                f"First passenger event: {first_event.event_time.strftime('%H:%M:%S')}"
            )

            print(
                f"Last passenger event:  {last_event.event_time.strftime('%H:%M:%S')}"
            )

        # --------------------------------------------------
        # EVENT COUNTS
        # --------------------------------------------------

        event_counts = defaultdict(int)

        for event in passenger_events:
            event_counts[event.event_type.value] += 1

        if event_counts:
            print()
            print("Passenger event counts:")

            for event_type, count in sorted(event_counts.items()):
                print(f"  {event_type:<25} {count}")

    # --------------------------------------------------
    # SAVE SIMULATION
    # --------------------------------------------------

    output_path = result.save_events("data/output/first_simulation.json")

    print()
    print("=" * 70)
    print("SIMULATION SAVED")
    print("=" * 70)
    print(output_path)


if __name__ == "__main__":
    main()
