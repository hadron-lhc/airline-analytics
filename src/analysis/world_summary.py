import unicodedata

from ..world.simulation_world import SimulationWorld
from ..simulation.result import SimulationResult


def _display_width(text: str) -> int:
    return sum(
        2 if unicodedata.east_asian_width(c) in ("W", "F") else 1
        for c in text
    )


def _pad(text: str, width: int) -> str:
    return text + " " * max(0, width - _display_width(text))


def print_world_summary(world: SimulationWorld):
    active_airports = len({f.origin_airport.iata_code for f in world.flights})

    print("=" * 66)
    print("  WORLD SUMMARY")
    print("=" * 66)
    print(f"  Airports:")
    print(f"    Total:        {len(world.airports)}")
    print(f"    Active today: {active_airports}")
    print(f"  Flights:        {len(world.flights)}")
    print(f"  Passengers:     {len(world.passengers)}")
    print(f"  Bookings:       {len(world.bookings)}")
    print("=" * 66)

    for flight in world.flights:
        n_bookings = len(flight.bookings)
        print(
            f"\n  {flight.flight_number}  {flight.origin_airport.iata_code} \u2192 "
            f"{flight.destination_airport.iata_code}  "
            f"{flight.scheduled_departure.strftime('%H:%M')}  "
            f"Gate {flight.gate.gate_code}  "
            f"({n_bookings}/{flight.capacity})"
        )
        print(f"  {'─' * 66}")
        for booking in flight.bookings:
            p = booking.passenger
            name = f"{p.first_name} {p.last_name}"
            seat = booking.seat.seat_number if booking.seat else "N/A"
            print(
                f"    {_pad(name, 25)} {booking.travel_class.value:<15} "
                f"{seat:>4}  ${booking.ticket_price:>8,.2f}"
            )

    print()


def print_statistics(result: SimulationResult):
    print("=" * 66)
    print("  STATISTICS")
    print("=" * 66)
    result.world.statistics()
    print(f"\n  Simulation duration: {result.duration}")
    print()
