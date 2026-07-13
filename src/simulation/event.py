from dataclasses import dataclass, field
from datetime import datetime

from ..enums.simulation_enums import EventType


@dataclass(slots=True)
class SimulationEvent:
    event_time: datetime
    event_type: EventType
    entity: any
    payload: dict = field(default_factory=dict)
