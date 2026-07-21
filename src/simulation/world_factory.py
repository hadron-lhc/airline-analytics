import random
from datetime import datetime, timedelta

from ..world.simulation_world import SimulationWorld
from ..world.flight import Flight

from .generators.airport_factory import (
    get_or_create_airport,
    AIRPORTS_DATA,
    AIRLINE_CODES,
    ROUTES,
    generate_synthetic_airports,
    generate_synthetic_routes,
)

from .generators.flight_factory import _allocate_gate
from .generators.passenger_factory import generate_passengers
from .generators.booking_factory import generate_bookings


def _generate_real_routes(all_codes):
    routes = list(ROUTES)

    real_codes = {c for c, _ in AIRPORTS_DATA}

    synth_codes = [c for c in all_codes if c not in real_codes]

    if synth_codes:
        routes.extend(
            generate_synthetic_routes(
                synth_codes + list(real_codes),
                200,
            )
        )

    return routes


def _create_flight(routes, base_date):
    for _ in range(10):
        origin_iata, dest_iata, duration_min = random.choice(routes)

        origin = get_or_create_airport(origin_iata)
        destination = get_or_create_airport(dest_iata)

        airline = random.choice(AIRLINE_CODES)
        flight_number = f"{airline}{random.randint(100, 999)}"

        departure_hour = random.randint(5, 22)
        departure_minute = random.choice([0, 15, 30, 45])

        scheduled_departure = base_date + timedelta(
            hours=departure_hour,
            minutes=departure_minute,
        )

        scheduled_arrival = scheduled_departure + timedelta(minutes=duration_min)

        try:
            gate = _allocate_gate(
                origin,
                scheduled_departure,
            )

        except RuntimeError:
            continue

        return Flight(
            flight_number=flight_number,
            origin_airport=origin,
            destination_airport=destination,
            scheduled_departure=scheduled_departure,
            scheduled_arrival=scheduled_arrival,
            gate=gate,
        )

    raise RuntimeError("Could not allocate gate after 10 attempts")


def _generate_airports(n: int):
    real_codes = [code for code, _ in AIRPORTS_DATA]

    if n <= len(real_codes):
        return real_codes[:n]

    for code in real_codes:
        get_or_create_airport(code)

    extra = n - len(real_codes)

    synthetic = generate_synthetic_airports(extra)

    return real_codes + synthetic


def generate_world(
    n_airports: int = 12,
    n_flights: int = 5,
    n_passengers: int = 500,
    simulation_date: datetime | None = None,
):
    if simulation_date is None:
        simulation_date = datetime.now().replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

    all_codes = _generate_airports(n_airports)

    routes = _generate_real_routes(all_codes)

    flights = [
        _create_flight(
            routes,
            simulation_date,
        )
        for _ in range(n_flights)
    ]

    passengers = generate_passengers(n=n_passengers)

    bookings = generate_bookings(
        passengers=passengers,
        flights=flights,
    )

    airports = [get_or_create_airport(code) for code in all_codes]

    return SimulationWorld(
        airports=airports,
        flights=flights,
        passengers=passengers,
        bookings=bookings,
    )
