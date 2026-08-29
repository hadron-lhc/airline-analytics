"""Resaltancia de la máquina de estados para la web.

Verifica que los estados Check In / Boarding aparezcan en el replay y que los
handlers los asignen correctamente (antes quedaban siempre en 0 en la web).
"""

from datetime import datetime

from src.enums.simulation_enums import EventType
from src.enums.world_enums import (
    BookingStatus,
    CurrencyType,
    FlightStatus,
    PassengerState,
    TravelClass,
)
from src.simulation.event import SimulationEvent
from src.simulation.generators.passenger_factory import generate_passengers
from src.simulation.handlers.passenger_handler import passenger_handler
from src.simulation.handlers.flight_handler import flight_handler
from src.world.booking import Booking
from src.world.flight import Flight
from src.world.gate import Gate

_ORIGIN = None


def _fresh_flight(n_seats: int = 2) -> Flight:
    from src.world.airport import Airport

    origin = Airport(iata_code="JFK", name="John F. Kennedy", gates=[Gate("B3")])
    dest = Airport(iata_code="LAX", name="Los Angeles", gates=[Gate("C1")])
    flight = Flight(
        flight_number="AR1000",
        origin_airport=origin,
        destination_airport=dest,
        scheduled_departure=datetime(2026, 7, 13, 10, 0),
        scheduled_arrival=datetime(2026, 7, 13, 16, 0),
        gate=Gate("B3"),
    )
    from src.enums.world_enums import TravelClass as TC

    flight.total_seats = {TC.ECONOMY: n_seats}
    flight.__post_init__()
    return flight


def _fresh_booking(passenger, flight) -> Booking:
    booking = Booking(
        passenger=passenger,
        flight=flight,
        booking_date=datetime(2026, 7, 13),
        booking_status=BookingStatus.CONFIRMED,
        travel_class=TravelClass.ECONOMY,
        ticket_price=120.0,
        currency=CurrencyType.USD,
    )
    flight.bookings.append(booking)
    passenger.current_booking = booking
    return booking


# ----------------------------------------------------------------------
# ARRIVE_CHECK_IN -> CHECK_IN
# ----------------------------------------------------------------------

def test_arrive_check_in_sets_check_in_state():
    flight = _fresh_flight()
    p = generate_passengers(1)[0]
    p.state = PassengerState.AT_AIRPORT
    ev = SimulationEvent(
        event_time=datetime(2026, 7, 13, 8, 0),
        event_type=EventType.ARRIVE_CHECK_IN,
        entity=p,
        payload={"flight": flight},
    )
    passenger_handler.process(ev)
    assert p.state == PassengerState.CHECK_IN


# ----------------------------------------------------------------------
# BOARDING_STARTED marks waiting passengers as boarding
# ----------------------------------------------------------------------

def test_boarding_started_marks_gate_passengers():
    flight = _fresh_flight()
    p_at_gate = generate_passengers(1)[0]
    p_elsewhere = generate_passengers(1)[0]
    p_at_gate.state = PassengerState.WAITING_GATE
    p_elsewhere.state = PassengerState.AT_SECURITY
    _fresh_booking(p_at_gate, flight)
    _fresh_booking(p_elsewhere, flight)
    assert flight.status == FlightStatus.SCHEDULED

    ev = SimulationEvent(
        event_time=datetime(2026, 7, 13, 9, 0),
        event_type=EventType.BOARDING_STARTED,
        entity=flight,
        payload={},
    )
    flight_handler.process(ev)

    assert flight.status == FlightStatus.BOARDING
    assert p_at_gate.state == PassengerState.BOARDING
    assert p_elsewhere.state == PassengerState.AT_SECURITY


# ----------------------------------------------------------------------
# ARRIVE_GATE: BOARDING si el vuelo ya está embarcando, si no WAITING_GATE
# ----------------------------------------------------------------------

def test_arrive_gate_during_boarding_sets_boarding():
    flight = _fresh_flight()
    flight.status = FlightStatus.BOARDING
    p = generate_passengers(1)[0]
    p.state = PassengerState.AT_SECURITY
    _fresh_booking(p, flight)

    ev = SimulationEvent(
        event_time=datetime(2026, 7, 13, 9, 30),
        event_type=EventType.ARRIVE_GATE,
        entity=p,
        payload={"flight": flight, "gate": "B3"},
    )
    passenger_handler.process(ev)
    assert p.state == PassengerState.BOARDING


def test_arrive_gate_before_boarding_sets_waiting_gate():
    flight = _fresh_flight()
    assert flight.status == FlightStatus.SCHEDULED
    p = generate_passengers(1)[0]
    p.state = PassengerState.AT_SECURITY
    _fresh_booking(p, flight)

    ev = SimulationEvent(
        event_time=datetime(2026, 7, 13, 8, 0),
        event_type=EventType.ARRIVE_GATE,
        entity=p,
        payload={"flight": flight, "gate": "B3"},
    )
    passenger_handler.process(ev)
    assert p.state == PassengerState.WAITING_GATE