from dataclasses import dataclass
from collections import defaultdict
from statistics import mean

from ..simulation.result import SimulationResult


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

    def _load_factors(self):
        load_factors = {}
        for flight in self.world.flights:
            load_factors[flight.flight_number] = flight.load_factor
        return load_factors

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
        load_factors = self._load_factors()
        return load_factors

    def average_load_factor(self) -> float:
        lfs = list(self._load_factors().values())
        return sum(lfs) / len(lfs) if lfs else 0.0

    def most_full_flights(self, n: int = 10) -> list[tuple[str, float]]:
        return sorted(self._load_factors().items(), key=lambda x: x[1], reverse=True)[
            :n
        ]

    def least_full_flights(self, n: int = 10) -> list[tuple[str, float]]:
        return sorted(self._load_factors().items(), key=lambda x: x[1])[:n]

    def flight_count_by_airline(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for f in self.world.flights:
            counts[f.airline_code] += 1
        return dict(counts)

    def flight_count_by_airport(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for f in self.world.flights:
            counts[f.origin_airport.iata_code] += 1
        return dict(counts)
