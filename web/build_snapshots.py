"""Build spatial + metric snapshots from a simulation for the static web timeline.

Usage (terminal):
    python web/build_snapshots.py [--n-passengers 1000] [--step-min 5] [--sql]
    python web/build_snapshots.py --saturate --margin 60     # pico de cola de seguridad
    python web/build_snapshots.py --full-day --step-min 15   # red completa, día entero

Writes a self-contained static site into ``web/dist/``:
    dist/index.html
    dist/js/{app.js,style.css}
    dist/vendor/chart.umd.js
    dist/data/meta.json
    dist/data/snapshots.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parent
ROOT_DIR = WEB_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.enums.simulation_enums import EventType
from src.enums.world_enums import PassengerState
from src.loaders.airport_layout_loader import load_airport_layout
STATIC_DIR = WEB_DIR / "static"
DIST_DIR = WEB_DIR / "dist"
DATA_DIR = DIST_DIR / "data"

# Airports whose layout JSON may be missing are rendered with a generic grid.
_GENERIC_ZONES = {
    "entrance": ((8.0, 78.0), (5.0, 4.0)),
    "check_in": ((28.0, 42.0), (8.0, 6.0)),
    "security": ((48.0, 42.0), (8.0, 6.0)),
    "gate": ((70.0, 40.0), (12.0, 16.0)),
    "destination": ((86.0, 78.0), (9.0, 6.0)),
    "exited": ((86.0, 16.0), (5.0, 4.0)),
}
_GENERIC_GATES: dict[str, tuple[float, float]] = {}


# ----------------------------------------------------------------------
# Passenger state -> (group, zone) mapping
# ----------------------------------------------------------------------

# group: where the passenger is at a high level (for global counters)
# zone:  zone label inside its airport (or "air" / "ground" / "exited")
_STATE_INFO = {
    PassengerState.AT_HOME: ("at_home", "home"),
    PassengerState.GOING_TO_AIRPORT: ("to_airport", "to_airport"),
    PassengerState.AT_AIRPORT: ("origin", "entrance"),
    PassengerState.CHECK_IN: ("origin", "check_in"),
    PassengerState.AT_SECURITY: ("origin", "security"),
    PassengerState.WAITING_GATE: ("origin", "gate"),
    PassengerState.BOARDING: ("origin", "gate"),
    PassengerState.ON_FLIGHT: ("air", "air"),
    PassengerState.ARRIVED: ("destination", "destination"),
    PassengerState.AT_DESTINATION_AIRPORT: ("destination", "destination"),
    PassengerState.EXITED_AIRPORT: ("exited", "exited"),
}

ZONES = ["entrance", "check_in", "security", "gate", "destination", "exited"]


def _airport_for(passenger, state: PassengerState, flight_by_number: dict) -> str | None:
    """Return the airport code where this passenger is, if any.

    Arrival group uses ``passenger.current_airport`` (set by the AIRCRAFT_LANDED
    handler), so destination airports show up even after ``current_booking`` is
    cleared on EXIT_AIRPORT.
    """
    booking = passenger.current_booking
    flight = booking.flight if booking else None

    group = _STATE_INFO[state][0]
    if group == "origin":
        if flight is None:
            return None
        return flight.origin_airport.iata_code

    if group in ("destination", "exited"):
        code = passenger.current_airport
        if isinstance(code, str):
            return code
        if flight is not None:
            return flight.destination_airport.iata_code
        if passenger.last_flight and passenger.last_flight in flight_by_number:
            return flight_by_number[
                passenger.last_flight
            ].destination_airport.iata_code
        return None

    return None


def _gate_for(passenger) -> str | None:
    gate = getattr(passenger, "current_gate", None)
    if gate is not None:
        return getattr(gate, "gate_code", None)
    return None


# ----------------------------------------------------------------------
# Real airport geometry (from src/data/airports/*.json, normalized to %)
# ----------------------------------------------------------------------

_geometry_cache: dict[str, dict] = {}


def _layout_geometry(airport_code: str) -> dict:
    """Zone/gate coordinates in [0, 100]² for an airport floor plan.

    Returns {"zones": {zone: {"c": [x, y], "r": [rx, ry]}},
            "gates": {gate_code: [x, y]}, "flow": [...]}.
    """
    cached = _geometry_cache.get(airport_code)
    if cached is not None:
        return cached

    try:
        layout = load_airport_layout(airport_code)
    except (FileNotFoundError, ValueError):
        geometry = {
            "zones": {
                z: {"c": list(c), "r": list(r)}
                for z, (c, r) in _GENERIC_ZONES.items()
            },
            "gates": dict(_GENERIC_GATES),
            "flow": ["entrance", "check_in", "security", "gate"],
        }
        _geometry_cache[airport_code] = geometry
        return geometry

    def norm(location_code: str) -> tuple[float, float]:
        loc = layout.locations[location_code].position
        return (
            round(loc.x / layout.width * 100, 2),
            round(loc.y / layout.height * 100, 2),
        )

    zone_centers: dict[str, tuple[float, float]] = {}
    gates: dict[str, tuple[float, float]] = {}

    for code, loc in layout.locations.items():
        if code.startswith("gate_"):
            gates[code[5:]] = norm(code)
        elif code in ("entrance", "check_in", "security", "baggage_claim", "exit"):
            zone_centers[code] = norm(code)

    if "baggage_claim" in zone_centers:
        zone_centers["destination"] = zone_centers.pop("baggage_claim")
    if "exit" in zone_centers:
        zone_centers["exited"] = zone_centers.pop("exit")

    # Room spread ("r") per zone: fixed for halls, bounding box for gates.
    spreads = {
        "entrance": (5.0, 4.0),
        "check_in": (8.0, 6.0),
        "security": (8.0, 6.0),
        "destination": (9.0, 6.0),
        "exited": (5.0, 4.0),
    }
    if gates:
        xs = [x for x, _ in gates.values()]
        ys = [y for _, y in gates.values()]
        gate_c = (
            (min(xs) + max(xs)) / 2,
            (min(ys) + max(ys)) / 2,
        )
        spreads["gate"] = (
            max((max(xs) - min(xs)) / 2 + 1.0, 8.0),
            max((max(ys) - min(ys)) / 2 + 1.5, 12.0),
        )
    else:
        gate_c = zone_centers.get("gate") or (70.0, 40.0)
        spreads["gate"] = (12.0, 16.0)

    if "gate" not in zone_centers:
        zone_centers["gate"] = gate_c

    zones = {
        z: {"c": [round(zone_centers[z][0], 2), round(zone_centers[z][1], 2)],
            "r": list(spreads[z])}
        for z in ZONES
        if z in zone_centers
    }

    geometry = {
        "zones": zones,
        "gates": {g: [round(x, 2), round(y, 2)] for g, (x, y) in gates.items()},
        "flow": ["entrance", "check_in", "security", "gate"],
    }
    _geometry_cache[airport_code] = geometry
    return geometry


# ----------------------------------------------------------------------
# Snapshot capture
# ----------------------------------------------------------------------


def build_passenger_spatial(passengers, flights) -> dict:
    """Group passengers by global state and by airport+zone.

    "In the air" is *geographically correct*: a passenger counts as flying
    only if their flight's status is `DEPARTED` (took off, not yet landed).
    Passengers who are on board but still pre-take-off are counted at the
    origin airport (gate/aircraft).

    Returns (global_by_state, by_airport, air_by_flight).
    """
    flight_status = {f.flight_number: f.status.value for f in flights}
    flight_by_number = {f.flight_number: f for f in flights}

    global_by_state = {s.value: 0 for s in PassengerState}
    by_airport: dict[str, dict] = {}
    air_by_flight: dict[str, int] = {}

    for p in passengers:
        booking = p.current_booking
        flight = booking.flight if booking else None
        fcode = flight.flight_number if flight else None
        fstatus = flight_status.get(fcode)

        if fstatus == "Departed":
            global_by_state["On Flight"] += 1
            air_by_flight[fcode] = air_by_flight.get(fcode, 0) + 1
            continue

        state = p.state
        if state == PassengerState.ON_FLIGHT:
            # on board but not yet airborne -> at origin airport, at gate
            state = PassengerState.WAITING_GATE

        group, zone = _STATE_INFO[state]
        global_by_state[state.value] += 1

        airport_code = _airport_for(p, state, flight_by_number)
        if airport_code is None:
            continue

        apt = by_airport.setdefault(
            airport_code,
            {z: 0 for z in ZONES} | {"gates": {}, "total": 0},
        )
        apt[zone] += 1
        apt["total"] += 1

        if zone == "gate":
            gate_code = _gate_for(p) or fcode or "?"
            apt["gates"][gate_code] = apt["gates"].get(gate_code, 0) + 1

    return global_by_state, by_airport, air_by_flight


# ----------------------------------------------------------------------
# Metrics (single-pass accumulator)
# ----------------------------------------------------------------------


class _MetricsTracker:
    """Accumulates operational/security metrics in one chronological pass.

    ``feed(event)`` processes events in order; ``snapshot()`` returns the
    cumulative state up to the last fed event. The web build feeds events up
    to each snapshot tick once (total O(events + snapshots) instead of the
    previous O(snapshots * events)).
    """

    def __init__(self, airports: list[str]):
        self.airports = list(airports)
        security = {
            code: {"processed": 0, "waits": [], "max_wait": 0.0,
                   "congested": 0, "in_queue": 0}
            for code in self.airports
        }
        self._security = security
        self._index = 0
        self.boarded = 0
        self.missed = 0
        self._arrive_ts: dict[str, datetime] = {}
        self._origin_min: list[float] = []

    def feed(self, event) -> None:
        t = event.event_type
        payload = event.payload

        if t == EventType.SECURITY_STARTED:
            apt = payload.get("airport")
            if apt in self._security:
                self._security[apt]["in_queue"] += 1

        elif t == EventType.SECURITY_COMPLETED:
            apt = payload.get("airport")
            if apt in self._security:
                wait = float(payload.get("queue_wait") or 0.0)
                s = self._security[apt]
                s["processed"] += 1
                s["waits"].append(wait)
                if wait > s["max_wait"]:
                    s["max_wait"] = wait
                if payload.get("security_congested"):
                    s["congested"] += 1
                if s["in_queue"]:
                    s["in_queue"] -= 1

        elif t == EventType.ARRIVE_AIRPORT:
            pid = self._pid(event)
            if pid is not None:
                self._arrive_ts[pid] = event.event_time

        elif t == EventType.PASSENGER_BOARDED:
            self.boarded += 1
            pid = self._pid(event)
            arrive = self._arrive_ts.get(pid)
            if arrive is not None:
                self._origin_min.append(
                    (event.event_time - arrive).total_seconds() / 60.0
                )

        elif t == EventType.MISSED_FLIGHT:
            self.missed += 1

    @staticmethod
    def _pid(event):
        entity = event.entity
        return str(entity.passenger_id) if hasattr(entity, "passenger_id") else None

    def snapshot(self) -> dict:
        security_out = {}
        for code, s in self._security.items():
            avg = sum(s["waits"]) / len(s["waits"]) if s["waits"] else 0.0
            pct_congested = (
                (s["congested"] / s["processed"]) if s["processed"] else 0.0
            )
            security_out[code] = {
                "processed": s["processed"],
                "wait_avg_s": round(avg, 1),
                "wait_max_s": round(s["max_wait"], 1),
                "congested_pct": round(pct_congested * 100, 1),
                "in_queue": s["in_queue"],
            }

        avg_origin = (
            sum(self._origin_min) / len(self._origin_min)
            if self._origin_min
            else 0.0
        )
        return {
            "security": security_out,
            "operational": {
                "boarded": self.boarded,
                "missed": self.missed,
                "completed": len(self._origin_min),
                "avg_origin_min": round(avg_origin, 1),
            },
        }


def build_metrics(events, now: datetime, airports: list[str]) -> dict:
    """Aggregate per-moment metrics from the full event log up to ``now``.

    Uses the *original* events (with rich payloads including queue metrics),
    not the replayed ones.
    """
    tracker = _MetricsTracker(airports)
    for e in events:
        if e.event_time > now:
            break
        tracker.feed(e)
    return tracker.snapshot()


def build_flight_statuses(world) -> dict:
    return {
        f.flight_number: {
            "from": f.origin_airport.iata_code,
            "to": f.destination_airport.iata_code,
            "status": f.status.value,
            "on_board": f.passenger_count,
            "dep": f.scheduled_departure.strftime("%H:%M"),
            "arr": f.scheduled_arrival.strftime("%H:%M"),
        }
        for f in world.flights
    }


# ----------------------------------------------------------------------
# Airport floor-plan points (real layouts)
# ----------------------------------------------------------------------

MAX_POINTS_PER_ZONE = 60

# Scatter spread (rx%, ry%) per zone around its real position.
_ZONE_SCATTER = {
    "entrance": (5.0, 4.0),
    "check_in": (8.0, 6.0),
    "security": (8.0, 6.0),
    "gate": (4.0, 6.0),
    "destination": (9.0, 6.0),
    "exited": (5.0, 4.0),
}


def _scatter(pid: str) -> tuple[float, float]:
    """Deterministic [0,1)^2 offset for a passenger id (stable across frames)."""
    h = hashlib.md5(pid.encode()).digest()
    return h[0] / 255.0, h[1] / 255.0


def _clamp(v: float) -> float:
    return max(0.0, min(100.0, v))


def build_airport_points(passengers, flights, airport_code: str = "JFK") -> dict:
    """Floor-plan positions for passengers in the given airport.

    Coordinates come from the real layout JSON (normalized to %): halls are
    scattered around their zone center, gate passengers around their actual
    gate position (so gates stay visually separated). Deterministic per
    passenger id, so the frontend can interpolate real movement.

    If a zone has more than ``MAX_POINTS_PER_ZONE`` people, only that many are
    emitted (sampled); the per-zone total is reported in ``zones``.

    Returns {"zones": {zone: total}, "points": [{id, zone, x, y, g}]}.
    """
    geo = _layout_geometry(airport_code)
    flight_status = {f.flight_number: f.status.value for f in flights}
    flight_by_number = {f.flight_number: f for f in flights}
    counts = {z: 0 for z in ZONES}
    points = []

    for p in passengers:
        booking = p.current_booking
        flight = booking.flight if booking else None
        fstatus = flight_status.get(flight.flight_number) if flight else None
        if fstatus == "Departed":
            continue

        state = p.state
        if state == PassengerState.ON_FLIGHT:
            state = PassengerState.WAITING_GATE
        group, zone = _STATE_INFO[state]
        apt_code = _airport_for(p, state, flight_by_number)
        if apt_code != airport_code:
            continue

        counts[zone] += 1
        if counts[zone] > MAX_POINTS_PER_ZONE:
            continue

        if zone == "gate":
            gate_code = _gate_for(p)
            pos = geo["gates"].get(gate_code) or geo["zones"].get("gate", {}).get("c")
            cx, cy = pos
        else:
            region = geo["zones"].get(zone) or {"c": (50.0, 50.0)}
            cx, cy = region["c"]
        rx, ry = _ZONE_SCATTER[zone]

        pid = str(p.passenger_id)
        u1, u2 = _scatter(pid)
        x = _clamp(cx + (2 * u1 - 1) * rx)
        y = _clamp(cy + (2 * u2 - 1) * ry)
        points.append(
            {
                "id": pid[:8],
                "zone": zone,
                "x": round(x, 2),
                "y": round(y, 2),
                "g": _gate_for(p),
            }
        )

    return {"zones": counts, "points": points}


def build_meta(world, result, airport_names: dict) -> dict:
    layouts = {
        code: _layout_geometry(code)
        for code in airport_names
    }
    return {
        "title": "Airline Day — JFK hub",
        "start": result.events[0].event_time.isoformat(),
        "end": result.events[-1].event_time.isoformat(),
        "passengers": len(world.passengers),
        "flights": len(world.flights),
        "airports": {code: airport_names.get(code, code) for code in airport_names},
        "total_events": len(result.events),
        "layouts": layouts,
    }


# ----------------------------------------------------------------------
# Ticks
# ----------------------------------------------------------------------


def timeline_ticks(start: datetime, end: datetime, step_min: int) -> list[datetime]:
    """Bucketed wall-clock ticks every step_min between start and end."""
    ticks = []
    t = start.replace(second=0, microsecond=0)
    if t < start:
        t += timedelta(minutes=1)
    while t <= end:
        ticks.append(t)
        t += timedelta(minutes=step_min)
    if ticks[-1] < end:
        ticks.append(end)
    return ticks


# ----------------------------------------------------------------------
# Build driver
# ----------------------------------------------------------------------


def _airport_names() -> dict:
    from src.simulation.generators.airport_factory import AIRPORTS

    return dict(AIRPORTS)


def run(
    step_min: int = 5,
    n_passengers: int = 1000,
    saturate: bool = False,
    margin: int | None = None,
    full_day: bool = False,
) -> int:
    if full_day:
        from src.simulation.world_factory import generate_world

        world = generate_world(n_airports=12, n_flights=56, n_passengers=n_passengers)
    else:
        from src.scenarios.hub_day_simulation import build_hub_world

        world = build_hub_world(
            n_passengers=n_passengers,
            staggered=not saturate,
        )

    if margin is not None:
        for p in world.passengers:
            p.arrival_margin = margin

    from src.simulation.runner import run_simulation
    from src.simulation.replay import SimulationReplay

    result = run_simulation(world)
    replay = SimulationReplay(result)

    airport_names = _airport_names()
    all_airport_codes = [
        f.origin_airport.iata_code for f in world.flights
    ] + [f.destination_airport.iata_code for f in world.flights]
    all_airport_codes = list(dict.fromkeys(all_airport_codes))

    events = result.events
    start = events[0].event_time
    end = events[-1].event_time

    ticks = timeline_ticks(start, end, step_min)

    tracker = _MetricsTracker(all_airport_codes)
    event_index = 0
    snapshots = []
    for t in ticks:
        while event_index < len(events) and events[event_index].event_time <= t:
            tracker.feed(events[event_index])
            event_index += 1

        replay.at(t)
        cur_world = replay.current_world
        global_by_state, by_airport, air_by_flight = build_passenger_spatial(
            cur_world.passengers, cur_world.flights
        )
        air_total = sum(air_by_flight.values())

        airports_floor = {
            code: build_airport_points(cur_world.passengers, cur_world.flights, code)
            for code in by_airport
            if by_airport[code]["total"] > 0
        }

        snapshots.append(
            {
                "t": t.isoformat(),
                "global": {
                    "by_state": {
                        k: v for k, v in global_by_state.items() if v
                    },
                    "air_by_flight": air_by_flight,
                    "air_total": air_total,
                },
                "by_airport": by_airport,
                "airports": airports_floor,
                "metrics": tracker.snapshot(),
                "flights": build_flight_statuses(replay.current_world),
            }
        )

    meta = build_meta(world, result, airport_names)
    return _write(snapshots, meta)


def _write(snapshots: list[dict], meta: dict) -> int:
    # wipe and recreate dist
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True)

    DATA_DIR.mkdir(parents=True)
    (DATA_DIR / "snapshots.json").write_text(
        json.dumps(snapshots, ensure_ascii=False), encoding="utf-8"
    )
    (DATA_DIR / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False), encoding="utf-8"
    )

    dst_js = DIST_DIR / "js"
    dst_js.mkdir(parents=True)
    shutil.copy(STATIC_DIR / "app.js", dst_js / "app.js")
    shutil.copy(STATIC_DIR / "style.css", dst_js / "style.css")
    shutil.copy(STATIC_DIR / "index.html", DIST_DIR / "index.html")

    dst_vendor = DIST_DIR / "vendor"
    dst_vendor.mkdir(parents=True)
    shutil.copy(STATIC_DIR / "vendor" / "chart.umd.js", dst_vendor / "chart.umd.js")

    return len(snapshots)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step-min", type=int, default=5, help="Snapshot bucket (min)")
    parser.add_argument("--n-passengers", type=int, default=1000)
    parser.add_argument(
        "--saturate",
        action="store_true",
        help="Hub escenario: all flights depart at the same time (security spike).",
    )
    parser.add_argument(
        "--margin",
        type=int,
        default=None,
        help="Forced arrival margin for every passenger (minutes).",
    )
    parser.add_argument(
        "--full-day",
        action="store_true",
        help="Build from the full network (12 airports, 56 flights) instead of the hub.",
    )
    parser.add_argument(
        "--sql",
        action="store_true",
        help="Also load events into PostgreSQL (analysis layer).",
    )
    args = parser.parse_args()

    n = run(
        step_min=args.step_min,
        n_passengers=args.n_passengers,
        saturate=args.saturate,
        margin=args.margin,
        full_day=args.full_day,
    )
    print(f"Built web/dist with {n} snapshots.")

    if args.sql:
        from src.simulation.result import load_events_from_json  # noqa
        from src.database import load_simulation

        raise NotImplementedError(
            "SQL loading is a separate step; run "
            "src/database/load_simulation.py on the exported JSON instead."
        )


if __name__ == "__main__":
    main()