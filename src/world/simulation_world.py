from dataclasses import dataclass
from datetime import date
from statistics import mean
from collections import Counter

from .airport import Airport
from .flight import Flight
from .passenger import Passenger
from .booking import Booking


def _seat_type(seat_number: str) -> str:
    letter = seat_number[-1]
    if letter in ("A", "F"):
        return "Window"
    if letter in ("B", "E"):
        return "Middle"
    return "Aisle"


@dataclass(slots=True)
class SimulationWorld:
    airports: list[Airport]
    flights: list[Flight]
    passengers: list[Passenger]
    bookings: list[Booking]

    def passenger_count(self) -> int:
        return len(self.passengers)

    def flight_count(self) -> int:
        return len(self.flights)

    def booking_count(self) -> int:
        return len(self.bookings)

    def statistics(self):
        today = date.today()
        prices = [b.ticket_price for b in self.bookings]
        load_factors = [
            len(f.bookings) / f.capacity * 100 for f in self.flights if f.capacity
        ]
        ages = [
            (today - p.birth_date).days // 365 for p in self.passengers if p.birth_date
        ]
        origins = Counter(f.origin_airport.iata_code for f in self.flights)
        active = len(origins)
        classes = Counter(b.travel_class.value for b in self.bookings)
        seats = Counter(_seat_type(b.seat.seat_number) for b in self.bookings if b.seat)

        print(f"  Flights:           {len(self.flights)}")
        print(f"  Passengers:        {len(self.passengers)}")
        print(f"  Bookings:          {len(self.bookings)}")
        print(f"  Average ticket:    ${mean(prices):,.2f}" if prices else "")
        print(f"  Average load:      {mean(load_factors):.1f}%" if load_factors else "")
        print(f"  Average age:       {mean(ages):.0f}" if ages else "")
        print()
        print(f"  Airports:          {len(self.airports)} ({active} active)")
        for code, count in sorted(origins.items()):
            print(f"    {code:<6}: {count}")
        print()
        print("  Travel classes:")
        for cls, count in sorted(classes.items()):
            print(f"    {cls:<15}: {count}")
        print()
        print("  Seat preference:")
        for seat_type in ("Window", "Middle", "Aisle"):
            print(f"    {seat_type:<10}: {seats.get(seat_type, 0)}")
