from copy import deepcopy

from ..world.simulation_world import SimulationWorld

from .simulation_runner import SimulationRunner
from .logger import SimulationLogger
from .result import SimulationResult


def run_simulation(
    world: SimulationWorld,
    logger: SimulationLogger | None = None,
) -> SimulationResult:
    """
    Run a full simulation over a world.

    Delegates to SimulationRunner so passenger journeys share
    airport resources chronologically. The initial world is
    captured so the result supports SimulationReplay.
    """

    runner = SimulationRunner()

    result = runner.run(world.bookings)

    result.initial_world = deepcopy(world) if result.initial_world is None else result.initial_world

    return result
