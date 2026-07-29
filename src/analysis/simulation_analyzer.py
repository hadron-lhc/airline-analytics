from dataclasses import dataclass
from datetime import date
from collections import defaultdict
from statistics import mean

from ..simulation.result import SimulationResult
from ..simulation.event import SimulationEvent
from ..world.flight import Flight
from ..world.passenger import Passenger
from ..enums.world_enums import PassengerState
from ..enums.simulation_enums import EventType


@dataclass(slots=True)
class SimulationAnalyzer:
    result: SimulationResult

    @property
    def world(self):
        return self.result.world

    @property
    def events(self):
        return self.result.events

    # --- Helpers ----------------------------------------------------

    def _flight_revenues(self) -> dict[str, float]:
        rev = defaultdict(float)
        for b in self.world.bookings:
            rev[b.flight.flight_number] += b.ticket_price
        return dict(rev)

    def _load_factors(self) -> dict[str, float]:
        load_factors = {}
        for flight in self.world.flights:
            load_factors[flight.flight_number] = flight.load_factor
        return load_factors

    def _airport_operations(self) -> dict[str, int]:
        return self.flight_operations_by_airport()

    def _airport_gate_counts(self) -> dict[str, int]:
        return {a.iata_code: len(a.gates) for a in self.world.airports}

    def _airport_flights(self) -> dict[str, list[Flight]]:
        groups: dict[str, list[Flight]] = defaultdict(list)
        for f in self.world.flights:
            groups[f.origin_airport.iata_code].append(f)
        return dict(groups)

    def _passenger_ages(self) -> list[int]:
        today = date.today()
        return [
            (today - p.birth_date).days // 365
            for p in self.world.passengers
            if p.birth_date
        ]

    # --- Revenue Block ---------------------------------------------

    def total_revenue(self) -> float:
        return sum(b.ticket_price for b in self.world.bookings)

    def average_ticket_price(self) -> float:
        return mean(b.ticket_price for b in self.world.bookings)

    def revenue_by_airline(self) -> dict[str, float]:
        rev = defaultdict(float)
        for b in self.world.bookings:
            rev[b.flight.airline_code] += b.ticket_price
        return dict(rev)

    def revenue_by_route(self) -> dict[tuple[str, str], float]:
        rev = defaultdict(float)
        for b in self.world.bookings:
            route = (
                b.flight.origin_airport.iata_code,
                b.flight.destination_airport.iata_code,
            )
            rev[route] += b.ticket_price
        return dict(rev)

    def revenue_by_airport(self) -> dict[str, float]:
        rev = defaultdict(float)
        for b in self.world.bookings:
            rev[b.flight.origin_airport.iata_code] += b.ticket_price
        return dict(rev)

    def revenue_by_travel_class(self) -> dict[str, float]:
        rev = defaultdict(float)
        for b in self.world.bookings:
            rev[b.travel_class.value] += b.ticket_price
        return dict(rev)

    def highest_revenue_flights(self, n: int = 10) -> list[tuple[str, float]]:
        rev = self._flight_revenues()
        return sorted(rev.items(), key=lambda x: x[1], reverse=True)[:n]

    def lowest_revenue_flights(self, n: int = 10) -> list[tuple[str, float]]:
        rev = self._flight_revenues()
        return sorted(rev.items(), key=lambda x: x[1])[:n]

    # --- Flight Block ------------------------------------------------------

    def flight_load_factors(self) -> dict[str, float]:
        return self._load_factors()

    def average_load_factor(self) -> float:
        lfs = list(self._load_factors().values())
        return sum(lfs) / len(lfs) if lfs else 0.0

    def most_full_flights(self, n: int = 10) -> list[tuple[str, float]]:
        return sorted(self._load_factors().items(), key=lambda x: x[1], reverse=True)[
            :n
        ]

    def least_full_flights(self, n: int = 10) -> list[tuple[str, float]]:
        return sorted(self._load_factors().items(), key=lambda x: x[1])[:n]

    def departures_by_airport(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for f in self.world.flights:
            counts[f.origin_airport.iata_code] += 1
        return dict(counts)

    def arrivals_by_airport(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for f in self.world.flights:
            counts[f.destination_airport.iata_code] += 1
        return dict(counts)

    def flight_operations_by_airport(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for f in self.world.flights:
            counts[f.origin_airport.iata_code] += 1
            counts[f.destination_airport.iata_code] += 1
        return dict(counts)

    def flight_count_by_route(self) -> dict[tuple[str, str], int]:
        counts: dict[tuple[str, str], int] = defaultdict(int)
        for f in self.world.flights:
            counts[f.origin_airport.iata_code, f.destination_airport.iata_code] += 1
        return dict(counts)

    def flight_statistics(self) -> dict:
        flights = self.world.flights
        count = len(flights)
        avg_lf = self.average_load_factor()
        durations = [
            (f.scheduled_arrival - f.scheduled_departure).total_seconds() / 60
            for f in flights
        ]
        revenues = self._flight_revenues()
        avg_duration = mean(durations) if durations else 0.0
        avg_revenue = mean(revenues.values()) if revenues else 0.0
        total_revenue = sum(revenues.values())
        lf_dict = self._load_factors()
        most_full = max(lf_dict, key=lf_dict.get) if lf_dict else None
        least_full = min(lf_dict, key=lf_dict.get) if lf_dict else None
        return {
            "count": count,
            "average_load_factor": round(avg_lf, 2),
            "average_duration": round(avg_duration),
            "average_revenue": round(avg_revenue),
            "total_revenue": round(total_revenue),
            "most_full": most_full,
            "least_full": least_full,
        }

    # --- Airport Block ----------------------------------------

    def operations_per_gate(self) -> dict[str, float]:
        ops = self._airport_operations()
        gates = self._airport_gate_counts()
        return {code: round(ops.get(code, 0) / gates[code], 2) for code in gates}

    def busiest_airports(self, n: int = 10) -> list[tuple[str, int]]:
        ops = self._airport_operations()
        return sorted(ops.items(), key=lambda x: x[1], reverse=True)[:n]

    def least_busy_airports(self, n: int = 10) -> list[tuple[str, int]]:
        ops = self._airport_operations()
        return sorted(ops.items(), key=lambda x: x[1])[:n]

    def airport_statistics(self) -> dict:
        airports = self.world.airports
        ops = self._airport_operations()
        gates = self._airport_gate_counts()
        util = self.operations_per_gate()

        busiest = max(ops, key=ops.get) if ops else None
        quietest = min(ops, key=ops.get) if ops else None

        return (
            {
                "count": len(airports),
                "total_operations": sum(ops.values()),
                "busiest": busiest,
                "quietest": quietest,
                "average_gates": round(mean(gates.values()), 1) if gates else 0.0,
                "average_operations_per_gate": round(mean(util.values()), 2)
                if util
                else 0.0,
            },
        )

    # --- Passenger Block --------------------------------

    def passenger_age_distribution(self) -> dict[str, int]:
        buckets: dict[str, int] = defaultdict(int)
        for age in self._passenger_ages():
            if age <= 18:
                buckets["0-18"] += 1
            elif age <= 30:
                buckets["19-30"] += 1
            elif age <= 50:
                buckets["31-50"] += 1
            else:
                buckets["51+"] += 1
        return dict(buckets)

    def passenger_nationalities(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for p in self.world.passengers:
            counts[p.nationality] += 1
        return dict(counts)

    def loyalty_distribution(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for p in self.world.passengers:
            counts[p.loyalty_level.value] += 1
        return dict(counts)

    def preferred_seat_distribution(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for p in self.world.passengers:
            counts[p.preferred_seat] += 1
        return dict(counts)

    def arrival_margin_distribution(self) -> dict[str, int]:
        buckets: dict[str, int] = defaultdict(int)
        for p in self.world.passengers:
            m = p.arrival_margin
            if m < 60:
                buckets["< 60"] += 1
            elif m <= 90:
                buckets["60–90"] += 1
            elif m <= 120:
                buckets["90–120"] += 1
            elif m <= 180:
                buckets["120–180"] += 1
            else:
                buckets["> 180"] += 1
        return dict(buckets)

    def walking_speed_distribution(self) -> dict[str, int]:
        buckets: dict[str, int] = defaultdict(int)
        for p in self.world.passengers:
            s = p.walking_speed
            if s < 1.0:
                buckets["< 1.0"] += 1
            elif s <= 1.2:
                buckets["1.0–1.2"] += 1
            elif s <= 1.4:
                buckets["1.2–1.4"] += 1
            else:
                buckets["> 1.4"] += 1
        return dict(buckets)

    def travel_experience_distribution(self) -> dict[int, int]:
        counts: dict[int, int] = defaultdict(int)
        for p in self.world.passengers:
            counts[p.travel_experience] += 1
        return dict(counts)

    def checked_in_ratio(self) -> float:
        if not self.world.passengers:
            return 0.0
        checked = sum(1 for p in self.world.passengers if p.checked_in)
        return checked / len(self.world.passengers)

    def boarded_ratio(self) -> float:
        if not self.world.passengers:
            return 0.0
        boarded = sum(1 for p in self.world.passengers if p.boarded)
        return boarded / len(self.world.passengers)

    def online_checkin_ratio(self) -> float:
        if not self.world.passengers:
            return 0.0
        online = sum(1 for p in self.world.passengers if p.checked_in)
        return online / len(self.world.passengers)

    def baggage_ratio(self) -> float:
        if not self.world.bookings:
            return 0.0
        with_baggage = sum(1 for b in self.world.bookings if b.checked_baggage > 0)
        return with_baggage / len(self.world.bookings)

    def boarding_success_ratio(self) -> float:
        return self.boarded_ratio()

    def exit_airport_ratio(self) -> float:
        if not self.world.passengers:
            return 0.0
        exited = sum(
            1 for p in self.world.passengers
            if p.state == PassengerState.EXITED_AIRPORT
        )
        return exited / len(self.world.passengers)

    def passenger_statistics(self) -> dict:
        passengers = self.world.passengers
        ages = self._passenger_ages()
        loyalties = self.loyalty_distribution()
        top_loyalty = max(loyalties, key=loyalties.get) if loyalties else None
        nationalities = self.passenger_nationalities()
        top_nationality = max(nationalities, key=nationalities.get) if nationalities else None
        margins = [p.arrival_margin for p in passengers]
        speeds = [p.walking_speed for p in passengers]

        return {
            "count": len(passengers),
            "average_age": round(mean(ages), 1) if ages else 0.0,
            "average_arrival_margin": round(mean(margins), 1) if margins else 0.0,
            "average_walking_speed": round(mean(speeds), 2) if speeds else 0.0,
            "checked_in_ratio": round(self.checked_in_ratio(), 2),
            "boarded_ratio": round(self.boarded_ratio(), 2),
            "top_nationality": top_nationality,
            "top_loyalty": top_loyalty,
        }

    # --- Events Block ------------------------------------------------

    def event_count(self) -> int:
        return len(self.events)

    def events_by_type(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for e in self.events:
            counts[e.event_type.value] += 1
        return dict(counts)

    def events_by_hour(self) -> dict[int, int]:
        counts: dict[int, int] = defaultdict(int)
        for e in self.events:
            counts[e.event_time.hour] += 1
        return dict(counts)

    def passenger_events(self) -> list[SimulationEvent]:
        return [e for e in self.events if isinstance(e.entity, Passenger)]

    def flight_events(self) -> list[SimulationEvent]:
        return [e for e in self.events if isinstance(e.entity, Flight)]

    def peak_activity_hour(self) -> int | None:
        by_hour = self.events_by_hour()
        return max(by_hour, key=by_hour.get) if by_hour else None

    def event_statistics(self) -> dict:
        by_hour = self.events_by_hour()
        by_type = self.events_by_type()
        top_type = max(by_type, key=by_type.get) if by_type else None
        peak = max(by_hour, key=by_hour.get) if by_hour else None
        n_passenger = len(self.passenger_events())
        n_flight = len(self.flight_events())

        return {
            "total_events": self.event_count(),
            "event_types": len(by_type),
            "most_frequent_event": top_type,
            "peak_activity_hour": peak,
            "peak_activity_count": by_hour.get(peak, 0) if peak else 0,
            "passenger_events": n_passenger,
            "flight_events": n_flight,
        }
