"""Tests del informe operativo (build_report / render_markdown)."""

import json

from datetime import datetime

from src.analysis.report_builder import build_report, render_markdown
from src.simulation.world_factory import generate_world
from src.simulation.runner import run_simulation
from web.build_snapshots import _MetricsTracker, build_meta, _airport_names


def _report():
    world = generate_world(
        n_airports=4,
        n_flights=8,
        n_passengers=400,
        simulation_date=datetime(2026, 7, 13),
        seed=7,
    )
    result = run_simulation(world)

    codes = [f.origin_airport.iata_code for f in world.flights]
    tracker = _MetricsTracker(codes, flights=world.flights)
    for e in result.events:
        tracker.feed(e)

    meta = build_meta(world, result, _airport_names())
    return build_report(meta, tracker.snapshot(), world, result)


def test_report_sections_present():
    r = _report()

    assert set(r) >= {"meta", "resumen", "colas", "experiencia",
                      "cohortes", "vuelos", "heatmap"}
    assert set(r["resumen"]) >= {
        "boarded", "missed", "missed_rate", "on_time_rate",
        "avg_delay_min", "load_factor_avg", "completed_pct",
    }
    assert {"security", "checkin"} <= set(r["colas"])
    assert r["vuelos"], "al menos un vuelo operado"
    f = r["vuelos"][0]
    assert set(f) >= {"flight", "origin", "destination", "dep", "capacity",
                      "load_factor", "boarded", "missed", "on_time",
                      "delay_min"}

    # Puntualidad dentro de rango porcentual (0-100).
    assert 0.0 <= r["resumen"]["on_time_rate"] <= 100.0
    assert 0.0 <= r["resumen"]["load_factor_avg"] <= 100.0
    assert 0.0 <= r["resumen"]["completed_pct"] <= 100.0
    assert isinstance(r["resumen"]["avg_delay_min"], float)


def test_report_json_serializable():
    r = _report()
    dumped = json.dumps(r, ensure_ascii=False)
    loaded = json.loads(dumped)
    assert loaded["meta"]["title"] == r["meta"]["title"]
    assert loaded["vuelos"][0]["flight"] == r["vuelos"][0]["flight"]


def test_report_markdown_renders_tables():
    md = render_markdown(_report())

    assert md.startswith("# ")
    assert "## Resumen operativo" in md
    assert "## Colas de seguridad" in md
    assert "## Vuelos" in md
    assert "| Vuelo |" in md
    assert "## Heatmap" in md