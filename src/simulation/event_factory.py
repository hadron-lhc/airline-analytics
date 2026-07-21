from ..world.simulation_world import SimulationWorld

from .generators.flight_journey import generate_flight_journey
from .generators.passenger_journey import generate_passenger_journey


def generate_events(world: SimulationWorld):
    events = []

    for flight in world.flights:
        events.extend(generate_flight_journey(flight))

    for booking in world.bookings:
        events.extend(generate_passenger_journey(booking))

    events.sort(key=lambda e: e.event_time)

    return events
