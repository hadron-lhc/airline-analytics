from copy import deepcopy

from .event import SimulationEvent
from .generators.passenger_journey import (
    PassengerJourney,
    PassengerJourneyContext,
)
from .generators.flight_journey import generate_flight_journey
from .result import SimulationResult

from ..world.booking import Booking
from ..world.simulation_world import SimulationWorld
from ..loaders.airport_layout_loader import load_airport_layout

from .queues.security_queue import SecurityQueue
from .queues.checkin_queue import CheckInQueue
from ..world.models.queue_service_model import QueueServiceModel

from ..enums.simulation_enums import EventType
from ..enums.world_enums import FlightMilestone


class SimulationRunner:
    """
    Coordinates the global simulation.

    PassengerJourney calculates individual passenger movement.

    Shared resources such as SecurityQueue are coordinated here,
    in chronological order.
    """

    def __init__(self):
        self.queue_service_model = QueueServiceModel()

        self.passenger_journey = PassengerJourney(
            queue_service_model=self.queue_service_model,
        )

        self.security_queues: dict[str, SecurityQueue] = {}
        self.checkin_queues: dict[str, CheckInQueue] = {}

    # ==========================================================
    # CHECK-IN QUEUE
    # ==========================================================

    def _get_checkin_queue(
        self,
        airport_code: str,
    ) -> CheckInQueue:
        if airport_code not in self.checkin_queues:
            self.checkin_queues[airport_code] = CheckInQueue(
                queue_service_model=self.queue_service_model,
            )

        return self.checkin_queues[airport_code]

    # ==========================================================
    # SECURITY QUEUE
    # ==========================================================

    def _get_security_queue(
        self,
        airport_code: str,
    ) -> SecurityQueue:
        if airport_code not in self.security_queues:
            self.security_queues[airport_code] = SecurityQueue(
                queue_service_model=self.queue_service_model,
            )

        return self.security_queues[airport_code]

    # ==========================================================
    # RUN
    # ==========================================================

    def run(
        self,
        bookings: list[Booking],
    ) -> SimulationResult:
        all_events: list[SimulationEvent] = []

        # ------------------------------------------------------
        # 1. LOAD AIRPORT LAYOUTS
        # ------------------------------------------------------

        layouts = {}

        for booking in bookings:
            airport_code = booking.flight.origin_airport.iata_code

            if airport_code not in layouts:
                layouts[airport_code] = load_airport_layout(airport_code)

        # ------------------------------------------------------
        # 2. PREPARE ALL PASSENGER JOURNEYS
        # ------------------------------------------------------

        contexts: list[PassengerJourneyContext] = []

        for booking in bookings:
            airport_code = booking.flight.origin_airport.iata_code

            layout = layouts[airport_code]

            context = self.passenger_journey.prepare(
                booking=booking,
                airport_layout=layout,
            )

            contexts.append(context)

        # ------------------------------------------------------
        # 3. PROCESS CHECK-IN QUEUES
        # ------------------------------------------------------

        contexts.sort(key=lambda context: context.check_in_arrival)

        for context in contexts:
            airport_code = context.booking.flight.origin_airport.iata_code

            checkin_queue = self._get_checkin_queue(airport_code)

            checkin_result = checkin_queue.process(
                passenger=context.booking.passenger,
                arrival_time=context.check_in_arrival,
            )

            self.passenger_journey.continue_after_checkin(
                context=context,
                checkin_result=checkin_result,
            )

        # ------------------------------------------------------
        # 4. SORT BY SECURITY ARRIVAL
        # ------------------------------------------------------

        contexts.sort(key=lambda context: context.security_arrival)

        # ------------------------------------------------------
        # 5. PROCESS SECURITY QUEUES
        # ------------------------------------------------------

        for context in contexts:
            airport_code = context.booking.flight.origin_airport.iata_code

            security_queue = self._get_security_queue(airport_code)

            security_result = security_queue.process(
                passenger=context.booking.passenger,
                arrival_time=context.security_arrival,
            )

            passenger_events = self.passenger_journey.continue_after_security(
                context=context,
                security_result=security_result,
            )

            all_events.extend(passenger_events)

        # ------------------------------------------------------
        # 6. FLIGHT EVENTS
        # ------------------------------------------------------

        flights = list(
            {
                booking.flight.flight_number: booking.flight for booking in bookings
            }.values()
        )

        for flight in flights:
            all_events.extend(generate_flight_journey(flight))

        # ------------------------------------------------------
        # 7. ARRIVAL PHASE (EXIT_AIRCRAFT → EXIT_AIRPORT)
        # ------------------------------------------------------

        destination_layouts = {}

        boarded_ids = {
            event.entity.passenger_id
            for event in all_events
            if event.event_type == EventType.PASSENGER_BOARDED
        }

        for booking in bookings:
            if booking.passenger.passenger_id not in boarded_ids:
                continue

            flight = booking.flight
            destination_code = flight.destination_airport.iata_code

            if destination_code not in destination_layouts:
                destination_layouts[
                    destination_code
                ] = load_airport_layout(destination_code)

            landed_time = flight.get_milestone(FlightMilestone.LANDED)

            arrival_events = self.passenger_journey.after_boarding(
                booking=booking,
                airport_layout=destination_layouts[destination_code],
                landed_time=landed_time,
            )

            all_events.extend(arrival_events)

        # ------------------------------------------------------
        # 8. GLOBAL TIMELINE
        # ------------------------------------------------------

        all_events.sort(key=lambda event: event.event_time)

        world = self._build_world(bookings)

        return SimulationResult(
            world=world,
            events=all_events,
            initial_world=deepcopy(world) if world is not None else None,
        )

    # ==========================================================
    # WORLD
    # ==========================================================

    def _build_world(
        self,
        bookings: list[Booking],
    ) -> SimulationWorld | None:
        """
        Reconstruct a SimulationWorld from the bookings.

        The world contains every passenger, flight and airport
        referenced by the bookings so that SimulationReplay can
        re-bind events to deep copies.
        """

        if not bookings:
            return None

        passengers: dict = {}
        flights: dict = {}
        airports: dict = {}

        for booking in bookings:
            passenger = booking.passenger
            passengers[passenger.passenger_id] = passenger

            flight = booking.flight
            flights[flight.flight_number] = flight
            airports[flight.origin_airport.iata_code] = flight.origin_airport
            airports[flight.destination_airport.iata_code] = flight.destination_airport

        return SimulationWorld(
            airports=list(airports.values()),
            flights=list(flights.values()),
            passengers=list(passengers.values()),
            bookings=bookings,
        )
