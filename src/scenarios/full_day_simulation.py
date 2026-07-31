from copy import deepcopy
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
        n_flights=2,
        n_passengers=150,
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

    initial_world = deepcopy(world)

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
        initial_world=initial_world,
    )

    analyzer = SimulationAnalyzer(result)

    print("=" * 60)
    print("SIMULATION FINISHED")
    print("=" * 60)

    world = result.world
    print(f"""
  Airports:   {len(world.airports)}
  Flights:    {len(world.flights)}
  Passengers: {len(world.passengers)}
  Bookings:   {len(world.bookings)}
  Events:     {len(result.events)}
""")

    # ── REVENUE BLOCK ──
    print("=" * 60)
    print("  REVENUE ANALYSIS")
    print("=" * 60)
    print(f"  Total revenue:        ${analyzer.total_revenue():,.2f}")
    print(f"  Avg ticket price:     ${analyzer.average_ticket_price():,.2f}")
    print(f"  Revenue by airline:   {analyzer.revenue_by_airline()}")
    print(f"  Revenue by route:     {analyzer.revenue_by_route()}")
    print(f"  Revenue by airport:   {analyzer.revenue_by_airport()}")
    print(f"  Revenue by class:     {analyzer.revenue_by_travel_class()}")
    print(f"  Top 3 flights:        {analyzer.highest_revenue_flights(3)}")
    print(f"  Bottom 3 flights:     {analyzer.lowest_revenue_flights(3)}")

    # ── FLIGHT BLOCK ──
    print("\n" + "=" * 60)
    print("  FLIGHT ANALYSIS")
    print("=" * 60)
    print(f"  Flight stats:         {analyzer.flight_statistics()}")
    print(f"  Avg load factor:      {analyzer.average_load_factor():.2%}")
    print(f"  Most full (top 3):    {analyzer.most_full_flights(3)}")
    print(f"  Least full (top 3):   {analyzer.least_full_flights(3)}")
    print(f"  Departures/airport:   {analyzer.departures_by_airport()}")
    print(f"  Arrivals/airport:     {analyzer.arrivals_by_airport()}")
    print(f"  Operations/airport:   {analyzer.flight_operations_by_airport()}")
    print(f"  Routes:               {analyzer.flight_count_by_route()}")

    # ── AIRPORT BLOCK ──
    print("\n" + "=" * 60)
    print("  AIRPORT ANALYSIS")
    print("=" * 60)
    print(f"  Airport stats:        {analyzer.airport_statistics()}")
    print(f"  Busiest airports:     {analyzer.busiest_airports(5)}")
    print(f"  Least busy:           {analyzer.least_busy_airports(5)}")
    print(f"  Operations per gate:  {analyzer.operations_per_gate()}")

    # ── PASSENGER BLOCK ──
    print("\n" + "=" * 60)
    print("  PASSENGER ANALYSIS")
    print("=" * 60)
    print(f"  Passenger stats:      {analyzer.passenger_statistics()}")
    print(f"  Age distribution:     {analyzer.passenger_age_distribution()}")
    print(f"  Nationalities:        {analyzer.passenger_nationalities()}")
    print(f"  Loyalty:              {analyzer.loyalty_distribution()}")
    print(f"  Preferred seat:       {analyzer.preferred_seat_distribution()}")
    print(f"  Arrival margin:       {analyzer.arrival_margin_distribution()}")
    print(f"  Walking speed:        {analyzer.walking_speed_distribution()}")
    print(f"  Travel experience:    {analyzer.travel_experience_distribution()}")
    print(f"  Check-in ratio:       {analyzer.checked_in_ratio():.2%}")
    print(f"  Boarded ratio:        {analyzer.boarded_ratio():.2%}")
    print(f"  Online check-in:      {analyzer.online_checkin_ratio():.2%}")
    print(f"  Baggage ratio:        {analyzer.baggage_ratio():.2%}")
    print(f"  Boarding success:     {analyzer.boarding_success_ratio():.2%}")
    print(f"  Exit airport:         {analyzer.exit_airport_ratio():.2%}")

    # ── EVENTS BLOCK ──
    print("\n" + "=" * 60)
    print("  EVENTS ANALYSIS")
    print("=" * 60)
    print(f"  Event stats:           {analyzer.event_statistics()}")
    print(f"  Events by hour:        {dict(sorted(analyzer.events_by_hour().items()))}")
    print(f"  Events by type:        {analyzer.events_by_type()}")
    print(f"  Peak activity hour:    {analyzer.peak_activity_hour()}:00")
    print(f"  Passenger events:      {len(analyzer.passenger_events())}")
    print(f"  Flight events:         {len(analyzer.flight_events())}")


if __name__ == "__main__":
    main()
