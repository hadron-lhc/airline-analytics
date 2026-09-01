from datetime import datetime

from src.simulation.generators.booking_factory import (
    generate_booking,
    generate_bookings,
    _select_flight,
    _select_travel_class,
)
from src.simulation.generators.passenger_factory import create_random_passenger
from src.simulation.world_factory import generate_world
from src.enums.world_enums import FlightFullError, LoyaltyLevel, TravelClass, TravelPurpose


def create_test_world(n_airports=12, n_flights=5, n_passengers=100, date=None):
    return generate_world(
        n_airports=n_airports,
        n_flights=n_flights,
        n_passengers=n_passengers,
        simulation_date=date or datetime(2026, 7, 13),
    )


def test_generate_bookings_respects_flight_capacity():
    world = create_test_world(n_airports=12, n_flights=3, n_passengers=1000)

    for flight in world.flights:
        assert flight.passenger_count <= flight.capacity


def test_every_booking_is_linked_to_passenger_and_flight():
    world = create_test_world(n_passengers=50)

    assert len(world.bookings) > 0

    for booking in world.bookings:
        assert booking.passenger.current_booking is booking
        assert booking in booking.flight.bookings


def test_bookings_never_exceed_flight_capacity_end_to_end():
    world = create_test_world(n_airports=12, n_flights=20, n_passengers=2000)

    for flight in world.flights:
        assert flight.passenger_count <= flight.capacity


def test_adding_booking_over_capacity_raises():
    world = create_test_world(n_passengers=5)

    flight = world.flights[0]

    # Reducimos la capacidad hasta el número actual de reservas para que
    # un booking adicional quede por encima del límite.
    flight.capacity = len(flight.bookings)

    passenger = create_random_passenger()

    try:
        generate_booking(passenger, flight)
    except FlightFullError:
        return
    else:
        raise AssertionError(
            "generate_booking sobre un vuelo lleno debería lanzar FlightFullError"
        )


def test_select_flight_prefers_preferred_airline():
    world = create_test_world(n_passengers=1)

    flight = world.flights[0]
    passenger = create_random_passenger()

    airline = flight.flight_number[:2]
    passenger.preferred_airline = airline

    selected = _select_flight(passenger, world.flights)

    assert selected is None or selected.flight_number.startswith(airline)


def test_select_flight_with_all_flights_full_returns_none():
    world = create_test_world(n_flights=1, n_passengers=180)

    flight = world.flights[0]
    passenger = create_random_passenger()

    flight.capacity = len(flight.bookings)

    assert _select_flight(passenger, [flight]) is None


def test_assign_seat_marks_seat_occupied():
    world = create_test_world(n_passengers=1)

    booking = world.bookings[0]

    assert booking.seat is not None
    assert booking.seat.seat_number in booking.flight._occupied
    assert booking.seat.seat_number not in booking.flight._available


def test_travel_class_is_not_hardcoded_to_economy():
    world = create_test_world(n_passengers=150)

    classes = {b.travel_class for b in world.bookings}

    assert classes != {TravelClass.ECONOMY}
    assert TravelClass.ECONOMY in classes


def test_boarding_group_is_always_assigned():
    world = create_test_world(n_passengers=150)

    for booking in world.bookings:
        assert booking.boarding_group is not None


def test_checked_baggage_varies():
    world = create_test_world(n_passengers=200)

    values = {b.checked_baggage for b in world.bookings}

    assert 0 in values
    assert 1 in values


def test_preferred_seat_respected_when_available():
    world = create_test_world(n_flights=10, n_passengers=5)

    for booking in world.bookings:
        pref = booking.passenger.preferred_seat.value
        letter = booking.seat.seat_number[-1]

        if pref == "Window":
            assert letter in ("A", "F")
        elif pref == "Aisle":
            assert letter in ("C", "D")


def test_select_travel_class_business_purpose_not_all_economy():
    passenger = create_random_passenger()
    passenger.travel_purpose = TravelPurpose.BUSINESS
    passenger.loyalty_level = LoyaltyLevel.NONE

    classes = {_select_travel_class(passenger) for _ in range(300)}

    assert len(classes) > 1
    assert TravelClass.ECONOMY in classes
    assert TravelClass.BUSINESS in classes


# ---------------------------------------------------------------------------
# home_airport: pasajeros que "nacen" en su aeropuerto base
# ---------------------------------------------------------------------------


def test_passenger_home_airport_is_set_and_consistent():
    passenger = create_random_passenger()

    assert passenger.home_airport is not None
    assert isinstance(passenger.home_airport, str)
    assert len(passenger.home_airport) == 3


def test_generate_world_home_airports_cover_multiple_origins():
    world = create_test_world(n_airports=12, n_flights=60, n_passengers=3000)

    homes = {p.home_airport for p in world.passengers}

    # La demanda se reparte entre varios aeropuertos base (US + Europa + SA),
    # no se concentra en un único hub.
    assert len(homes) >= 5

    # Un pasajero que "nace" en su base debe tomar, en su mayoría, vuelos que
    # salen de esa base (cuando existe ruta desde allí).
    from collections import Counter

    matched = Counter()
    for b in world.bookings:
        origin = b.flight.origin_airport.iata_code
        home = b.passenger.home_airport
        matched["home"] += origin == home
        matched["total"] += 1

    assert matched["total"] > 0
    assert matched["home"] >= matched["total"] * 0.5


def test_select_flight_prefers_home_airport_when_available():
    world = create_test_world(n_airports=12, n_flights=60, n_passengers=2000)

    passenger = create_random_passenger()
    passenger.home_airport = "JFK"

    # Un pasajero con home JFK debe recaer en vuelos de origen JFK cuando existan.
    jfk_flights = [f for f in world.flights if f.origin_airport.iata_code == "JFK"]
    if jfk_flights:
        passenger.preferred_airline = None
        selected = _select_flight(passenger, world.flights)
        assert selected is None or selected.origin_airport.iata_code == "JFK"
