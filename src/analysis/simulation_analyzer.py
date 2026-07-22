from dataclasses import dataclass
from ..simulation.result import SimulationResult


@dataclass(slots=True)
class SimulationAnalyzer:
    result: SimulationResult

    @property
    def world(self):
        return self.result.world

    @property
    def events(self):
        return self.result.events

    @property
    def flight_load_factors(self):
        return {
            flight.flight_number: flight.load_factor for flight in self.world.flights
        }
