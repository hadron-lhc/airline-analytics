"""Builds the operational report of an airline simulation.

build_report() aggregates metrics (already computed by the web build tracker)
together with world and event data into a JSON-serializable dict.
render_markdown() produces a terminal-readable report.

Usage from web/build_snapshots.py:
    report = build_report(meta, final_metrics, world, result)
    markdown = render_markdown(report)
"""

from __future__ import annotations

from datetime import datetime

from ..enums.simulation_enums import EventType

# Threshold (min) below which a flight is still considered on time.
ON_TIME_THRESHOLD_MIN = 15


def _scalar(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _avg(values: list[float]) -> float:
    return (sum(values) / len(values)) if values else 0.0


def _baggage_and_stow(result) -> dict:
    """Average baggage wait and stow time from the events."""
    baggage_waits: list[float] = []
    stow_times: list[float] = []

    for event in result.events:
        payload = event.payload or {}
        if event.event_type == EventType.EXIT_AIRPORT:
            bw = payload.get("baggage_wait")
            if isinstance(bw, (int, float)):
                baggage_waits.append(float(bw))
        elif event.event_type == EventType.PASSENGER_BOARDED:
            st = payload.get("stow_time")
            if isinstance(st, (int, float)):
                stow_times.append(float(st))

    return {
        "avg_baggage_wait_s": round(_avg(baggage_waits), 1),
        "checked_passengers": len(baggage_waits),
        "avg_stow_s": round(_avg(stow_times), 1),
    }


def _peak_hour(airport: dict) -> str | None:
    """Hour of the day with the maximum average wait at an airport."""
    hours = airport.get("hours") or {}
    if not hours:
        return None
    return max(
        hours.items(),
        key=lambda item: _scalar(item[1].get("wait_avg_s")),
    )[0]


def build_report(meta: dict, metrics: dict, world, result) -> dict:
    """Builds the full report (dict serializable to JSON)."""
    final = metrics
    operational = final.get("operational", {})
    stress = final.get("stress", {})

    boarded = int(operational.get("boarded", 0))
    missed = int(operational.get("missed", 0))
    completed = int(operational.get("completed", 0))
    total_pax = boarded + missed

    security = final.get("security", {})
    checkin = final.get("checkin", {})

    def _queue_rows(states: dict) -> list[dict]:
        rows = []
        for code, s in sorted(states.items()):
            if not s.get("processed"):
                continue
            rows.append(
                {
                    "airport": code,
                    "processed": s.get("processed", 0),
                    "wait_avg_s": s.get("wait_avg_s", 0.0),
                    "wait_p90_s": s.get("wait_p90_s", 0.0),
                    "wait_max_s": s.get("wait_max_s", 0.0),
                    "congested_pct": s.get("congested_pct", 0.0),
                    "peak_hour": _peak_hour(s),
                }
            )
        rows.sort(key=lambda r: -_scalar(r["wait_p90_s"]))
        return rows

    # Flight table sorted by departure time.
    flights = []
    for fn, f in (operational.get("flight") or {}).items():
        flights.append(
            {
                "flight": fn,
                "origin": f.get("origin", "?"),
                "destination": f.get("destination", "?"),
                "dep": f.get("dep", ""),
                "sched_arr": f.get("arr", ""),
                "capacity": f.get("capacity", 0),
                "load_factor": f.get("load_factor", 0.0),
                "boarded": f.get("boarded", 0),
                "missed": f.get("missed", 0),
                "on_time": bool(f.get("on_time", True)),
                "delay_min": f.get("delay_min", 0.0),
            }
        )
    flights.sort(key=lambda f: f["dep"])

    start = meta.get("start")
    end = meta.get("end")

    def _hour(t: str | None) -> str | None:
        if not t:
            return None
        try:
            return datetime.fromisoformat(t).strftime("%H:%M")
        except ValueError:
            return t

    baggage = _baggage_and_stow(result)

    return {
        "meta": {
            "title": meta.get("title", "Airline Day"),
            "date": (start[:10] if start else None),
            "start": _hour(start),
            "end": _hour(end),
            "passengers": meta.get("passengers", 0),
            "flights": meta.get("flights", 0),
            "airports": meta.get("airports", {}),
            "events": meta.get("total_events", 0),
        },
        "resumen": {
            "boarded": boarded,
            "missed": missed,
            "missed_rate": round((missed / total_pax) if total_pax else 0.0, 3),
            "completed": completed,
            "completed_pct": round(
                (completed / total_pax) * 100.0 if total_pax else 0.0, 1
            ),
            "avg_origin_min": operational.get("avg_origin_min", 0.0),
            "on_time_rate": operational.get("on_time_rate", 0.0),
            "avg_delay_min": operational.get("avg_delay_min", 0.0),
            "load_factor_avg": operational.get("load_factor_avg", 0.0),
            "boarding_avg_stress": stress.get("boarding_avg", 0.0),
            "high_pressure_pct": stress.get("high_pressure_pct", 0.0),
        },
        "colas": {
            "security": _queue_rows(security),
            "checkin": _queue_rows(checkin),
        },
        "experiencia": {
            **stress,
            **baggage,
        },
        "cohortes": [
            {
                "purpose": purpose,
                **c,
            }
            for purpose, c in (final.get("cohorts") or {}).items()
        ],
        "vuelos": flights,
        "heatmap": {
            "security": {
                code: [
                    [int(h), _scalar(b["wait_avg_s"])]
                    for h, b in sorted((s.get("hours") or {}).items())
                ]
                for code, s in sorted(security.items())
                if s.get("processed")
            },
            "checkin": {
                code: [
                    [int(h), _scalar(b["wait_avg_s"])]
                    for h, b in sorted((s.get("hours") or {}).items())
                ]
                for code, s in sorted(checkin.items())
                if s.get("processed")
            },
        },
    }


# ----------------------------------------------------------------------
# Markdown
# ----------------------------------------------------------------------


def _fmt_queue_rows(rows: list[dict]) -> str:
    lines = ["| Airport | Processed | Avg wait | P90 | Max | Congested | Peak hour |"]
    lines.append("|---|---|---:|---:|---:|---:|---|")
    for r in rows:
        lines.append(
            f"| {r['airport']} | {r['processed']:,} "
            f"| {r['wait_avg_s']:.0f}s | {r['wait_p90_s']:.0f}s | "
            f"{r['wait_max_s']:.0f}s | {r['congested_pct']:.0f}% "
            f"| {r['peak_hour'] or '—'}h |"
        )
    return "\n".join(lines)


def _fmt_flight_rows(flights: list[dict]) -> str:
    lines = ["| Flight | Route | Dep | Arr | Cap. | Load | Boarded | Missed | On-time | Delay |"]
    lines.append("|---|---|---|---|---:|---:|---:|---:|:---:|---:|")
    for f in flights:
        lines.append(
            f"| {f['flight']} | {f['origin']}→{f['destination']} "
            f"| {f['dep']} | {f['sched_arr']} | {f['capacity']} "
            f"| {f['load_factor']:.0f}% | {f['boarded']} | {f['missed']} "
            f"| {'Yes' if f['on_time'] else 'No'} | {f['delay_min']:.0f}m |"
        )
    return "\n".join(lines)


def _fmt_heatmap(data: dict) -> str:
    if not data:
        return "_no data_"
    airports = list(data)
    hours = sorted({h for rows in data.values() for h, _ in rows})
    header = "".join(f"{h:>5}" for h in hours)
    lines = [f"{'':<6}|" + header]
    for code in airports:
        by_hour = dict(data[code])
        cells = "".join(
            f"{by_hour.get(h, 0):5.0f}" for h in hours
        )
        lines.append(f"{code:<6} |{cells}")
    return "\n".join(lines)


def render_markdown(report: dict) -> str:
    meta = report["meta"]
    res = report["resumen"]
    exp = report["experiencia"]

    lines: list[str] = []
    lines.append(f"# {meta['title']}")
    lines.append("")
    lines.append(
        f"**Date:** {meta['date']}  ·  **Window:** {meta['start']}–{meta['end']}  "
        f"·  **Passengers:** {meta['passengers']:,}  ·  **Flights:** {meta['flights']}  "
        f"·  **Airports:** {len(meta['airports'])}  ·  **Events:** {meta['events']:,}"
    )
    lines.append("")

    lines.append("## Operational summary")
    lines.append("")
    lines.append(
        f"- **Boarded:** {res['boarded']:,} ({res['completed_pct']:.0f}% "
        f"completed the cycle) · **Missed:** {res['missed']:,} "
        f"({res['missed_rate'] * 100:.1f}%)"
    )
    lines.append(
        f"- **Avg origin-to-gate time:** {res['avg_origin_min']:.0f} min "
        f"· **On-time:** {res['on_time_rate']:.0f}% "
        f"· **Avg delay:** {res['avg_delay_min']:.1f} min "
        f"· **Avg load factor:** {res['load_factor_avg']:.0f}%"
    )
    lines.append(
        f"- **Avg boarding stress:** {res['boarding_avg_stress']:.0f} "
        f"· **Passengers under high pressure:** {res['high_pressure_pct']:.0f}%"
    )
    lines.append("")

    lines.append("## Security queues")
    lines.append("")
    lines.append(_fmt_queue_rows(report["colas"]["security"]))
    lines.append("")

    lines.append("## Check-in queues")
    lines.append("")
    lines.append(_fmt_queue_rows(report["colas"]["checkin"]))
    lines.append("")

    lines.append("## Experience")
    lines.append("")
    lines.append(
        f"- **Avg boarding stress:** {exp.get('boarding_avg', 0.0):.0f} "
        f"· **stressed:** {exp.get('boarding_stressed_pct', 0.0):.0f}%"
    )
    lines.append(
        f"- **Avg baggage wait:** {exp.get('avg_baggage_wait_s', 0.0):.0f} s "
        f"(passengers with checked bags: {exp.get('checked_passengers', 0):,}) "
        f"· **Avg stow at boarding:** {exp.get('avg_stow_s', 0.0):.0f} s"
    )
    lines.append("")

    if report["cohortes"]:
        lines.append("## Cohorts by travel purpose")
        lines.append("")
        lines.append("| Purpose | Boarded | Missed | Miss rate | Avg wait | Stress |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for c in report["cohortes"]:
            lines.append(
                f"| {c['purpose']} | {c['boarded']} | {c['missed']} "
                f"| {c['missed_rate'] * 100:.1f}% | {c['avg_wait']:.0f}s "
                f"| {c['avg_stress']:.0f} |"
            )
        lines.append("")

    lines.append(f"## Flights ({len(report['vuelos'])} operated)")
    lines.append("")
    lines.append(_fmt_flight_rows(report["vuelos"]))
    lines.append("")

    lines.append("## Average wait heatmap by airport and hour (seconds)")
    lines.append("")
    lines.append("### Security")
    lines.append("")
    lines.append(_fmt_heatmap(report["heatmap"]["security"]))
    lines.append("")
    lines.append("### Check-in")
    lines.append("")
    lines.append(_fmt_heatmap(report["heatmap"]["checkin"]))
    lines.append("")

    return "\n".join(lines)