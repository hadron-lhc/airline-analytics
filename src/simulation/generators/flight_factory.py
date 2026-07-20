import random
from datetime import datetime, timedelta

from ...world.flight import Flight

from .airport_factory import get_or_create_airport, ROUTES, AIRLINE_CODES

BOARDING_BUFFER = timedelta(minutes=15)


def _allocate_gate(origin, scheduled_departure):
    gate_start = scheduled_departure - timedelta(minutes=45)
    gate_end = scheduled_departure + BOARDING_BUFFER
    gate = origin.find_available_gate(gate_start, gate_end)
    if gate is None:
        raise RuntimeError(
            f"No available gate at {origin.iata_code} for "
            f"{gate_start.strftime('%H:%M')}–{gate_end.strftime('%H:%M')}"
        )
    origin.book_gate(gate, gate_start, gate_end)
    return gate


def create_random_flight(base_date=None) -> Flight:
    if base_date is None:
        now = datetime.now()
        base_date = now.replace(hour=0, minute=0, second=0, microsecond=0)

    origin_iata, dest_iata, duration_min = random.choice(ROUTES)

    origin = get_or_create_airport(origin_iata)
    destination = get_or_create_airport(dest_iata)

    airline = random.choice(AIRLINE_CODES)
    flight_number = f"{airline}{random.randint(100, 999)}"

    departure_hour = random.randint(5, 22)
    scheduled_departure = base_date + timedelta(hours=departure_hour)
    scheduled_arrival = scheduled_departure + timedelta(minutes=duration_min)

    gate = _allocate_gate(origin, scheduled_departure)

    return Flight(
        flight_number=flight_number,
        origin_airport=origin,
        destination_airport=destination,
        scheduled_departure=scheduled_departure,
        scheduled_arrival=scheduled_arrival,
        gate=gate,
    )


def generate_flights(n, base_date=None) -> list[Flight]:
    return [create_random_flight(base_date) for _ in range(n)]


def main():
    flights = generate_flights(5)
    for f in flights:
        print(
            f"{f.flight_number} {f.origin_airport.iata_code} → {f.destination_airport.iata_code} "
            f"({f.scheduled_departure.strftime('%H:%M')} - {f.scheduled_arrival.strftime('%H:%M')}) "
            f"[Gate: {f.gate.gate_code}]"
        )


if __name__ == "__main__":
    main()
