import random
from datetime import timedelta

from ...world.booking import Booking
from ...world.passenger import Passenger
from ...world.flight import Flight

from ...enums.world_enums import (
    BookingStatus,
    TravelClass,
    CurrencyType,
)


def _select_flight(passenger: Passenger, flights: list[Flight]) -> Flight | None:
    """Selecciona un vuelo disponible para el pasajero."""

    candidates = [
        flight
        for flight in flights
        if len(flight.bookings) < flight.capacity
        and (
            passenger.preferred_airline is None
            or flight.flight_number.startswith(passenger.preferred_airline)
        )
    ]

    if not candidates:
        return None

    return random.choice(candidates)


def _generate_booking_date(flight: Flight):
    """La mayoría de reservas se realizan entre 1 y 90 días antes."""

    days_before = random.randint(1, 90)

    return flight.scheduled_departure - timedelta(days=days_before)


def _calculate_ticket_price(
    flight: Flight,
    travel_class: TravelClass,
) -> float:
    """Precio muy simple por ahora."""

    base = random.uniform(200, 1500)

    if travel_class == TravelClass.BUSINESS:
        base *= 2.2

    elif travel_class == TravelClass.FIRST:
        base *= 4

    return round(base, 2)


def generate_booking(passenger: Passenger, flight: Flight) -> Booking:
    seat = flight.assign_seat(passenger)

    travel_class = TravelClass.ECONOMY

    booking = Booking(
        passenger=passenger,
        flight=flight,
        seat=seat,
        booking_date=_generate_booking_date(flight),
        booking_status=BookingStatus.CONFIRMED,
        travel_class=travel_class,
        ticket_price=_calculate_ticket_price(
            flight,
            travel_class,
        ),
        currency=CurrencyType.USD,
    )

    passenger.current_booking = booking

    flight.add_booking(booking)

    return booking


def generate_bookings(
    passengers: list[Passenger],
    flights: list[Flight],
) -> list[Booking]:
    bookings = []

    random.shuffle(passengers)

    for passenger in passengers:
        flight = _select_flight(passenger, flights)

        if flight is None:
            continue

        booking = generate_booking(passenger, flight)

        bookings.append(booking)

    return bookings
