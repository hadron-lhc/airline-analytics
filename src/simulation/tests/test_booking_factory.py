from datetime import datetime

from src.simulation.generators.booking_factory import (
    generate_booking,
    generate_bookings,
    _select_flight,
)
from src.simulation.generators.passenger_factory import create_random_passenger
from src.simulation.world_factory import generate_world
from src.enums.world_enums import FlightFullError


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
