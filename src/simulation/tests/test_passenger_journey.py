from datetime import datetime, timedelta

from src.simulation.generators.passenger_journey import PassengerJourney
from src.simulation.queues.security_queue import SecurityQueue
from src.simulation.queues.checkin_queue import CheckInQueue
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

    # prepare() llega hasta el mostrador de check-in; el check-in (cola
    # compartida) y el tramo a seguridad se completan en continue_after_checkin.
    assert event_types == [
        EventType.ARRIVE_AIRPORT,
        EventType.ARRIVE_CHECK_IN,
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


def test_prepare_checkin_arrival_matches_context():
    world = create_test_world()

    booking = world.bookings[0]
    layout = load_airport_layout(booking.flight.origin_airport.iata_code)

    journey = PassengerJourney()

    context = journey.prepare(
        booking=booking,
        airport_layout=layout,
    )

    checkin_event = next(
        event
        for event in context.events
        if event.event_type == EventType.ARRIVE_CHECK_IN
    )

    assert checkin_event.event_time == context.check_in_arrival


def test_continue_after_checkin_finalizes_security_arrival():
    world = create_test_world()

    booking = world.bookings[0]
    layout = load_airport_layout(booking.flight.origin_airport.iata_code)

    journey = PassengerJourney()

    context = journey.prepare(
        booking=booking,
        airport_layout=layout,
    )

    queue = CheckInQueue(queue_service_model=journey.queue_service_model)

    checkin_result = queue.process(
        passenger=booking.passenger,
        arrival_time=context.check_in_arrival,
    )

    context = journey.continue_after_checkin(
        context=context,
        checkin_result=checkin_result,
    )

    event_types = [event.event_type for event in context.events]

    assert EventType.CHECK_IN_COMPLETED in event_types
    assert EventType.ARRIVE_SECURITY in event_types

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

    checkin_queue = CheckInQueue(queue_service_model=journey.queue_service_model)
    checkin_result = checkin_queue.process(
        passenger=booking.passenger,
        arrival_time=context.check_in_arrival,
    )
    context = journey.continue_after_checkin(
        context=context,
        checkin_result=checkin_result,
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

    checkin_queue = CheckInQueue(queue_service_model=journey.queue_service_model)
    checkin_result = checkin_queue.process(
        passenger=booking.passenger,
        arrival_time=context.check_in_arrival,
    )
    context = journey.continue_after_checkin(
        context=context,
        checkin_result=checkin_result,
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
