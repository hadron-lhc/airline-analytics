from .clock import SimulationClock
from .event import SimulationEvent

from dataclasses import dataclass


@dataclass(slots=True)
class SimulationEngine:
    clock: SimulationClock
    events: list[SimulationEvent]

    def add_event(self, event: SimulationEvent):
        self.events.append(event)
        self.events.sort(key=lambda e: e.event_time)

    def run(self):
        while self.events:
            event = self.events.pop(0)
            delta = event.event_time - self.clock.current_time
            self.clock.advance_time(delta)
            self.process_event(event)

    def process_event(self, event: SimulationEvent):
        print(
            f"Processing event: {event.event_type} at {event.event_time} for entity {event.entity}"
        )
