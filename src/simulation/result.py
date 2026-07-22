from dataclasses import dataclass, field
from datetime import timedelta, datetime
import json
import os

from ..world.simulation_world import SimulationWorld
from .event import SimulationEvent

from ..world.passenger import Passenger
from ..world.flight import Flight


@dataclass(slots=True)
class SimulationResult:
    world: SimulationWorld
    events: list[SimulationEvent]

    def to_event_dicts(self) -> list[dict]:
        result = []
        for e in self.events:
            entry = {
                "time": e.event_time.strftime("%Y-%m-%d %H:%M:%S"),
                "event": e.event_type.value,
            }
            if isinstance(e.entity, Passenger):
                entry["entity"] = "passenger"
                entry["id"] = str(e.entity.passenger_id)
                flight = e.payload.get("flight")
                if flight:
                    entry["flight"] = flight.flight_number
                    entry["airport"] = flight.origin_airport.iata_code
            elif isinstance(e.entity, Flight):
                entry["entity"] = "flight"
                entry["id"] = e.entity.flight_number
                entry["airport"] = e.entity.origin_airport.iata_code
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
