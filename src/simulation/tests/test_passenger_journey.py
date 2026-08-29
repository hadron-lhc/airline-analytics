from datetime import datetime, timedelta

from src.simulation.generators.passenger_journey import PassengerJourney
from src.simulation.queues.security_queue import SecurityQueue
from src.simulation.world_factory import generate_world
from src.loaders.airport_layout_loader import load_airport_layout
from src.enums.simulation_enums import EventType


def create_test_world():
    return generate_world(
        n_airports=2,
        n_flights=1,
        n_passengers=1,
        simulation_date=datetime(2026, 7, 13),
    )


def test_prepare_generates_initial_journey_events():
    world = create_test_world()

    booking = world.bookings[0]
    layout = load_airport_layout(booking.flight.origin_airport.iata_code)

    journey = PassengerJourney()

    context = journey.prepare(
        booking=booking,
        airport_layout=layout,
    )

    event_types = [event.event_type for event in context.events]

    assert event_types == [
        EventType.ARRIVE_AIRPORT,
        EventType.ARRIVE_CHECK_IN,
        EventType.CHECK_IN_COMPLETED,
        EventType.ARRIVE_SECURITY,
    ]


def test_prepare_events_are_chronological():
    world = create_test_world()

    booking = world.bookings[0]
    layout = load_airport_layout(booking.flight.origin_airport.iata_code)

    journey = PassengerJourney()

    context = journey.prepare(
        booking=booking,
        airport_layout=layout,
    )

    times = [event.event_time for event in context.events]

    assert times == sorted(times)


def test_prepare_security_arrival_matches_context():
    world = create_test_world()

    booking = world.bookings[0]
    layout = load_airport_layout(booking.flight.origin_airport.iata_code)

    journey = PassengerJourney()

    context = journey.prepare(
        booking=booking,
        airport_layout=layout,
    )

    security_event = next(
        event
        for event in context.events
        if event.event_type == EventType.ARRIVE_SECURITY
    )

    assert security_event.event_time == context.security_arrival


def test_continue_after_security_generates_complete_remaining_journey():
    world = create_test_world()

    booking = world.bookings[0]
    layout = load_airport_layout(booking.flight.origin_airport.iata_code)

    journey = PassengerJourney()

    context = journey.prepare(
        booking=booking,
        airport_layout=layout,
    )

    queue = SecurityQueue(
        queue_service_model=journey.queue_service_model,
    )

    security_result = queue.process(
        passenger=booking.passenger,
        arrival_time=context.security_arrival,
    )

    events = journey.continue_after_security(
        context=context,
        security_result=security_result,
    )

    event_types = [event.event_type for event in events]

    assert event_types == [
        EventType.ARRIVE_AIRPORT,
        EventType.ARRIVE_CHECK_IN,
        EventType.CHECK_IN_COMPLETED,
        EventType.ARRIVE_SECURITY,
        EventType.SECURITY_STARTED,
        EventType.SECURITY_COMPLETED,
        EventType.ARRIVE_GATE,
        EventType.PASSENGER_BOARDED,
    ] or event_types == [
        EventType.ARRIVE_AIRPORT,
        EventType.ARRIVE_CHECK_IN,
        EventType.CHECK_IN_COMPLETED,
        EventType.ARRIVE_SECURITY,
        EventType.SECURITY_STARTED,
        EventType.SECURITY_COMPLETED,
        EventType.ARRIVE_GATE,
        EventType.MISSED_FLIGHT,
    ]


def test_security_completed_before_gate_arrival():
    world = create_test_world()

    booking = world.bookings[0]
    layout = load_airport_layout(booking.flight.origin_airport.iata_code)

    journey = PassengerJourney()

    context = journey.prepare(
        booking=booking,
        airport_layout=layout,
    )

    queue = SecurityQueue(
        queue_service_model=journey.queue_service_model,
    )

    security_result = queue.process(
        passenger=booking.passenger,
        arrival_time=context.security_arrival,
    )

    events = journey.continue_after_security(
        context=context,
        security_result=security_result,
    )

    security_completed = next(
        event for event in events if event.event_type == EventType.SECURITY_COMPLETED
    )

    gate_arrival = next(
        event for event in events if event.event_type == EventType.ARRIVE_GATE
    )

    assert gate_arrival.event_time >= security_completed.event_time


def test_run_generates_complete_journey():
    world = create_test_world()

    booking = world.bookings[0]
    layout = load_airport_layout(booking.flight.origin_airport.iata_code)

    journey = PassengerJourney()

    events = journey.run(
        booking=booking,
        airport_layout=layout,
    )

    event_types = [event.event_type for event in events]

    assert event_types[:4] == [
        EventType.ARRIVE_AIRPORT,
        EventType.ARRIVE_CHECK_IN,
        EventType.CHECK_IN_COMPLETED,
        EventType.ARRIVE_SECURITY,
    ]

    assert EventType.SECURITY_STARTED in event_types
    assert EventType.SECURITY_COMPLETED in event_types
    assert EventType.ARRIVE_GATE in event_types

    assert (
        EventType.PASSENGER_BOARDED in event_types
        or EventType.MISSED_FLIGHT in event_types
    )


def test_run_events_are_chronological():
    world = create_test_world()

    booking = world.bookings[0]
    layout = load_airport_layout(booking.flight.origin_airport.iata_code)

    journey = PassengerJourney()

    events = journey.run(
        booking=booking,
        airport_layout=layout,
    )

    times = [event.event_time for event in events]

    assert times == sorted(times)
