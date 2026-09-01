from copy import deepcopy
from datetime import datetime, timedelta

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


# Margen entre el último embarque y el despegue (stow, cierre de rampa, taxi).
_BUFFER_SECONDS = 20 * 60

# Perfil de staffing (servidores, capacidad) por franja horaria. Durante las
# ondas de salida se abren más puntos de servicio; de noche la operación
# queda mínima.
_PEAK_HOURS_START = {6, 7, 8, 9, 10, 16, 17, 18, 19, 20}
_NIGHT_HOURS = {0, 1, 2, 3, 4, 22, 23}

_SECURITY_PROFILE = {"peak": (6, 28), "off": (4, 20), "night": (2, 10)}
_CHECKIN_PROFILE = {"peak": (5, 24), "off": (3, 18), "night": (2, 8)}


def _staffing_for(time_, profile: dict) -> tuple[int, int]:
    """Devuelve (service_points, capacity) para una hora dada del día."""
    hour = time_.hour
    if hour in _PEAK_HOURS_START:
        return profile["peak"]
    if hour in _NIGHT_HOURS:
        return profile["night"]
    return profile["off"]


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

    def _configure_service(
        self,
        queue,
        current_time: datetime,
        profile: dict,
    ) -> None:
        """Ajusta el staffing de una cola según la hora del día.

        Al cambiar el número de puestos se mantiene la lista de
        ``server_available_times`` sincronizada (reservas de pasajeros en
        cola): solo se retiran puestos libres, y los nuevos puestos se
        abren disponibles.
        """
        service_points, capacity = _staffing_for(current_time, profile)

        queue.capacity = capacity

        if service_points == queue.service_points:
            return

        avail = list(queue.server_available_times)

        if len(avail) > service_points:
            busy_up_to = current_time
            kept = [
                t for t in avail if t is not None and t <= busy_up_to
            ]
            kept.extend(t for t in avail if t is None)
            avail = kept[:service_points]

        if len(avail) < service_points:
            avail.extend([None] * (service_points - len(avail)))

        queue.service_points = service_points
        queue.server_available_times = avail

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

            self._configure_service(
                checkin_queue,
                context.check_in_arrival,
                _CHECKIN_PROFILE,
            )

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

            self._configure_service(
                security_queue,
                context.security_arrival,
                _SECURITY_PROFILE,
            )

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

        # ------------------------------------------------------
        # 6a. BOARDING-GATED DEPARTURE (on-time)
        # ------------------------------------------------------
        # El despegue real depende del fin del embarque: si el último pasajero
        # embarcó tarde (colas, remplazos), la rueda-despega se retrasa. Los
        # hitos TAKE_OFF/LANDED se desplazan ANTES de generar los eventos del
        # vuelo y de la fase de llegada, para que todo el timeline sea
        # consistente ("en el aire" solo tras el despegue real).

        last_boarded: dict[str, datetime] = {}

        for event in all_events:
            if event.event_type != EventType.PASSENGER_BOARDED:
                continue
            fn = event.payload.get("flight_number")
            if isinstance(fn, str) and (
                fn not in last_boarded or event.event_time > last_boarded[fn]
            ):
                last_boarded[fn] = event.event_time

        for flight in flights:
            latest = last_boarded.get(flight.flight_number)
            if latest is None:
                continue

            scheduled = flight.get_milestone(FlightMilestone.TAKE_OFF)
            actual = max(scheduled, latest + timedelta(seconds=_BUFFER_SECONDS))

            if actual == scheduled:
                continue

            flight.milestones[FlightMilestone.TAKE_OFF] = actual
            flight.milestones[FlightMilestone.LANDED] = actual + (
                flight.scheduled_arrival - flight.scheduled_departure
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

        checked_baggage_by_flight: dict[str, int] = {}
        for booking in bookings:
            if not booking.checked_baggage:
                continue
            fn = booking.flight.flight_number
            checked_baggage_by_flight[fn] = checked_baggage_by_flight.get(fn, 0) + 1

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
                baggage_load=checked_baggage_by_flight.get(
                    flight.flight_number, 0
                ),
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
