from ..world.simulation_world import SimulationWorld

from .simulation_runner import SimulationRunner


def generate_events(world: SimulationWorld):
    """
    Generate the complete timeline of events for a world.

    Delegates to SimulationRunner so passenger journeys share
    airport resources (e.g. security queues) chronologically.
    """
    if not world.bookings:
        return []

    runner = SimulationRunner()

    result = runner.run(world.bookings)

    return result.events
