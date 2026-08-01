from datetime import timedelta

from ..simulation.world_factory import generate_world
from ..simulation.runner import run_simulation
from ..simulation.replay import SimulationReplay
from ..analysis.simulation_analyzer import SimulationAnalyzer
from ..render.console_renderer import ConsoleRenderer


def main():
    world = generate_world(
        n_airports=8,
        n_flights=2,
        n_passengers=60,
    )

    result = run_simulation(world)

    replay = SimulationReplay(result)

    print("=" * 66)
    print("  TIMELINE")
    print("=" * 66)
    print(f"  Frames: {replay.frame_count}")
    print(f"  Start:  {replay.start_time}")
    print(f"  End:    {replay.end_time}")
    print(f"  Progress inicial: {replay.progress:.0%}")

    for frame in replay.timeline[:5]:
        print(
            f"    [{frame.index}] {frame.time} "
            f"{frame.event_type.value:<20} "
            f"{frame.entity_kind:<10} {frame.entity_id}"
        )

    print()
    print("=" * 66)
    print("  PLAYING THROUGH THE WHOLE SIMULATION")
    print("=" * 66)
    while replay.has_next():
        replay.step()
    print(f"  Progress final: {replay.progress:.0%}")
    print(f"  Index final:    {replay.current_index}")

    print()
    print("=" * 66)
    print("  SEEK TO THE MIDDLE AND ANALYZE")
    print("=" * 66)
    replay.seek(replay.frame_count // 2)
    current = replay.current_event
    print(f"  Event: {current.event_type.value} @ {current.event_time}")
    print(f"  Progress: {replay.progress:.0%}")

    analyzer = SimulationAnalyzer(replay.current_result)
    bookings = replay.current_world.bookings
    checked = sum(1 for b in bookings if b.checked_in)
    boarded = sum(1 for b in bookings if b.boarded)
    print(f"  Bookings con check-in:    {checked}/{len(bookings)}")
    print(f"  Bookings con boarding:    {boarded}/{len(bookings)}")
    print(f"  Revenue acumulado:        ${analyzer.total_revenue():,.2f}")

    print()
    print("=" * 66)
    print("  AT A SPECIFIC TIME")
    print("=" * 66)
    midpoint = replay.start_time + (replay.end_time - replay.start_time) / 2
    replay.at(midpoint)
    s = replay.summary()
    print(f"  Requested time:   {midpoint:%H:%M:%S}")
    print(f"  Simulation time:  {s['current_time']:%H:%M:%S}")
    print()
    print("  Current state established by:")
    if s["current_event"]:
        print(f"    {s['current_event'].value.replace('_', ' ')} @ {s['event_time']:%H:%M}")
    else:
        print("    (initial world)")
    if s["next_event"]:
        print("  Next event:")
        print(f"    {s['next_event'].value.replace('_', ' ')} @ {s['next_event_time']:%H:%M}")
    else:
        print("  Next event:      (fin)")
    if s["idle"] is not None:
        idle_min = int(s["idle"].total_seconds() // 60)
        h, m = divmod(idle_min, 60)
        idle = f"{h}h {m}m" if h else f"{m}m"
        print(f"  Idle for:        {idle}")
    print(f"  Event progress:  {s['event_progress']:.0%}")
    print(f"  Timeline:        {s['time_progress']:.0%}")

    print()
    print("=" * 66)
    print("  WORLD SUMMARY")
    print("=" * 66)
    replay.print_summary()

    print()
    print("=" * 66)
    print("  AIRPORT RENDERER")
    print("=" * 66)
    renderer = ConsoleRenderer()
    airport_code = world.flights[0].origin_airport.iata_code
    print(renderer.render_airport(replay.current_world, airport_code, replay.current_time))


if __name__ == "__main__":
    main()
