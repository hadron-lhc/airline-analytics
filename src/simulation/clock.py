from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(slots=True)
class SimulationClock:
    current_time: datetime

    def advance(self, delta: timedelta):
        self.current_time += delta

    def advance_to(self, new_time: datetime):
        if new_time < self.current_time:
            raise ValueError("Cannot advance to a time in the past.")
        self.current_time = new_time
