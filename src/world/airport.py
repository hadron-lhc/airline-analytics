from dataclasses import dataclass, field
from datetime import datetime
from .gate import Gate


@dataclass(slots=True)
class Airport:
    iata_code: str
    name: str
    gates: list[Gate]
    _gate_bookings: dict = field(default_factory=dict, init=False, repr=False)

    def find_available_gate(
        self, start: datetime, end: datetime
    ) -> Gate | None:
        for gate in self.gates:
            bookings = self._gate_bookings.get(gate.gate_code, [])
            if all(b_end <= start or b_start >= end for b_start, b_end in bookings):
                return gate
        return None

    def book_gate(self, gate: Gate, start: datetime, end: datetime):
        self._gate_bookings.setdefault(gate.gate_code, []).append((start, end))

    def release_gate(self, gate: Gate, start: datetime, end: datetime):
        bookings = self._gate_bookings.get(gate.gate_code, [])
        if (start, end) in bookings:
            bookings.remove((start, end))
