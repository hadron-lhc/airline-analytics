import random
from datetime import timedelta

from ...world.booking import Booking
from ...world.passenger import Passenger
from ...world.flight import Flight

from ...enums.world_enums import (
    BookingStatus,
    BoardingGroup,
    LoyaltyLevel,
    TravelClass,
    TravelPurpose,
    CurrencyType,
)


def _select_flight(passenger: Passenger, flights: list[Flight]) -> Flight | None:
    """Selecciona un vuelo disponible para el pasajero.

    Si el pasajero tiene un ``home_airport`` (su aeropuerto base), se
    priorizan los vuelos que salen de allí — así "nace" en su aeropuerto.
    Si no hay ningún vuelo desde su base (o si no tiene base), se cae a
    cualquier vuelo disponible para no dejar demanda huérfana.
    """

    base = [
        flight
        for flight in flights
        if len(flight.bookings) < flight.capacity
        and flight._available
        and (
            passenger.preferred_airline is None
            or flight.flight_number.startswith(passenger.preferred_airline)
        )
    ]

    if not base:
        return None

    if passenger.home_airport is not None:
        home = [
            f for f in base
            if f.origin_airport.iata_code == passenger.home_airport
        ]
        if home:
            return random.choice(home)

    return random.choice(base)


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


def _select_travel_class(passenger: Passenger) -> TravelClass:
    """Deriva la clase de viaje del propósito y de la lealtad del pasajero.

    - Viajes de negocio tienden a Business / Premium Economy.
    - Los pasajeros con lealtad alta suben de clase con más frecuencia.
    - La mayoría de los viajes de ocio/visita son Economy.
    """

    loyalty_bump = {
        LoyaltyLevel.NONE: 0.02,
        LoyaltyLevel.SILVER: 0.06,
        LoyaltyLevel.GOLD: 0.15,
        LoyaltyLevel.PLATINUM: 0.35,
    }.get(passenger.loyalty_level, 0.02)

    if passenger.travel_purpose == TravelPurpose.BUSINESS:
        weights = [
            (TravelClass.FIRST, 0.04),
            (TravelClass.BUSINESS, 0.22),
            (TravelClass.PREMIUM_ECONOMY, 0.24),
            (TravelClass.ECONOMY, 0.50),
        ]
    else:
        weights = [
            (TravelClass.FIRST, 0.01),
            (TravelClass.BUSINESS, 0.04 + loyalty_bump),
            (TravelClass.PREMIUM_ECONOMY, 0.10 + loyalty_bump),
            (TravelClass.ECONOMY, 0.85 - 2 * loyalty_bump),
        ]

    classes = [c for c, _ in weights]
    probs = [w for _, w in weights]
    return random.choices(classes, weights=probs, k=1)[0]


def _select_boarding_group(
    travel_class: TravelClass,
    passenger: Passenger,
) -> BoardingGroup:
    """Grupo de embarque: prioridad para clases altas y lealtad alta."""

    if travel_class in (TravelClass.FIRST, TravelClass.BUSINESS):
        return BoardingGroup.PRIORITY
    if passenger.loyalty_level in (
        LoyaltyLevel.PLATINUM,
        LoyaltyLevel.GOLD,
    ):
        return BoardingGroup.PRIORITY

    group_roll = random.random()
    if group_roll < 0.15:
        return BoardingGroup.GROUP_1
    if group_roll < 0.40:
        return BoardingGroup.GROUP_2
    if group_roll < 0.70:
        return BoardingGroup.GROUP_3
    if group_roll < 0.90:
        return BoardingGroup.GROUP_4
    return BoardingGroup.GROUP_5


def generate_booking(passenger: Passenger, flight: Flight) -> Booking:
    travel_class = _select_travel_class(passenger)

    seat = flight.assign_seat(
        passenger,
        preferred_class=travel_class,
        seat_preference=passenger.preferred_seat,
    )

    checked_baggage = 1 if random.random() < passenger.baggage_probability else 0

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

    booking.checked_baggage = checked_baggage
    booking.boarding_group = _select_boarding_group(travel_class, passenger)

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
