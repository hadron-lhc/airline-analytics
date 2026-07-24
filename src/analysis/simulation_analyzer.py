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

    # ── Revenue Block ──────────────────────────────────────────────

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

    # ── Legacy stubs (to be implemented next) ──────────────────────

    def flight_load_factors(self):
        return {
            flight.flight_number: flight.load_factor for flight in self.world.flights
        }

    def average_load_factor(self):
        pass

    def passengers_by_country(self):
        pass

    def passengers_by_airport(self):
        pass

    def busiest_airports(self):
        pass

    def most_popular_routes(self):
        pass

    def average_passenger_age(self):
        pass

    def seat_distribution(self):
        pass

    def travel_class_distribution(self):
        pass

    def boarding_times(self):
        pass

    def checkin_statistics(self):
        pass
