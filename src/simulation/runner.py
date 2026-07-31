from copy import deepcopy

from ..world.simulation_world import SimulationWorld

from .engine import SimulationEngine
from .logger import SimulationLogger
from .event_factory import generate_events
from .result import SimulationResult


def run_simulation(
    world: SimulationWorld,
    logger: SimulationLogger | None = None,
) -> SimulationResult:
    events = generate_events(world)

    initial_world = deepcopy(world)

    engine = SimulationEngine(world, logger=logger)
    engine.load_events(events)

    result_events = list(events)

    engine.run()

    return SimulationResult(
        world=world,
        events=result_events,
        initial_world=initial_world,
    )
