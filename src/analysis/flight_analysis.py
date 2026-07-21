from collections import Counter
from statistics import mean
from datetime import datetime


def average_delay(events):
    delays = {}
    fmt = "%Y-%m-%d %H:%M:%S"
    for e in events:
        if e["event"] == "Aircraft_Take_Off" and e["entity"] == "flight":
            delays[e["id"]] = e["time"]
    if not delays:
        return 0
    return mean(list(delays.values()))  


def average_load_factor(events):
    capacities = Counter()
    boardings = Counter()
    for e in events:
        if e["event"] == "Boarding_Started" and e["entity"] == "flight":
            capacities[e["id"]] = 200  
        elif e["event"] == "Passenger_Boarded":
            boardings[e.get("flight", e["id"])] += 1
    if not capacities:
        return 0
    factors = [
        boardings.get(fid, 0) / cap * 100
        for fid, cap in capacities.items()
    ]
    return mean(factors) if factors else 0


def boarding_duration(events):
    starts = {}
    durations = []
    fmt = "%Y-%m-%d %H:%M:%S"
    for e in events:
        if e["event"] == "Boarding_Started" and e["entity"] == "flight":
            starts[e["id"]] = datetime.strptime(e["time"], fmt)
        elif e["event"] == "Aircraft_Take_Off" and e["entity"] == "flight":
            fid = e["id"]
            if fid in starts:
                d = (datetime.strptime(e["time"], fmt) - starts[fid]).total_seconds() / 60
                durations.append(d)
    return mean(durations) if durations else 0


def flight_status_summary(events):
    statuses = Counter()
    for e in events:
        if e["entity"] == "flight" and e["event"] in ("Aircraft_Landed", "Aircraft_Take_Off", "Boarding_Started"):
            statuses[e["event"]] += 1
    return statuses
