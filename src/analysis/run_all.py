from ..simulation.result import SimulationResult
from .passenger_analysis import (
    average_time_at_airport,
    average_checkin_time,
    average_security_time,
    average_boarding_time,
    lost_flights,
    passenger_experience_score,
)
from .flight_analysis import (
    average_load_factor,
    boarding_duration,
    flight_status_summary,
)
from .airport_analysis import (
    airport_congestion,
    security_peak_hours,
    busiest_airport,
)


def run_all(events_path: str):
    events = SimulationResult.load_event_dicts(events_path)

    print("=" * 60)
    print("  PASSENGER ANALYSIS")
    print("=" * 60)
    print(f"  Avg time at airport:  {average_time_at_airport(events):.1f} min")
    print(f"  Avg check-in wait:   {average_checkin_time(events):.1f} min")
    print(f"  Avg security wait:   {average_security_time(events):.1f} min")
    print(f"  Avg boarding time:   {average_boarding_time(events):.1f} min")
    missed, total = lost_flights(events)
    print(f"  Lost flights:        {missed}/{total} ({missed/total*100:.1f}%)")
    print(f"  Experience score:    {passenger_experience_score(events)}/100")

    print()
    print("=" * 60)
    print("  FLIGHT ANALYSIS")
    print("=" * 60)
    print(f"  Avg load factor:     {average_load_factor(events):.1f}%")
    print(f"  Avg boarding time:   {boarding_duration(events):.1f} min")
    print(f"  Status summary:      {dict(flight_status_summary(events))}")

    print()
    print("=" * 60)
    print("  AIRPORT ANALYSIS")
    print("=" * 60)
    arrivals, departures = airport_congestion(events)
    peak = security_peak_hours(events)
    busiest, busiest_count = busiest_airport(events)
    print(f"  Busiest airport:     {busiest} ({busiest_count} events)")
    print(f"  Security peak hour:  {peak.most_common(1)[0][0]:02d}:00")
    print()


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "data/exports/simulation_2026_07_13.json"
    run_all(path)
