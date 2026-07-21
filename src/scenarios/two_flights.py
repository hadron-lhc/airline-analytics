from datetime import datetime, timedelta

from ..world.passenger import Passenger
from ..world.flight import Flight
from ..world.gate import Gate
from ..enums.world_enums import Gender, DocumentType

from ..simulation.generators.passenger_journey import generate_passenger_journey
from ..simulation.generators.flight_journey import generate_flight_journey
from ..simulation.generators.airport_factory import get_or_create_airport
from ..simulation.generators.passenger_factory import generate_passengers
from ..simulation.generators.booking_factory import generate_bookings
from ..simulation.engine import SimulationEngine
from ..simulation.clock import SimulationClock
from ..simulation.logger import SimulationLogger


def _assign_gate(airport, departure):
    gate_start = departure - timedelta(minutes=45)
    gate_end = departure + timedelta(minutes=15)
    gate = airport.find_available_gate(gate_start, gate_end)
    if gate is None:
        raise RuntimeError(
            f"No available gate at {airport.iata_code} for "
            f"{gate_start.strftime('%H:%M')}–{gate_end.strftime('%H:%M')}"
        )
    airport.book_gate(gate, gate_start, gate_end)
    return gate


def show_gate_summary(airport):
    print("\n" + "=" * 60)
    print(f"Gate schedule at {airport.iata_code}:")
    print("=" * 60)
    for gate in airport.gates:
        bookings = airport._gate_bookings.get(gate.gate_code, [])
        if bookings:
            for b_start, b_end in bookings:
                print(
                    f"  {gate.gate_code}: {b_start.strftime('%H:%M')}–{b_end.strftime('%H:%M')}"
                )
        else:
            print(f"  {gate.gate_code}: free")
    print("=" * 60)


def main():
    eze = get_or_create_airport("EZE")

    base = datetime(2026, 7, 13, 0, 0, 0)

    flights = []

    # Flight 1: AR130 EZE→MIA 10:00
    dep1 = base.replace(hour=10)
    gate1 = _assign_gate(eze, dep1)
    flight1 = Flight(
        flight_number="AR130",
        origin_airport=eze,
        destination_airport=get_or_create_airport("MIA"),
        scheduled_departure=dep1,
        scheduled_arrival=dep1 + timedelta(hours=9, minutes=30),
        gate=gate1,
    )
    flights.append(flight1)

    # Flight 2: UA865 EZE→JFK 10:30 (same day, 30 min after AR130)
    dep2 = base.replace(hour=10, minute=30)
    gate2 = _assign_gate(eze, dep2)
    flight2 = Flight(
        flight_number="UA865",
        origin_airport=eze,
        destination_airport=get_or_create_airport("JFK"),
        scheduled_departure=dep2,
        scheduled_arrival=dep2 + timedelta(hours=10),
        gate=gate2,
    )
    flights.append(flight2)

    show_gate_summary(eze)

    all_events = []
    for flight in flights:
        passengers = generate_passengers(3)
        bookings = generate_bookings(passengers, [flight])
        all_events.extend(generate_flight_journey(flight))
        for booking in bookings:
            all_events.extend(generate_passenger_journey(booking))

    all_events.sort(key=lambda e: e.event_time)

    engine = SimulationEngine(
        clock=SimulationClock(current_time=base),
        logger=SimulationLogger(),
    )
    engine.load_events(all_events)
    engine.run()

    print("\n--- Summary ---")
    for flight in flights:
        print(
            f"{flight.flight_number} → Gate {flight.gate.gate_code} "
            f"dep {flight.scheduled_departure.strftime('%H:%M')}"
        )


if __name__ == "__main__":
    main()
