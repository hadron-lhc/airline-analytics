from datetime import datetime

from .clock import SimulationClock
from .event import SimulationEvent
from .logger import SimulationLogger

from .handlers.passenger_handler import passenger_handler
from .handlers.flight_handler import flight_handler

from ..world.passenger import Passenger
from ..world.flight import Flight
from ..world.simulation_world import SimulationWorld

from dataclasses import dataclass, field


@dataclass(slots=True)
class SimulationEngine:
    world: SimulationWorld | None = None
    clock: SimulationClock = field(
        default_factory=lambda: SimulationClock(datetime.now())
    )
    events: list[SimulationEvent] = field(default_factory=list)
    processed_events: list[SimulationEvent] = field(default_factory=list)
    logger: SimulationLogger | None = None

    def add_event(self, event: SimulationEvent):
        self.events.append(event)
        self.events.sort(key=lambda e: e.event_time)

    def load_events(self, events: list[SimulationEvent]):
        self.events = events
        self.events.sort(key=lambda e: e.event_time)

    def run(self):
        while self.events:
            event = self.events.pop(0)

            self.processed_events.append(event)

            delta = event.event_time - self.clock.current_time
            self.clock.advance(delta)

            self.dispatch(event)

        if self.logger:
            self.logger.show_summary()

    def dispatch(self, event: SimulationEvent):
        if isinstance(event.entity, Flight):
            handler = flight_handler

        elif isinstance(event.entity, Passenger):
            handler = passenger_handler

        else:
            return

        handler.process(event)

        if self.logger:
            self.logger.log(event)
