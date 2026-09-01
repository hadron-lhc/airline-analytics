import time
from datetime import datetime

from src.simulation.world_factory import generate_world
from src.simulation.simulation_runner import SimulationRunner
from src.simulation.result import SimulationResult
from src.enums.simulation_enums import EventType


def _run(n_passengers=8, n_airports=2, n_flights=1, seed=1):
    world = generate_world(
        n_airports=n_airports,
        n_flights=n_flights,
        n_passengers=n_passengers,
        simulation_date=datetime(2026, 7, 13),
        seed=seed,
    )
    runner = SimulationRunner()
    result = runner.run(world.bookings)
    return world, result


def _by_event(dicts, event_value):
    return [d for d in dicts if d["event"] == event_value]


# ---------------------------------------------------------------------------
# Golden test del esquema de export (docs/11 §4.4)
# ---------------------------------------------------------------------------


def test_golden_passenger_arrival_event_schema():
    _, result = _run()
    entries = _by_event(result.to_event_dicts(), EventType.ARRIVE_AIRPORT.value)

    assert entries

    for entry in entries:
        assert set(entry.keys()) == {
            "time",
            "event",
            "zone",
            "state",
            "entity",
            "id",
            "flight",
            "airport",
            "arrival_margin",
            "stress",
        }
        assert entry["zone"] == "entrance"
        assert entry["state"] == "At Airport"
        assert entry["entity"] == "passenger"
        assert entry["flight"]
        assert entry["airport"]


def test_golden_security_metric_aliases_present():
    _, result = _run()
    entries = _by_event(
        result.to_event_dicts(), EventType.SECURITY_STARTED.value
    )

    assert entries

    required = {
        "wait_seconds",
        "service_time",
        "queue_length",
        "security_occupancy",
        "security_congested",
    }
    for entry in entries:
        # Los alias de métricas traducen los nombres internos del payload.
        assert required <= set(entry.keys())


def test_golden_gate_zone_uses_gate_code():
    _, result = _run()
    entries = _by_event(result.to_event_dicts(), EventType.ARRIVE_GATE.value)

    assert entries

    for entry in entries:
        assert entry["zone"].startswith("gate_")
        assert entry["state"] == "Waiting Gate"


def test_golden_flight_entity_schema():
    _, result = _run()
    entries = _by_event(
        result.to_event_dicts(), EventType.AIRCRAFT_TAKE_OFF.value
    )

    assert entries

    for entry in entries:
        assert entry["entity"] == "flight"
        assert "id" in entry
        assert "airport" in entry
        # Los eventos de aeronave no llevan "state" (mapa _STATE_BY_EVENT).
        assert "state" not in entry
        assert entry["zone"] == "aircraft"


def test_metric_aliases_match_internal_payload_keys():
    """Cada alias declarado debe reflejar el nombre interno del payload."""
    from src.simulation import result as result_module

    event = None
    for e in _run()[1].events:
        if e.event_type == EventType.SECURITY_STARTED:
            event = e
            break

    assert event is not None

    aliases = result_module._METRIC_ALIASES
    for source, alias in aliases.items():
        if source in event.payload:
            assert alias in result_module._metric_columns(event.payload)


# ---------------------------------------------------------------------------
# Golden test de `_build_world` (docs/11 §4.4)
# ---------------------------------------------------------------------------


def test_build_world_recomposes_unique_referenced_objects():
    world, _ = _run()
    runner = SimulationRunner()

    rebuilt = runner._build_world(world.bookings)

    assert rebuilt is not None
    assert len(rebuilt.passengers) == len(world.bookings)

    expected_airports = {
        code
        for b in world.bookings
        for code in (
            b.flight.origin_airport.iata_code,
            b.flight.destination_airport.iata_code,
        )
    }
    assert {a.iata_code for a in rebuilt.airports} == expected_airports
    assert {f.flight_number for f in rebuilt.flights} == {
        b.flight.flight_number for b in world.bookings
    }


def test_build_world_with_empty_bookings_returns_none():
    runner = SimulationRunner()

    assert runner._build_world([]) is None


# ---------------------------------------------------------------------------
# Test de rendimiento / techo (docs/11 §4.4)
# ---------------------------------------------------------------------------


def test_large_run_completes_within_budget():
    """Test de techo de recursos: un día a gran escala debe completar dentro de
    un presupuesto generoso y producir un resultado consistente (sin crash).
    """
    n_passengers = 2500
    n_flights = 30
    n_airports = 12

    start = time.monotonic()
    world = generate_world(
        n_airports=n_airports,
        n_flights=n_flights,
        n_passengers=n_passengers,
        simulation_date=datetime(2026, 7, 13),
        seed=42,
    )
    result = SimulationRunner().run(world.bookings)
    elapsed = time.monotonic() - start

    assert elapsed < 20.0, f"simulación demasiado lenta: {elapsed:.1f}s"

    total = sum(
        1
        for e in result.events
        if e.event_type in (EventType.PASSENGER_BOARDED, EventType.MISSED_FLIGHT)
    )
    assert total == len(result.world.bookings)
    assert result.duration.total_seconds() > 0
