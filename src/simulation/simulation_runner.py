from .event import SimulationEvent
from .generators.passenger_journey import PassengerJourney
from .generators.flight_journey import generate_flight_journey
from .result import SimulationResult

from ..world.booking import Booking
from ..loaders.airport_layout_loader import load_airport_layout


class SimulationRunner:
    def __init__(self):
        self.passenger_journey = PassengerJourney()

    def run(
        self,
        bookings: list[Booking],
    ) -> SimulationResult:
        events: list[SimulationEvent] = []

        # --------------------------------------------------
        # PASSENGER EVENTS
        # --------------------------------------------------

        layouts = {}

        for booking in bookings:
            airport_code = booking.flight.origin_airport.iata_code

            if airport_code not in layouts:
                layouts[airport_code] = load_airport_layout(airport_code)

            layout = layouts[airport_code]

            passenger_events = self.passenger_journey.run(
                booking=booking,
                airport_layout=layout,
            )

            events.extend(passenger_events)

        # --------------------------------------------------
        # FLIGHT EVENTS
        # --------------------------------------------------

        flights = list(
            {
                booking.flight.flight_number: booking.flight for booking in bookings
            }.values()
        )

        for flight in flights:
            events.extend(generate_flight_journey(flight))

        # --------------------------------------------------
        # SORT GLOBAL TIMELINE
        # --------------------------------------------------

        events.sort(key=lambda event: event.event_time)

        return SimulationResult(
            world=None,
            events=events,
        )
