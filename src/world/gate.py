from dataclasses import dataclass


@dataclass(slots=True)
class Gate:
    gate_code: str
