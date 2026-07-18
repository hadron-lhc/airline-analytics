import random
from datetime import datetime, timedelta

from ...world.flight import Flight
from ...world.airport import Airport
from ...world.gate import Gate

AIRPORTS_DATA = [
    ("EZE", "Aeropuerto de Ezeiza"),
    ("MIA", "Aeropuerto Internacional de Miami"),
    ("JFK", "John F. Kennedy International Airport"),
    ("LAX", "Los Angeles International Airport"),
    ("MAD", "Adolfo Suárez Madrid-Barajas"),
    ("BCN", "Barcelona-El Prat"),
    ("CDG", "Charles de Gaulle Airport"),
    ("LHR", "Heathrow Airport"),
    ("GRU", "Aeroporto Internacional de São Paulo"),
    ("MEX", "Aeropuerto Internacional de la Ciudad de México"),
    ("BOG", "Aeropuerto Internacional El Dorado"),
    ("SCL", "Aeropuerto Internacional de Santiago"),
]

AIRPORTS = dict(AIRPORTS_DATA)

ROUTES = [
    ("EZE", "MIA", 540),
    ("EZE", "MAD", 660),
    ("EZE", "JFK", 600),
    ("MIA", "JFK", 200),
    ("MIA", "LAX", 300),
    ("MIA", "MAD", 540),
    ("MIA", "LHR", 480),
    ("MIA", "GRU", 420),
    ("MIA", "BOG", 240),
    ("MIA", "MEX", 220),
    ("JFK", "LAX", 360),
    ("JFK", "LHR", 420),
    ("JFK", "CDG", 450),
    ("JFK", "MAD", 420),
    ("LAX", "JFK", 300),
    ("MAD", "BCN", 90),
    ("MAD", "MIA", 540),
    ("MAD", "GRU", 600),
    ("MAD", "MEX", 600),
    ("BCN", "CDG", 90),
    ("CDG", "LHR", 60),
    ("GRU", "BOG", 300),
    ("GRU", "EZE", 180),
    ("MEX", "BOG", 240),
    ("BOG", "MIA", 240),
    ("BOG", "MAD", 540),
    ("SCL", "EZE", 120),
    ("SCL", "MIA", 480),
]

AIRLINE_CODES = ["AR", "AA", "IB", "LA", "DL", "UA", "AF", "BA", "AV"]

GATE_CODES = [
    "A1",
    "A2",
    "A3",
    "A4",
    "A5",
    "A6",
    "A7",
    "A8",
    "A9",
    "A10",
    "B1",
    "B2",
    "B3",
    "B4",
    "B5",
    "B6",
    "B7",
    "B8",
    "B9",
    "B10",
    "C1",
    "C2",
    "C3",
    "C4",
    "C5",
    "C6",
    "C7",
    "C8",
    "C9",
    "C10",
]


def create_random_flight(base_date=None) -> Flight:
    if base_date is None:
        now = datetime.now()
        base_date = now.replace(hour=0, minute=0, second=0, microsecond=0)

    origin_iata, dest_iata, duration_min = random.choice(ROUTES)

    gate_name = random.choice(GATE_CODES)
    gate = Gate(gate_code=gate_name)

    origin = Airport(iata_code=origin_iata, name=AIRPORTS[origin_iata], gates=[gate])
    destination = Airport(iata_code=dest_iata, name=AIRPORTS[dest_iata], gates=[])

    airline = random.choice(AIRLINE_CODES)
    flight_number = f"{airline}{random.randint(100, 999)}"

    departure_hour = random.randint(5, 22)
    scheduled_departure = base_date + timedelta(hours=departure_hour)
    scheduled_arrival = scheduled_departure + timedelta(minutes=duration_min)

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
            f"({f.scheduled_departure.strftime('%H:%M')} - {f.scheduled_arrival.strftime('%H:%M')})"
        )


if __name__ == "__main__":
    main()
