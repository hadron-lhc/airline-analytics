from datetime import datetime

from src.simulation.generators.passenger_journey import PassengerJourney
from src.simulation.simulation_runner import SimulationRunner
from src.simulation.replay import SimulationReplay
from src.simulation.world_factory import generate_world
from src.loaders.airport_layout_loader import load_airport_layout
from src.enums.simulation_enums import EventType
from src.enums.world_enums import FlightMilestone


def create_test_world(n_passengers=8):
    return generate_world(
        n_airports=2,
        n_flights=1,
        n_passengers=n_passengers,
        simulation_date=datetime(2026, 7, 13),
    )


def run_and_get_result(n_passengers=8):
    world = create_test_world(n_passengers=n_passengers)
    return SimulationRunner().run(world.bookings)


def test_every_boarded_passenger_gets_arrival_events():
    result = run_and_get_result()

    boarded = [
        event.entity
        for event in result.events
        if event.event_type == EventType.PASSENGER_BOARDED
    ]

    assert len(boarded) > 0

    for passenger in boarded:
        passenger_events = [
            event
            for event in result.events
            if event.entity is passenger
            and event.event_type in (
                EventType.EXIT_AIRCRAFT,
                EventType.EXIT_AIRPORT,
            )
        ]

        event_types = {event.event_type for event in passenger_events}

        assert EventType.EXIT_AIRCRAFT in event_types
        assert EventType.EXIT_AIRPORT in event_types


def test_arrival_events_follow_aircraft_landed():
    result = run_and_get_result()

    landed_time = next(
        event.event_time
        for event in result.events
        if event.event_type == EventType.AIRCRAFT_LANDED
    )

    for event in result.events:
        if event.event_type in (EventType.EXIT_AIRCRAFT, EventType.EXIT_AIRPORT):
            assert event.event_time >= landed_time


def test_exit_aircraft_precedes_exit_airport():
    result = run_and_get_result()

    for passenger in result.world.passengers:
        passenger_events = [
            event
            for event in result.events
            if event.entity is passenger
            and event.event_type in (
                EventType.EXIT_AIRCRAFT,
                EventType.EXIT_AIRPORT,
            )
        ]

        exit_aircraft = next(
            event
            for event in passenger_events
            if event.event_type == EventType.EXIT_AIRCRAFT
        )

        exit_airport = next(
            event
            for event in passenger_events
            if event.event_type == EventType.EXIT_AIRPORT
        )

        assert exit_aircraft.event_time <= exit_airport.event_time


def test_replay_ends_with_passengers_exited():
    result = run_and_get_result()

    replay = SimulationReplay(result)
    replay.seek(replay.frame_count)

    states = {passenger.state.value for passenger in replay.current_world.passengers}

    assert "Exited Airport" in states


def test_after_boarding_generates_two_arrival_events():
    world = create_test_world(n_passengers=1)
    booking = world.bookings[0]
    flight = booking.flight

    layout = load_airport_layout(flight.destination_airport.iata_code)
    landed_time = flight.get_milestone(FlightMilestone.LANDED)

    events = PassengerJourney().after_boarding(
        booking=booking,
        airport_layout=layout,
        landed_time=landed_time,
    )

    event_types = [event.event_type for event in events]

    assert event_types == [EventType.EXIT_AIRCRAFT, EventType.EXIT_AIRPORT]
    assert events[0].event_time >= landed_time
    assert events[1].event_time >= events[0].event_time


def test_export_maps_arrival_events_to_zones_and_states():
    result = run_and_get_result()

    exported = result.to_event_dicts()

    for entry in exported:
        if entry["event"] == EventType.EXIT_AIRCRAFT.value:
            assert entry["zone"] == "aircraft"
            assert entry["state"] == "At Destination Airport"

        if entry["event"] == EventType.EXIT_AIRPORT.value:
            assert entry["zone"] == "exit"
            assert entry["state"] == "Exited Airport"
