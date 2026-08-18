from dataclasses import dataclass
from .position import Position


@dataclass(slots=True)
class AirportLocation:
    code: str
    position: Position
