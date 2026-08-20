from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..enums.simulation_enums import EventType


@dataclass(slots=True)
class SimulationEvent:
    event_time: datetime
    event_type: EventType
    entity: Any
    payload: dict[str, Any] = field(default_factory=dict)
