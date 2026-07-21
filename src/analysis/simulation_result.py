from dataclasses import dataclass, field

from ..world.simulation_world import SimulationWorld
from ..simulation.event import SimulationEvent


@dataclass
class SimulationResult:
    world: SimulationWorld
    events: list[SimulationEvent]

    def passenger_count(self):
        return len(self.world.passengers)

    def flight_count(self):
        return len(self.world.flights)

    def booking_count(self):
        return len(self.world.bookings)
