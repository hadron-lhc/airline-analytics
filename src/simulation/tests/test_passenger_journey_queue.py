from datetime import datetime

from src.simulation.generators.passenger_journey import PassengerJourney
from src.simulation.queues.security_queue import SecurityQueue
from src.simulation.world_factory import generate_world
from src.loaders.airport_layout_loader import load_airport_layout
from src.enums.simulation_enums import EventType


def create_test_world(n_passengers=5):
    return generate_world(
        n_airports=2,
        n_flights=1,
        n_passengers=n_passengers,
        simulation_date=datetime(2026, 7, 13),
    )


def prepare_passenger(journey, booking, layout):
    return journey.prepare(
        booking=booking,
        airport_layout=layout,
    )


def create_shared_queue(journey):
    return SecurityQueue(
        capacity=20,
        service_points=4,
        queue_service_model=journey.queue_service_model,
    )


def test_shared_security_queue_creates_waiting_passengers():
    world = create_test_world(n_passengers=5)

    flight = world.flights[0]

    bookings = [
        booking
        for booking in world.bookings
        if booking.flight.flight_number == flight.flight_number
    ]

    layout = load_airport_layout(flight.origin_airport.iata_code)

    journey = PassengerJourney()
    queue = create_shared_queue(journey)

    arrival_time = datetime(2026, 7, 13, 10, 0, 0)

    results = [
        queue.process(
            passenger=booking.passenger,
            arrival_time=arrival_time,
        )
        for booking in bookings
    ]

    assert len(results) == 5

    waiting_times = [result.waiting_time for result in results]

    assert any(waiting_time > 0 for waiting_time in waiting_times)


def test_first_four_passengers_can_start_security_immediately():
    world = create_test_world(n_passengers=4)

    flight = world.flights[0]

    bookings = [
        booking
        for booking in world.bookings
        if booking.flight.flight_number == flight.flight_number
    ]

    journey = PassengerJourney()
    queue = create_shared_queue(journey)

    arrival_time = datetime(2026, 7, 13, 10, 0, 0)

    results = [
        queue.process(
            passenger=booking.passenger,
            arrival_time=arrival_time,
        )
        for booking in bookings
    ]

    assert len(results) == 4

    for result in results:
        assert result.waiting_time == 0


def test_fifth_passenger_waits_when_four_service_points_are_busy():
    world = create_test_world(n_passengers=5)

    flight = world.flights[0]

    bookings = [
        booking
        for booking in world.bookings
        if booking.flight.flight_number == flight.flight_number
    ]

    journey = PassengerJourney()
    queue = create_shared_queue(journey)

    arrival_time = datetime(2026, 7, 13, 10, 0, 0)

    results = [
        queue.process(
            passenger=booking.passenger,
            arrival_time=arrival_time,
        )
        for booking in bookings
    ]

    fifth_result = results[4]

    assert fifth_result.waiting_time > 0
    assert fifth_result.service_start > fifth_result.arrival_time


def test_shared_queue_preserves_service_order():
    world = create_test_world(n_passengers=5)

    flight = world.flights[0]

    bookings = [
        booking
        for booking in world.bookings
        if booking.flight.flight_number == flight.flight_number
    ]

    journey = PassengerJourney()
    queue = create_shared_queue(journey)

    arrival_time = datetime(2026, 7, 13, 10, 0, 0)

    results = [
        queue.process(
            passenger=booking.passenger,
            arrival_time=arrival_time,
        )
        for booking in bookings
    ]

    waiting_results = [result for result in results if result.waiting_time > 0]

    assert len(waiting_results) == 1

    fifth_result = waiting_results[0]

    immediate_results = [
        result for result in results if result.waiting_time == 0
    ]

    assert fifth_result.service_start == min(
        result.service_end for result in immediate_results
    )


def test_journey_continues_after_shared_security_queue():
    world = create_test_world(n_passengers=5)

    flight = world.flights[0]

    bookings = [
        booking
        for booking in world.bookings
        if booking.flight.flight_number == flight.flight_number
    ]

    layout = load_airport_layout(flight.origin_airport.iata_code)

    journey = PassengerJourney()
    queue = create_shared_queue(journey)

    contexts = [
        journey.prepare(
            booking=booking,
            airport_layout=layout,
        )
        for booking in bookings
    ]

    all_events = []

    shared_security_arrival = datetime(
        2026,
        7,
        13,
        10,
        0,
        0,
    )

    for context in contexts:
        security_result = queue.process(
            passenger=context.booking.passenger,
            arrival_time=shared_security_arrival,
        )

        events = journey.continue_after_security(
            context=context,
            security_result=security_result,
        )

        all_events.extend(events)

    assert len(all_events) > 0

    for booking in bookings:
        passenger_events = [
            event for event in all_events if event.entity is booking.passenger
        ]

        event_types = [event.event_type for event in passenger_events]

        assert EventType.ARRIVE_SECURITY in event_types
        assert EventType.SECURITY_STARTED in event_types
        assert EventType.SECURITY_COMPLETED in event_types
        assert EventType.ARRIVE_GATE in event_types

        assert (
            EventType.PASSENGER_BOARDED in event_types
            or EventType.MISSED_FLIGHT in event_types
        )


def test_security_completion_precedes_gate_arrival_for_all_passengers():
    world = create_test_world(n_passengers=5)

    flight = world.flights[0]

    bookings = [
        booking
        for booking in world.bookings
        if booking.flight.flight_number == flight.flight_number
    ]

    layout = load_airport_layout(flight.origin_airport.iata_code)

    journey = PassengerJourney()
    queue = create_shared_queue(journey)

    shared_security_arrival = datetime(
        2026,
        7,
        13,
        10,
        0,
        0,
    )

    for booking in bookings:
        context = journey.prepare(
            booking=booking,
            airport_layout=layout,
        )

        security_result = queue.process(
            passenger=booking.passenger,
            arrival_time=shared_security_arrival,
        )

        events = journey.continue_after_security(
            context=context,
            security_result=security_result,
        )

        security_completed = next(
            event
            for event in events
            if event.event_type == EventType.SECURITY_COMPLETED
        )

        gate_arrival = next(
            event for event in events if event.event_type == EventType.ARRIVE_GATE
        )

        assert security_completed.event_time <= gate_arrival.event_time


def test_shared_queue_does_not_exceed_service_points():
    world = create_test_world(n_passengers=10)

    flight = world.flights[0]

    bookings = [
        booking
        for booking in world.bookings
        if booking.flight.flight_number == flight.flight_number
    ]

    journey = PassengerJourney()
    queue = create_shared_queue(journey)

    arrival_time = datetime(
        2026,
        7,
        13,
        10,
        0,
        0,
    )

    results = [
        queue.process(
            passenger=booking.passenger,
            arrival_time=arrival_time,
        )
        for booking in bookings
    ]

    assert len(results) == 10

    for result in results:
        assert result.occupancy >= 1

    service_intervals = [
        (
            result.service_start,
            result.service_end,
        )
        for result in results
    ]

    for start, end in service_intervals:
        concurrent_services = sum(
            1
            for other_start, other_end in service_intervals
            if other_start <= start < other_end
        )

        assert concurrent_services <= queue.service_points
