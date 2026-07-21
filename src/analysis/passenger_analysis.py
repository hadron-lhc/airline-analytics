from collections import Counter
from statistics import mean


def _filter(events, *types):
    return [e for e in events if e["event"] in types]


def _times(events, event_a, event_b):
    pairs = []
    by_id = {}
    for e in events:
        eid = e["id"]
        if e["event"] == event_a and eid not in by_id:
            by_id[eid] = {"start": e["time"]}
        elif e["event"] == event_b and eid in by_id and "end" not in by_id[eid]:
            by_id[eid]["end"] = e["time"]
            pairs.append(by_id.pop(eid))
    return pairs


def minutes_between(t1, t2):
    from datetime import datetime
    fmt = "%Y-%m-%d %H:%M:%S"
    d1 = datetime.strptime(t1, fmt)
    d2 = datetime.strptime(t2, fmt)
    return (d2 - d1).total_seconds() / 60


def average_time_at_airport(events):
    pairs = _times(events, "Arrive_Airport", "Exit_Airport")
    if not pairs:
        return 0
    mins = [minutes_between(p["start"], p["end"]) for p in pairs]
    return mean(mins)


def average_checkin_time(events):
    pairs = _times(events, "Arrive_Airport", "Check_In_Completed")
    if not pairs:
        return 0
    mins = [minutes_between(p["start"], p["end"]) for p in pairs]
    return mean(mins)


def average_security_time(events):
    pairs = _times(events, "Check_In_Completed", "Security_Completed")
    if not pairs:
        return 0
    mins = [minutes_between(p["start"], p["end"]) for p in pairs]
    return mean(mins)


def average_boarding_time(events):
    pairs = _times(events, "Boarding_Started", "Passenger_Boarded")
    if not pairs:
        return 0
    mins = [minutes_between(p["start"], p["end"]) for p in pairs]
    return mean(mins)


def lost_flights(events):
    boarded = {e["id"] for e in events if e["event"] == "Passenger_Boarded"}
    all_passengers = {e["id"] for e in events if e["entity"] == "passenger"}
    missed = all_passengers - boarded
    return len(missed), len(all_passengers)


def passenger_experience_score(events):
    total_time = average_time_at_airport(events)
    checkin = average_checkin_time(events)
    security = average_security_time(events)
    boarding = average_boarding_time(events)
    missed, total = lost_flights(events)
    board_pct = (total - missed) / total * 100 if total else 0

    score = 100
    score -= max(0, (total_time - 120) * 0.2)
    score -= max(0, (checkin - 10) * 0.5)
    score -= max(0, (security - 15) * 0.3)
    score -= max(0, (boarding - 5) * 0.5)
    if board_pct < 95:
        score -= (95 - board_pct) * 2

    return max(0, round(score, 1))
