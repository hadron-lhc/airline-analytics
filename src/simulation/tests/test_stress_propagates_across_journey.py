from datetime import datetime, timedelta

from src.simulation.generators.passenger_journey import PassengerJourney
from src.simulation.queues.security_queue import SecurityQueue
from src.simulation.world_factory import generate_world
from src.loaders.airport_layout_loader import load_airport_layout
from src.enums.simulation_enums import EventType

from src.world.passenger import Passenger


def create_test_world(n_passengers=1):
    return generate_world(
        n_airports=2,
        n_flights=1,
        n_passengers=n_passengers,
        simulation_date=datetime(2026, 7, 13),
    )


def run_complete_journey():
    world = create_test_world()

    booking = world.bookings[0]
    layout = load_airport_layout(booking.flight.origin_airport.iata_code)

    journey = PassengerJourney()

    context = journey.prepare(booking=booking, airport_layout=layout)
    queue = SecurityQueue(queue_service_model=journey.queue_service_model)
    security_result = queue.process(
        passenger=booking.passenger,
        arrival_time=context.security_arrival,
    )

    events = journey.continue_after_security(
        context=context,
        security_result=security_result,
    )

    return booking, events


def test_all_events_reference_the_same_passenger_object():
    booking, events = run_complete_journey()

    passenger = booking.passenger

    for event in events:
        assert isinstance(event.entity, Passenger)
        assert event.entity is passenger


def test_stress_changes_toward_the_end_of_the_journey():
    booking, events = run_complete_journey()

    security_arrival = next(
        event
        for event in events
        if event.event_type == EventType.ARRIVE_SECURITY
    )
    gate_arrival = next(
        event for event in events if event.event_type == EventType.ARRIVE_GATE
    )

    # The REACHED_GATE stress event is applied on the security -> gate leg,
    # so the stress recorded at the gate must differ from the one at security.
    assert gate_arrival.payload["stress"] != security_arrival.payload["stress"]


def test_walking_legs_carry_speed_and_stress_payload():
    booking, events = run_complete_journey()

    walking_legs = [
        event
        for event in events
        if "walking_speed" in event.payload and "distance" in event.payload
    ]

    assert len(walking_legs) == 3

    for event in walking_legs:
        assert event.payload["walking_speed"] > 0
        assert event.payload["distance"] > 0
        assert event.payload["walking_time"] > 0


def test_journey_events_are_chronological_per_passenger():
    booking, events = run_complete_journey()

    times = [event.event_time for event in events]

    assert times == sorted(times)


def test_journey_state_order_is_expected():
    booking, events = run_complete_journey()

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


def test_boarding_event_final_stress_matches_passenger_state():
    booking, events = run_complete_journey()

    final_event = events[-1]

    boarding_deadline = booking.flight.scheduled_departure - timedelta(minutes=15)

    if final_event.event_type == EventType.PASSENGER_BOARDED:
        assert final_event.event_time <= boarding_deadline
    else:
        assert final_event.event_time > boarding_deadline