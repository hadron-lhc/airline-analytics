from dataclasses import dataclass
from .gate import Gate


@dataclass(slots=True)
class Airport:
    iata_code: str
    name: str
    gates: list[Gate]
