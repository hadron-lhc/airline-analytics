from dataclasses import dataclass, field
from datetime import timedelta, datetime
import json
import os

from ..world.simulation_world import SimulationWorld
from .event import SimulationEvent

from ..world.passenger import Passenger
from ..world.flight import Flight

from ..enums.simulation_enums import EventType


_ZONE_BY_EVENT = {
    EventType.ARRIVE_AIRPORT: "entrance",
    EventType.ARRIVE_CHECK_IN: "check_in",
    EventType.CHECK_IN_COMPLETED: "check_in",
    EventType.ARRIVE_SECURITY: "security",
    EventType.SECURITY_STARTED: "security",
    EventType.SECURITY_COMPLETED: "security",
    EventType.ARRIVE_GATE: "gate",
    EventType.BOARDING_STARTED: "gate",
    EventType.PASSENGER_BOARDED: "gate",
    EventType.MISSED_FLIGHT: "gate",
    EventType.AIRCRAFT_TAKE_OFF: "aircraft",
    EventType.AIRCRAFT_LANDED: "aircraft",
    EventType.EXIT_AIRCRAFT: "aircraft",
    EventType.EXIT_AIRPORT: "exit",
}

_STATE_BY_EVENT = {
    EventType.ARRIVE_AIRPORT: "At Airport",
    EventType.ARRIVE_CHECK_IN: "Check In",
    EventType.CHECK_IN_COMPLETED: "Check In",
    EventType.ARRIVE_SECURITY: "At Security",
    EventType.SECURITY_STARTED: "At Security",
    EventType.SECURITY_COMPLETED: "At Security",
    EventType.ARRIVE_GATE: "Waiting Gate",
    EventType.PASSENGER_BOARDED: "On Flight",
    EventType.MISSED_FLIGHT: "Missed Flight",
    EventType.EXIT_AIRCRAFT: "At Destination Airport",
    EventType.EXIT_AIRPORT: "Exited Airport",
}

_METRIC_ALIASES = {
    "arrival_margin": "arrival_margin",
    "queue_wait": "wait_seconds",
    "service_time": "service_time",
    "queue_length": "queue_length",
    "checkin_occupancy": "checkin_occupancy",
    "checkin_congested": "checkin_congested",
    "security_occupancy": "security_occupancy",
    "security_congested": "security_congested",
    "time_pressure": "time_pressure",
    "walking_speed": "walking_speed",
    "distance": "distance",
    "walking_time": "walking_time",
    "stress": "stress",
}


def _zone_alias(event: SimulationEvent) -> str | None:
    zone = _ZONE_BY_EVENT.get(event.event_type)
    if zone == "gate":
        gate = event.payload.get("gate")
        if isinstance(gate, str) and gate:
            return f"gate_{gate}"
        if gate is not None and getattr(gate, "gate_code", None):
            return f"gate_{gate.gate_code}"
    return zone


def _metric_columns(payload: dict) -> dict[str, float]:
    columns = {}
    for source, alias in _METRIC_ALIASES.items():
        if source in payload:
            columns[alias] = payload[source]
    return columns


@dataclass(slots=True)
class SimulationResult:
    world: SimulationWorld | None
    events: list[SimulationEvent]
    initial_world: SimulationWorld | None = None

    def to_event_dicts(self) -> list[dict]:
        result = []

        for event in self.events:
            entry = {
                "time": event.event_time.strftime("%Y-%m-%d %H:%M:%S"),
                "event": event.event_type.value,
            }

            zone = _zone_alias(event)
            if zone is not None:
                entry["zone"] = zone

            state = _STATE_BY_EVENT.get(event.event_type)
            if state is not None:
                entry["state"] = state

            # --------------------------------------------------
            # PASSENGER
            # --------------------------------------------------

            if isinstance(event.entity, Passenger):
                entry["entity"] = "passenger"
                entry["id"] = str(event.entity.passenger_id)

                flight = event.payload.get("flight_number")
                airport = event.payload.get("airport")

                if flight is not None:
                    entry["flight"] = flight

                if airport is not None:
                    entry["airport"] = airport

                boarding_group = event.payload.get("boarding_group")
                if boarding_group is not None:
                    entry["boarding_group"] = boarding_group

                entry.update(_metric_columns(event.payload))

            # --------------------------------------------------
            # FLIGHT
            # --------------------------------------------------

            elif isinstance(event.entity, Flight):
                entry["entity"] = "flight"
                entry["id"] = event.entity.flight_number

                entry["airport"] = event.entity.origin_airport.iata_code

            result.append(entry)

        return result

    def save_events(self, path: str | None = None) -> str:
        if path is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"simulation_{stamp}.json"
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_event_dicts(), f, indent=2, ensure_ascii=False)
        return path

    @property
    def duration(self) -> timedelta:
        if not self.events:
            return timedelta(0)
        inicio_simulacion = min(event.event_time for event in self.events)
        fin_simulacion = max(event.event_time for event in self.events)
        return fin_simulacion - inicio_simulacion

    @staticmethod
    def load_event_dicts(path: str) -> list[dict]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
