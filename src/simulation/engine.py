from datetime import datetime

from .clock import SimulationClock
from .event import SimulationEvent

from dataclasses import dataclass, field


@dataclass(slots=True)
class SimulationEngine:
    clock: SimulationClock = field(default_factory=lambda: SimulationClock(datetime.now()))
    events: list[SimulationEvent] = field(default_factory=list)

    def add_event(self, event: SimulationEvent):
        self.events.append(event)
        self.events.sort(key=lambda e: e.event_time)

    def load_events(self, events: list[SimulationEvent]):
        self.events = events
        self.events.sort(key=lambda e: e.event_time)

    def run(self):
        while self.events:
            event = self.events.pop(0)
            delta = event.event_time - self.clock.current_time
            self.clock.advance(delta)
            self.dispatch(event)

    def dispatch(self, event: SimulationEvent):
        event.entity.handler.process(event)
