from datetime import datetime, timedelta

import pytest

from web import build_snapshots as bs
from src.enums.simulation_enums import EventType
from src.scenarios.hub_day_simulation import build_hub_world
from src.simulation.runner import run_simulation
from src.simulation.replay import SimulationReplay
from src.simulation.event import SimulationEvent
from src.simulation.generators import airport_factory


def _fresh_world(n=60):
    # Airport instances/gates are shared module state that accumulates
    # gate bookings across runs (see docs/11_test_audit.md §5). Reset them so
    # each test gets a deterministic, gate-available world.
    airport_factory._airport_instances.clear()
    return build_hub_world(n_passengers=n, staggered=True)


def _small_result(n=60):
    world = _fresh_world(n)
    return world, run_simulation(world)


# ----------------------------------------------------------------------
# timeline_ticks
# ----------------------------------------------------------------------


def test_timeline_ticks_respect_step():
    start = datetime(2026, 7, 13, 3, 7, 30)
    end = datetime(2026, 7, 13, 3, 22, 0)
    ticks = bs.timeline_ticks(start, end, 5)
    # 03:08, 03:13, 03:18, 03:22(end)
    assert ticks[0] == datetime(2026, 7, 13, 3, 8, 0)
    assert ticks[-1] >= end
    # interior gaps are exactly 5 min; the final (end) bucket may be shorter
    interior = [(b - a).seconds for a, b in zip(ticks, ticks[1:])]
    assert set(interior[:-1]) <= {300}
    assert interior[-1] <= 300


def test_timeline_ticks_end_included():
    start = datetime(2026, 7, 13, 10, 0, 0)
    end = datetime(2026, 7, 13, 10, 25, 0)
    ticks = bs.timeline_ticks(start, end, 5)
    assert ticks[-1] >= end


# ----------------------------------------------------------------------
# build_passenger_spatial on a real (small) run
# ----------------------------------------------------------------------


def test_spatial_at_three_moments():
    world, result = _small_result(60)
    replay = SimulationReplay(result)
    start = result.events[0].event_time
    end = result.events[-1].event_time

    replay.at(start)
    g0, by0, air0 = bs.build_passenger_spatial(replay.current_world.passengers, replay.current_world.flights)
    assert g0["At Home"] + g0["At Airport"] == 60  # nobody flying at the very start

    # mid-day: some passengers should be in the air
    mid = start + (end - start) / 2
    replay.at(mid)
    g1, by1, air1 = bs.build_passenger_spatial(replay.current_world.passengers, replay.current_world.flights)
    total_placed = sum(v for v in g1.values())
    assert total_placed == 60

    replay.at(end)
    g2, by2, air2 = bs.build_passenger_spatial(replay.current_world.passengers, replay.current_world.flights)
    assert g2["Exited Airport"] == 60
    # exited passengers are counted at their *destination* airport
    assert sum(apt["exited"] for apt in by2.values()) == 60
    # no one remains in any origin-side zone
    origin_zones = ["entrance", "check_in", "security", "gate"]
    assert all(apt[z] == 0 for apt in by2.values() for z in origin_zones)


def test_air_by_flight_grouping():
    world, result = _small_result(60)
    replay = SimulationReplay(result)
    start = result.events[0].event_time
    end = result.events[-1].event_time
    mid = start + (end - start) / 2
    replay.at(mid)
    _, _, air = bs.build_passenger_spatial(replay.current_world.passengers, replay.current_world.flights)
    assert all(isinstance(k, str) and k.isupper() for k in air)


# ----------------------------------------------------------------------
# build_airport_points (floor plan)
# ----------------------------------------------------------------------


def test_airport_points_sampling_and_determinism():
    world, result = _small_result(60)
    replay = SimulationReplay(result)
    start = result.events[0].event_time
    mid = start + (result.events[-1].event_time - start) / 2
    replay.at(mid)
    passengers = replay.current_world.passengers
    flights = replay.current_world.flights

    floor = bs.build_airport_points(passengers, flights, "JFK")

    # totals per zone reported in `zones`
    total_reported = sum(floor["zones"].values())
    assert total_reported > 0

    # per-zone point cap respects the sampling limit
    from collections import Counter
    per_zone = Counter(pt["zone"] for pt in floor["points"])
    for zone, n in per_zone.items():
        assert n <= bs.MAX_POINTS_PER_ZONE
    for zone, total in floor["zones"].items():
        assert per_zone[zone] <= total

    # deterministic: same passenger id -> same (x, y)
    floor2 = bs.build_airport_points(passengers, flights, "JFK")
    by_id = {pt["id"]: (pt["x"], pt["y"]) for pt in floor["points"]}
    for pt in floor2["points"]:
        assert by_id[pt["id"]] == (pt["x"], pt["y"])

    # coordinates stay within the map bounds (0..100%)
    for pt in floor["points"]:
        assert 0.0 <= pt["x"] <= 100.0
        assert 0.0 <= pt["y"] <= 100.0


# ----------------------------------------------------------------------
# build_metrics
# ----------------------------------------------------------------------


def test_build_metrics_accumulate_only_up_to_now():
    airport = "JFK"
    now = datetime(2026, 7, 13, 10, 0, 0)


    def ev(t, etype, **payload):
        return SimulationEvent(event_time=t, event_type=etype, entity=None, payload=payload)

    events = [
        ev(now - timedelta(seconds=1), EventType.SECURITY_COMPLETED,
           airport=airport, queue_wait=5.0, security_congested=False),
        ev(now, EventType.SECURITY_COMPLETED,
           airport=airport, queue_wait=10.0, security_congested=True),
        ev(now + timedelta(seconds=10), EventType.SECURITY_COMPLETED,
           airport=airport, queue_wait=99.0, security_congested=True),  # future -> ignored
        ev(now - timedelta(seconds=1), EventType.PASSENGER_BOARDED, airport=airport),
    ]
    events.sort(key=lambda e: e.event_time)  # result.events are chronologically sorted

    m = bs.build_metrics(events, now, [airport])
    sec = m["security"][airport]
    assert sec["processed"] == 2  # the future one excluded
    assert sec["wait_avg_s"] == 7.5
    assert sec["wait_max_s"] == 10.0
    assert sec["congested_pct"] == 50.0
    assert m["operational"]["boarded"] == 1


def test_metrics_include_checkin_stress_flight_and_cohorts():
    world, result = _small_result(120)
    start = result.events[0].event_time
    end = result.events[-1].event_time
    codes = [f.origin_airport.iata_code for f in world.flights]
    codes += [f.destination_airport.iata_code for f in world.flights]
    codes = list(dict.fromkeys(codes))

    m = bs.build_metrics(result.events, end, codes)

    # Check-in queue: per-airport accumulators exist
    assert "checkin" in m
    for code in codes:
        ck = m["checkin"][code]
        assert set(ck) >= {"processed", "wait_avg_s", "wait_max_s",
                           "congested_pct", "in_queue"}

    # SLA / experiencia
    assert "stress" in m
    assert {"boarding_avg", "boarding_stressed_pct", "high_pressure_pct",
            "waited"} <= set(m["stress"])

    # Puntualidad por vuelo (todos los embarcados quedan registrados)
    flight = m["operational"]["flight"]
    assert isinstance(flight, dict)
    assert sum(v["boarded"] for v in flight.values()) == m["operational"]["boarded"]

    # Cohortes por motivo de viaje
    cohorts = m["cohorts"]
    assert isinstance(cohorts, dict) and cohorts
    assert sum(v["boarded"] for v in cohorts.values()) == m["operational"]["boarded"]
    for v in cohorts.values():
        assert {"boarded", "missed", "missed_rate", "avg_wait",
                "avg_stress"} <= set(v)


# ----------------------------------------------------------------------
# Full pipeline writes the static bundle
# ----------------------------------------------------------------------


def test_full_build_writes_dist(tmp_path, monkeypatch):
    import web.build_snapshots as module

    monkeypatch.setattr(module, "DIST_DIR", tmp_path)
    monkeypatch.setattr(module, "DATA_DIR", tmp_path / "data")

    n_snapshots = module._write(
        [{"t": "2026-07-13T03:00:00", "global": {}, "by_airport": {}, "metrics": {}, "flights": {}}],
        {"start": "x", "end": "y", "passengers": 1, "flights": 1, "airports": {}, "total_events": 1},
    )

    assert n_snapshots == 1
    assert (tmp_path / "index.html").exists()
    assert (tmp_path / "data" / "snapshots.json").exists()
    assert (tmp_path / "data" / "meta.json").exists()
    assert (tmp_path / "js" / "app.js").exists()
    assert (tmp_path / "vendor" / "chart.umd.js").exists()
