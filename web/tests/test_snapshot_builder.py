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
# Floor-plan geometry: gate box envelopes gates; arrivals row centered
# ----------------------------------------------------------------------


def _box(c, r):
    return (c[0] - r[0], c[0] + r[0], c[1] - r[1], c[1] + r[1])


def _inside(x, y, b, tol=0.01):
    return b[0] - tol <= x <= b[1] + tol and b[2] - tol <= y <= b[3] + tol


_GEO_CODES = ["EZE", "MIA", "JFK", "LAX", "MAD", "BCN", "CDG",
              "LHR", "GRU", "MEX", "BOG", "SCL"]


def test_gate_box_envelopes_real_gates():
    for code in _GEO_CODES:
        geo = bs._layout_geometry(code)
        gate_box = _box(geo["zones"]["gate"]["c"], geo["zones"]["gate"]["r"])
        for gate_code, (gx, gy) in geo["gates"].items():
            # the gate position and its outer scatter points stay inside
            assert _inside(gx, gy, gate_box), (code, gate_code)
            rx, ry = bs._ZONE_SCATTER["gate"]
            assert _inside(gx + rx, gy + ry, gate_box), (code, gate_code)


def test_arrivals_row_centered_no_left_hug():
    for code in _GEO_CODES:
        geo = bs._layout_geometry(code)
        zones = geo["zones"]
        assert zones["destination"]["c"][0] > 30, code
        assert zones["exited"]["c"][0] > 30, code
        # both boxes fully inside the plan (0..100)
        for z in ("destination", "exited"):
            b = _box(zones[z]["c"], zones[z]["r"])
            assert 0.0 <= b[0] and b[1] <= 100.0, (code, z)
            assert 0.0 <= b[2] and b[3] <= 100.0, (code, z)
        # and they don't touch each other
        d, e = zones["destination"], zones["exited"]
        db, eb = _box(d["c"], d["r"]), _box(e["c"], e["r"])
        assert db[1] < eb[0], code


def test_airport_points_inside_their_zone_boxes():
    world, result = _small_result(60)
    replay = SimulationReplay(result)
    start = result.events[0].event_time
    mid = start + (result.events[-1].event_time - start) / 2
    replay.at(mid)
    passengers = replay.current_world.passengers
    flights = replay.current_world.flights

    for code in ("JFK", "EZE", "MIA"):
        geo = bs._layout_geometry(code)
        floor = bs.build_airport_points(passengers, flights, code)
        for pt in floor["points"]:
            zone = geo["zones"].get(pt["zone"])
            if zone is None:
                continue
            b = _box(zone["c"], zone["r"])
            assert _inside(pt["x"], pt["y"], b), (code, pt)


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


# ----------------------------------------------------------------------
# Bundle único {meta, snapshots, report} + variantes gzip
# ----------------------------------------------------------------------


def test_write_creates_report_and_gzip_bundle(tmp_path, monkeypatch):
    import json
    import gzip

    import web.build_snapshots as module

    monkeypatch.setattr(module, "DIST_DIR", tmp_path)
    monkeypatch.setattr(module, "DATA_DIR", tmp_path / "data")

    snapshots = [{"t": "2026-07-13T03:00:00", "global": {}}]
    meta = {"start": "x", "end": "y", "passengers": 1, "flights": 1,
            "airports": {}, "total_events": 1, "title": "Prueba"}
    report = {
        "meta": {"title": "Prueba", "date": "2026-07-13", "start": "03:00",
                 "end": "11:00", "passengers": 1, "flights": 1,
                 "airports": {}, "events": 1},
        "resumen": {"boarded": 1, "missed": 0, "missed_rate": 0.0,
                    "completed": 1, "completed_pct": 100.0,
                    "avg_origin_min": 60.0, "on_time_rate": 100.0,
                    "avg_delay_min": 0.0, "load_factor_avg": 50.0,
                    "boarding_avg_stress": 0.0, "high_pressure_pct": 0.0},
        "colas": {"security": [], "checkin": []},
        "experiencia": {"boarding_avg": 0.0, "boarding_stressed_pct": 0.0,
                        "high_pressure_pct": 0.0, "waited": 0,
                        "avg_baggage_wait_s": 0.0, "checked_passengers": 0,
                        "avg_stow_s": 0.0},
        "cohortes": [],
        "vuelos": [],
        "heatmap": {"security": {}, "checkin": {}},
    }

    out_file = tmp_path / "custom" / "sim.json"
    module._write(snapshots, meta, report=report, out_file=str(out_file))

    # informe legible + json
    assert (tmp_path / "report.md").read_text().startswith("#")
    assert json.loads((tmp_path / "data" / "report.json").read_text())["resumen"]["boarded"] == 1

    # variantes gzip presentes y descomprimibles
    for name in ("snapshots.json.gz", "meta.json.gz", "simulation.json.gz"):
        path = tmp_path / "data" / name
        assert path.exists(), name
        with gzip.open(path, "rt", encoding="utf-8") as f:
            roundtrip = json.load(f)
        if name == "simulation.json.gz":
            assert roundtrip["meta"] == meta
            assert roundtrip["snapshots"] == snapshots
            assert roundtrip["report"] == report

    # bundle fuera de dist (--out-file)
    assert json.loads(out_file.read_text())["meta"]["flights"] == 1


def test_metrics_include_on_time_heatmap_and_percentiles():
    world, result = _small_result(120)
    start = result.events[0].event_time
    end = result.events[-1].event_time
    codes = [f.origin_airport.iata_code for f in world.flights]
    codes += [f.destination_airport.iata_code for f in world.flights]
    codes = list(dict.fromkeys(codes))

    m = bs.build_metrics(result.events, end, codes, flights=world.flights)

    op = m["operational"]
    assert "on_time_rate" in op
    assert 0.0 <= op["on_time_rate"] <= 100.0
    assert "load_factor_avg" in op

    sec = m["security"]
    first = next(iter(sec.values()))
    assert "wait_p50_s" in first and "wait_p90_s" in first
    assert "hours" in first

    # Puntualidad por vuelo incorpora el schedule (on_time/delay_min).
    some_flight = next(iter(op["flight"].values()))
    assert "on_time" in some_flight and "delay_min" in some_flight


# ----------------------------------------------------------------------
# Paso adaptativo (ondas finas, noche ancha)
# ----------------------------------------------------------------------


def test_timeline_ticks_adaptive_peak_finer():
    start = datetime(2026, 7, 13, 5, 0, 0)
    end = datetime(2026, 7, 13, 23, 0, 0)
    ticks = bs.timeline_ticks_adaptive(start, end, 5)

    gaps = {
        t.hour: (b - a).total_seconds() / 60.0
        for a, b, t in zip(ticks, ticks[1:], ticks)
        if (b - a).total_seconds() > 0
    }
    assert gaps, "debe generar ticks en todo el rango"
    assert all(minutes <= 15 for minutes in gaps.values()), "paso nunca > 15 min"
    assert all(minutes >= 1 for minutes in gaps.values())

    # Fuera de ondas y de la noche usa el paso base (5 min).
    assert gaps[12] == 5
    # En la oda de la mañana el paso se reduce (5 // 2 = 2 min).
    assert gaps[7] == 2
    # En la oda de la tarde también.
    assert gaps[17] == 2
    # De noche se ensancha a 15 min.
    assert gaps[22] == 15
