import random
from datetime import datetime, timedelta

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

AIRPORT_GATES = {
    "EZE": ["A1", "A2", "A3", "A4", "A5"],
    "MIA": ["A6", "A7", "A8", "A9", "A10", "B1", "B2"],
    "JFK": ["B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10"],
    "LAX": ["C1", "C2", "C3", "C4", "C5", "C6", "C7"],
    "MAD": ["D1", "D2", "D3", "D4", "D5"],
    "BCN": ["D6", "D7", "D8"],
    "CDG": ["E1", "E2", "E3", "E4", "E5", "E6"],
    "LHR": ["F1", "F2", "F3", "F4", "F5"],
    "GRU": ["G1", "G2", "G3", "G4"],
    "MEX": ["H1", "H2", "H3"],
    "BOG": ["I1", "I2"],
    "SCL": ["J1"],
}

GATE_CODES = [g for codes in AIRPORT_GATES.values() for g in codes]

_airport_instances: dict[str, Airport] = {}


def get_or_create_airport(iata_code: str) -> Airport:
    if iata_code not in _airport_instances:
        gates_data = AIRPORT_GATES.get(iata_code)
        if gates_data is None:
            gates_data = [f"{chr(65 + i % 26)}{i // 26 + 1}" for i in range(random.randint(10, 20))]
        gates = [Gate(code) for code in gates_data]
        name = AIRPORTS.get(iata_code, f"Synthetic Airport {iata_code}")
        _airport_instances[iata_code] = Airport(
            iata_code=iata_code, name=name, gates=gates
        )
    return _airport_instances[iata_code]


def generate_synthetic_airports(n: int) -> list[str]:
    """Generate synthetic airport codes and register them. Returns list of IATA codes."""
    codes = []
    for i in range(1, n + 1):
        code = f"X{i:02d}"
        if code not in AIRPORTS:
            AIRPORTS[code] = f"Synthetic Airport {i}"
        codes.append(code)
    return codes


def generate_synthetic_routes(airport_codes: list[str], n: int) -> list[tuple[str, str, int]]:
    """Generate random routes between a list of airport codes."""
    routes = []
    for _ in range(n):
        origin = random.choice(airport_codes)
        dest = random.choice([c for c in airport_codes if c != origin])
        duration = random.randint(60, 660)
        routes.append((origin, dest, duration))
    return routes


def create_random_airport(iata_code=None, gate=None) -> Airport:
    return get_or_create_airport(iata_code)


def create_random_destination(started_code=None, gate=None) -> Airport:
    destinos_validos = [
        destino for origen, destino, tiempo in ROUTES if origen == started_code
    ]
    result_code = random.choice(destinos_validos)
    return get_or_create_airport(result_code)


def main():
    pass


if __name__ == "__main__":
    main()
