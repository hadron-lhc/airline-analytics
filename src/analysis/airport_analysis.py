from collections import Counter, defaultdict
from statistics import mean


def airport_congestion(events):
    arrivals = Counter()
    departures = Counter()
    for e in events:
        airport = e.get("airport")
        if not airport:
            continue
        if e["event"] == "Arrive_Airport":
            arrivals[airport] += 1
        elif e["event"] == "Exit_Airport":
            departures[e.get("airport", airport)] += 1
    return arrivals, departures


def gate_utilization(events):
    gate_time = defaultdict(list)
    for e in events:
        if e["event"] == "Passenger_Boarded":
            gate_time[e.get("airport", "unknown")].append(
                e.get("flight", "unknown")
            )
    return {k: len(v) for k, v in gate_time.items()}


def security_peak_hours(events):
    from datetime import datetime
    fmt = "%Y-%m-%d %H:%M:%S"
    hours = Counter()
    for e in events:
        if e["event"] == "Security_Completed":
            t = datetime.strptime(e["time"], fmt)
            hours[t.hour] += 1
    return hours


def busiest_airport(events):
    arrivals, departures = airport_congestion(events)
    total = arrivals + departures
    return total.most_common(1)[0] if total else ("N/A", 0)
