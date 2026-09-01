from collections import defaultdict

from ..simulation.simulation_runner import SimulationRunner
from ..simulation.generators.passenger_factory import generate_passengers
from ..simulation.generators.flight_factory import generate_flights
from ..simulation.generators.booking_factory import generate_bookings

from ..world.passenger import Passenger
from ..world.flight import Flight


def main():
    # ==================================================
    # GENERATE WORLD
    # ==================================================

    passengers = generate_passengers(100)
    flights = generate_flights(5)

    bookings = generate_bookings(
        passengers=passengers,
        flights=flights,
    )

    print("=" * 70)
    print("FIRST AIRLINE SIMULATION")
    print("=" * 70)

    print(f"Passengers: {len(passengers)}")
    print(f"Flights:    {len(flights)}")
    print(f"Bookings:   {len(bookings)}")

    # ==================================================
    # RUN SIMULATION
    # ==================================================

    runner = SimulationRunner()

    result = runner.run(bookings)

    events = result.events

    print(f"Events:     {len(events)}")
    print(f"Duration:   {result.duration}")

    # ==================================================
    # GROUP PASSENGER EVENTS BY FLIGHT
    # ==================================================

    passenger_events_by_flight = defaultdict(list)

    for event in events:
        if not isinstance(event.entity, Passenger):
            continue

        flight_number = event.payload.get("flight_number")

        if flight_number is not None:
            passenger_events_by_flight[flight_number].append(event)

    # ==================================================
    # FLIGHT SUMMARY
    # ==================================================

    print()
    print("=" * 70)
    print("FLIGHT SUMMARY")
    print("=" * 70)

    for flight in sorted(
        flights,
        key=lambda flight: flight.scheduled_departure,
    ):
        flight_number = flight.flight_number

        passenger_events = passenger_events_by_flight.get(
            flight_number,
            [],
        )

        # ----------------------------------------------
        # PASSENGERS
        # ----------------------------------------------

        passenger_ids = {event.entity.passenger_id for event in passenger_events}

        # ----------------------------------------------
        # FLIGHT EVENTS
        # ----------------------------------------------

        flight_events = [
            event
            for event in events
            if isinstance(event.entity, Flight) and event.entity is flight
        ]

        # ----------------------------------------------
        # PRINT FLIGHT INFORMATION
        # ----------------------------------------------

        print()
        print("-" * 70)

        print(
            f"{flight.flight_number} "
            f"{flight.origin_airport.iata_code} → "
            f"{flight.destination_airport.iata_code}"
        )

        print(f"Departure: {flight.scheduled_departure.strftime('%Y-%m-%d %H:%M:%S')}")

        print(f"Arrival:   {flight.scheduled_arrival.strftime('%Y-%m-%d %H:%M:%S')}")

        print(f"Gate:      {flight.gate.gate_code}")

        print(f"Passengers: {len(passenger_ids)}")

        # ----------------------------------------------
        # OPERATIONAL EVENTS
        # ----------------------------------------------

        print()
        print("Operational events:")

        for event in sorted(
            flight_events,
            key=lambda event: event.event_time,
        ):
            print(
                f"  {event.event_time.strftime('%H:%M:%S')} | {event.event_type.value}"
            )

        # ----------------------------------------------
        # PASSENGER ARRIVAL
        # ----------------------------------------------

        airport_arrivals = [
            event.event_time
            for event in passenger_events
            if event.event_type.value == "Arrive_Airport"
        ]

        if airport_arrivals:
            first_arrival = min(airport_arrivals)
            last_arrival = max(airport_arrivals)

            print()
            print("Passenger arrivals:")

            print(f"  First: {first_arrival.strftime('%H:%M:%S')}")

            print(f"  Last:  {last_arrival.strftime('%H:%M:%S')}")

        # ----------------------------------------------
        # GATE ARRIVAL
        # ----------------------------------------------

        gate_arrivals = [
            event.event_time
            for event in passenger_events
            if event.event_type.value == "Arrive_Gate"
        ]

        if gate_arrivals:
            first_gate = min(gate_arrivals)
            last_gate = max(gate_arrivals)

            print()
            print("Gate arrivals:")

            print(f"  First: {first_gate.strftime('%H:%M:%S')}")

            print(f"  Last:  {last_gate.strftime('%H:%M:%S')}")

        # ----------------------------------------------
        # WALKING SPEED
        # ----------------------------------------------

        walking_speeds = [
            event.payload["walking_speed"]
            for event in passenger_events
            if "walking_speed" in event.payload
        ]

        if walking_speeds:
            average_speed = sum(walking_speeds) / len(walking_speeds)

            print()
            print(f"Average walking speed: {average_speed:.2f} m/s")

        # ----------------------------------------------
        # STRESS
        # ----------------------------------------------

        stress_values = [
            event.payload["stress"]
            for event in passenger_events
            if "stress" in event.payload
        ]

        if stress_values:
            average_stress = sum(stress_values) / len(stress_values)

            print(f"Average stress: {average_stress:.2f}")

    # ==================================================
    # GLOBAL TIMELINE
    # ==================================================

    print()
    print("=" * 70)
    print("GLOBAL TIMELINE — FIRST 30 EVENTS")
    print("=" * 70)

    for event in events[:30]:
        if isinstance(event.entity, Flight):
            entity_name = event.entity.flight_number

        elif isinstance(event.entity, Passenger):
            entity_name = f"{event.entity.first_name} {event.entity.last_name}"

        else:
            entity_name = str(event.entity)

        print(
            f"{event.event_time.strftime('%H:%M:%S')} | "
            f"{event.event_type.value:<25} | "
            f"{entity_name}"
        )

    if len(events) > 30:
        print()
        print(f"... {len(events) - 30} more events")

    # ==================================================
    # END
    # ==================================================

    print()
    print("=" * 70)
    print("SIMULATION COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()
