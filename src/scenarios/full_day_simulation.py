from datetime import datetime

from ..simulation.world_factory import generate_world
from ..simulation.event_factory import generate_events

from ..simulation.engine import SimulationEngine
from ..simulation.clock import SimulationClock

from ..simulation.result import SimulationResult

from ..analysis.simulation_analyzer import SimulationAnalyzer


def main():
    print("=" * 60)
    print("GENERATING WORLD")
    print("=" * 60)

    """
        n_airports: int,
        n_flights: int,
        n_passengers: int,

    """

    world = generate_world(
        n_airports=12,
        n_flights=20,
        n_passengers=100,
    )

    print(
        f"""
World:
  Airports:   {len(world.airports)}
  Flights:    {len(world.flights)}
  Passengers: {len(world.passengers)}
  Bookings:   {len(world.bookings)}
"""
    )

    print("=" * 60)
    print("GENERATING EVENTS")
    print("=" * 60)

    events = generate_events(world)

    print(f"Generated events: {len(events)}")

    engine = SimulationEngine(
        clock=SimulationClock(
            current_time=datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        )
    )

    engine.load_events(events)

    print("=" * 60)
    print("RUNNING SIMULATION")
    print("=" * 60)

    engine.run()

    result = SimulationResult(
        world=world,
        events=engine.processed_events,
    )

    analyzer = SimulationAnalyzer(result)

    print("=" * 60)
    print("SIMULATION FINISHED")
    print("=" * 60)

    print(
        f"""
Passengers: {result.world.passenger_count()}
Flights:    {result.world.flight_count()}
Bookings:   {result.world.booking_count()}
Events:     {len(result.events)}
"""
    )

    print("\nFlight Load Factors:")
    for flight, lf in analyzer.flight_load_factors.items():
        print(f"  {flight}: {lf}%")


if __name__ == "__main__":
    main()
