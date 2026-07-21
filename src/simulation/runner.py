from datetime import datetime

from ..world.simulation_world import SimulationWorld

from .engine import SimulationEngine
from .logger import SimulationLogger
from .event_factory import generate_events
from .result import SimulationResult


def run_simulation(
    world: SimulationWorld,
    logger: SimulationLogger | None = None,
) -> SimulationResult:
    start = datetime.now()

    events = generate_events(world)
    engine = SimulationEngine(world, logger=logger)
    engine.load_events(events)

    result_events = list(events)

    engine.run()

    duration = datetime.now() - start

    return SimulationResult(
        world=world,
        events=result_events,
        duration=duration,
    )
