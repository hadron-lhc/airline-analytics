from datetime import datetime, timedelta

from src.simulation.generators.passenger_journey import PassengerJourney
from src.simulation.queues.security_queue import SecurityQueue
from src.simulation.world_factory import generate_world
from src.loaders.airport_layout_loader import load_airport_layout
from src.enums.simulation_enums import EventType


def create_journey_fixture(n_passengers=30):
    """Crea un mundo con un vuelo y procesa todos sus pasajeros a través
    de una cola de seguridad compartida y congestionada."""
    world = generate_world(
        n_airports=2,
        n_flights=1,
        n_passengers=n_passengers,
        simulation_date=datetime(2026, 7, 13),
    )

    flight = world.flights[0]

    bookings = [
        booking
        for booking in world.bookings
        if booking.flight.flight_number == flight.flight_number
    ]

    layout = load_airport_layout(flight.origin_airport.iata_code)
    journey = PassengerJourney()

    security_queue = SecurityQueue(
        capacity=20,
        service_points=4,
    )

    # Concentramos la llegada de todos los pasajeros en el mismo margen
    # para forzar congestión en la cola de seguridad.
    for booking in bookings:
        booking.passenger.arrival_margin = 20

    contexts = [
        journey.prepare(
            booking=booking,
            airport_layout=layout,
        )
        for booking in bookings
    ]

    contexts.sort(key=lambda context: context.security_arrival)

    all_events = []

    for context in contexts:
        security_result = security_queue.process(
            passenger=context.booking.passenger,
            arrival_time=context.security_arrival,
        )

        events = journey.continue_after_security(
            context=context,
            security_result=security_result,
        )

        all_events.extend(events)

    return world, flight, bookings, all_events, security_queue


def test_every_passenger_completes_security():
    _, _, bookings, all_events, _ = create_journey_fixture()

    for booking in bookings:
        event_types = {
            event.event_type
            for event in all_events
            if event.entity is booking.passenger
        }

        assert EventType.SECURITY_COMPLETED in event_types


def test_congested_queue_produces_waits():
    _, _, _, all_events, _ = create_journey_fixture()

    waits = [
        event.payload.get("queue_wait", 0)
        for event in all_events
        if event.event_type == EventType.SECURITY_COMPLETED
    ]

    assert any(wait > 0 for wait in waits)


def test_every_passenger_reaches_the_gate():
    _, _, bookings, all_events, _ = create_journey_fixture()

    for booking in bookings:
        event_types = {
            event.event_type
            for event in all_events
            if event.entity is booking.passenger
        }

        assert EventType.ARRIVE_GATE in event_types


def test_every_passenger_has_a_boarding_result():
    _, _, bookings, all_events, _ = create_journey_fixture()

    for booking in bookings:
        event_types = {
            event.event_type
            for event in all_events
            if event.entity is booking.passenger
        }

        assert (
            EventType.PASSENGER_BOARDED in event_types
            or EventType.MISSED_FLIGHT in event_types
        )


def test_boarded_passengers_arrive_at_gate_on_time():
    _, flight, _, all_events, _ = create_journey_fixture()

    boarding_close = flight.scheduled_departure - timedelta(minutes=15)

    boarded = [
        event
        for event in all_events
        if event.event_type == EventType.PASSENGER_BOARDED
    ]

    assert all(event.event_time <= boarding_close for event in boarded)


def test_missed_flight_passengers_arrive_after_boarding_closes():
    _, flight, _, all_events, _ = create_journey_fixture()

    boarding_close = flight.scheduled_departure - timedelta(minutes=15)

    missed = [
        event for event in all_events if event.event_type == EventType.MISSED_FLIGHT
    ]

    assert all(event.event_time > boarding_close for event in missed)


def test_security_completion_precedes_gate_arrival_for_all():
    _, _, bookings, all_events, _ = create_journey_fixture()

    for booking in bookings:
        security_completed = next(
            event
            for event in all_events
            if event.entity is booking.passenger
            and event.event_type == EventType.SECURITY_COMPLETED
        )

        gate_arrival = next(
            event
            for event in all_events
            if event.entity is booking.passenger
            and event.event_type == EventType.ARRIVE_GATE
        )

        assert security_completed.event_time <= gate_arrival.event_time
