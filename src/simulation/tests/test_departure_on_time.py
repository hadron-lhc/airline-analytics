"""Tests del ciclo operativo realista: DOORS_CLOSED, despegue fijado por el
embarque (on-time), staffing por turno, equipaje y bancos de vuelos."""

from datetime import datetime, timedelta

import pytest

from src.enums.simulation_enums import EventType
from src.enums.world_enums import FlightMilestone
from src.simulation.simulation_runner import _staffing_for, _BUFFER_SECONDS
from src.simulation.world_factory import generate_world
from src.simulation.runner import run_simulation


def _full_enough_world(n_flights=12, n_passengers=1500, seed=11, n_airports=6):
    return generate_world(
        n_airports=n_airports,
        n_flights=n_flights,
        n_passengers=n_passengers,
        simulation_date=datetime(2026, 7, 13),
        seed=seed,
    )


# ----------------------------------------------------------------------
# DOORS_CLOSED + despegue fijado por el fin del embarque
# ----------------------------------------------------------------------


def test_flight_journey_emits_doors_closed():
    world = _full_enough_world()
    result = run_simulation(world)

    doors = [
        e for e in result.events if e.event_type == EventType.DOORS_CLOSED
    ]
    assert doors
    assert len(doors) == len(world.flights)

    # Doors close exactamente en el hito del vuelo (>= inicio de embarque).
    by_flight = {f.flight_number: f for f in world.flights}
    for event in doors:
        flight = by_flight[event.entity.flight_number]
        assert (
            event.event_time
            == flight.get_milestone(FlightMilestone.DOORS_CLOSED)
        )


def test_no_passenger_boards_after_doors_close():
    world = _full_enough_world()
    result = run_simulation(world)

    by_flight = {f.flight_number: f for f in world.flights}
    for event in result.events:
        if event.event_type != EventType.PASSENGER_BOARDED:
            continue
        flight = by_flight[event.payload["flight_number"]]
        assert (
            event.event_time
            <= flight.get_milestone(FlightMilestone.DOORS_CLOSED)
        )


def test_takeoff_never_before_schedule_and_keys_off_last_board():
    world = _full_enough_world()
    result = run_simulation(world)

    by_flight = {f.flight_number: f for f in world.flights}
    takeoffs = {
        e.entity.flight_number: e.event_time
        for e in result.events
        if e.event_type == EventType.AIRCRAFT_TAKE_OFF
    }
    assert len(takeoffs) == len(world.flights)

    last_boarded: dict[str, datetime] = {}
    for e in result.events:
        if e.event_type != EventType.PASSENGER_BOARDED:
            continue
        fn = e.payload["flight_number"]
        if fn not in last_boarded or e.event_time > last_boarded[fn]:
            last_boarded[fn] = e.event_time

    for fn, flight in by_flight.items():
        scheduled = flight.scheduled_departure
        assert takeoffs[fn] >= scheduled
        if last_boarded.get(fn) is not None:
            expected = max(
                scheduled, last_boarded[fn] + timedelta(seconds=_BUFFER_SECONDS)
            )
            assert takeoffs[fn] >= expected


def test_landed_shifted_with_takeoff():
    world = _full_enough_world()
    result = run_simulation(world)

    by_flight = {f.flight_number: f for f in world.flights}
    landed = {
        e.entity.flight_number: e.event_time
        for e in result.events
        if e.event_type == EventType.AIRCRAFT_LANDED
    }
    for fn, flight in by_flight.items():
        # La duración programada se mantiene aunque el despegue se retrase.
        flight_duration = (
            flight.scheduled_arrival - flight.scheduled_departure
        )
        assert landed[fn] - flight.get_milestone(FlightMilestone.TAKE_OFF) == (
            flight_duration
        )


# ----------------------------------------------------------------------
# Staffing por turno
# ----------------------------------------------------------------------


def test_staffing_profile_by_hour():
    from src.simulation.simulation_runner import _SECURITY_PROFILE

    assert _staffing_for(datetime(2026, 7, 13, 7, 0), _SECURITY_PROFILE) == (6, 28)
    assert _staffing_for(datetime(2026, 7, 13, 17, 0), _SECURITY_PROFILE) == (6, 28)
    assert _staffing_for(datetime(2026, 7, 13, 12, 0), _SECURITY_PROFILE) == (4, 20)
    assert _staffing_for(datetime(2026, 7, 13, 2, 0), _SECURITY_PROFILE) == (2, 10)
    assert _staffing_for(datetime(2026, 7, 13, 23, 0), _SECURITY_PROFILE) == (2, 10)


def test_staffing_peak_uses_more_security_points():
    from src.simulation.simulation_runner import (
        SimulationRunner,
        _SECURITY_PROFILE,
    )

    runner = SimulationRunner()
    pts = _staffing_for(datetime(2026, 7, 13, 7, 0), _SECURITY_PROFILE)[0]
    base_pts = _staffing_for(datetime(2026, 7, 13, 12, 0), _SECURITY_PROFILE)[0]
    assert pts > base_pts

    # Se aplica durante la corrida (los puestos mutan en vivo).
    world = _full_enough_world()
    queue = runner._get_security_queue(
        world.flights[0].origin_airport.iata_code
    )
    runner._configure_service(
        queue,
        datetime(2026, 7, 13, 7, 0),
        _SECURITY_PROFILE,
    )
    assert queue.service_points == pts
    assert len(queue.server_available_times) == pts


# ----------------------------------------------------------------------
# Equipaje real
# ----------------------------------------------------------------------


def test_baggage_wait_only_for_checked_and_stow_present():
    world = _full_enough_world()
    result = run_simulation(world)

    booked_checked = {
        b.passenger.passenger_id: b.checked_baggage for b in world.bookings
    }
    exits = [e for e in result.events if e.event_type == EventType.EXIT_AIRPORT]

    assert exits
    for event in exits:
        pid = event.entity.passenger_id
        checked = booked_checked[pid]
        bw = event.payload.get("baggage_wait", 0.0)
        assert (checked > 0) == (bw > 0), "solo viajan con espera si facturaron"

    boarded = [
        e for e in result.events if e.event_type == EventType.PASSENGER_BOARDED
    ]
    assert all("stow_time" in e.payload for e in boarded)


# ----------------------------------------------------------------------
# Bancos de vuelos (ondas 06-10 / 16-20)
# ----------------------------------------------------------------------


def test_departures_clustered_in_wave_banks():
    world = _full_enough_world(n_flights=30, n_passengers=900, seed=3)
    hours = {f.scheduled_departure.hour for f in world.flights}
    minutes = {f.scheduled_departure.minute for f in world.flights}

    assert hours <= set(range(6, 21))
    assert minutes <= {0, 15, 30, 45}
    # En 30 vuelos deben existir salidas tanto de mañana como de tarde.
    assert any(6 <= h <= 10 for h in hours)
    assert any(16 <= h <= 20 for h in hours)