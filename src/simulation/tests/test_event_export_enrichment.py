from datetime import datetime

from src.simulation.world_factory import generate_world
from src.simulation.simulation_runner import SimulationRunner
from src.enums.simulation_enums import EventType


def run_small_simulation(n_passengers=5):
    world = generate_world(
        n_airports=2,
        n_flights=1,
        n_passengers=n_passengers,
        simulation_date=datetime(2026, 7, 13),
    )

    result = SimulationRunner().run(world.bookings)

    return result.to_event_dicts()


def test_export_marks_every_passenger_event_with_zone_and_state():
    events = run_small_simulation()

    passenger_events = [event for event in events if event["entity"] == "passenger"]

    assert len(passenger_events) > 0

    for event in passenger_events:
        assert "zone" in event
        assert "state" in event


def test_export_includes_stress_on_passenger_events():
    events = run_small_simulation()

    arrivals = [
        event for event in events if event["event"] == EventType.ARRIVE_AIRPORT.value
    ]

    assert len(arrivals) > 0

    for event in arrivals:
        assert "stress" in event
        assert 0.0 <= event["stress"] <= 1.0


def test_export_maps_gate_zone_with_gate_code():
    events = run_small_simulation()

    gate_arrivals = [
        event
        for event in events
        if event["event"] == EventType.ARRIVE_GATE.value
    ]

    assert len(gate_arrivals) > 0

    for event in gate_arrivals:
        assert event["zone"].startswith("gate_")


def test_export_carries_walking_and_security_metrics():
    events = run_small_simulation()

    walking = [
        event
        for event in events
        if event["event"] == EventType.ARRIVE_SECURITY.value
    ]

    security = [
        event
        for event in events
        if event["event"] == EventType.SECURITY_STARTED.value
    ]

    assert walking

    for event in walking:
        assert event["walking_speed"] > 0
        assert event["distance"] > 0
        assert event["walking_time"] > 0

    assert security

    for event in security:
        assert "wait_seconds" in event
        assert "service_time" in event


def test_export_is_json_serializable():
    import json

    events = run_small_simulation()

    json.dumps(events)  # must not raise


def test_export_save_and_load_round_trip(tmp_path):
    from src.simulation.simulation_runner import SimulationRunner
    from src.simulation.result import SimulationResult

    world = generate_world(
        n_airports=2,
        n_flights=1,
        n_passengers=5,
        simulation_date=datetime(2026, 7, 13),
    )

    result = SimulationRunner().run(world.bookings)

    path = result.save_events(str(tmp_path / "events.json"))

    loaded = SimulationResult.load_event_dicts(path)

    assert loaded == result.to_event_dicts()


def test_export_uses_time_strings_and_event_values():
    events = run_small_simulation()

    from datetime import datetime as dt

    for event in events:
        # El tiempo se exporta como cadena en formato %Y-%m-%d %H:%M:%S.
        dt.strptime(event["time"], "%Y-%m-%d %H:%M:%S")

        # El "event" es el valor textual del enum.
        assert isinstance(event["event"], str)
        assert event["event"]