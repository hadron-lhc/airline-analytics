from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(slots=True)
class SimulationClock:
    current_time: datetime

    def advance_time(self, delta: timedelta):
        self.current_time += delta
