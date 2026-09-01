from dataclasses import dataclass
from datetime import datetime, timedelta

from ...enums.simulation_enums import EventType
from ...enums.world_enums import StressEvent, FlightMilestone, BoardingGroup
from ...world.booking import Booking
from ...world.models.stress_model import StressModel
from ...world.models.walking_model import WalkingModel
from ...world.models.queue_service_model import QueueServiceModel
from ...world.airport_layout import AirportLayout

from ..event import SimulationEvent
from ..passenger_movement import PassengerMovement
from ..passenger_waiting import PassengerWaitingSimulator
from ..queues.security_queue import SecurityQueue
from ..queues.checkin_queue import CheckInQueue


# Minimum time (seconds) a passenger needs after security to
# comfortably reach the gate. Used to estimate time pressure while
# waiting in the security queue.
SECURITY_TO_GATE_BUFFER_SECONDS = 600.0

# Fracción del tramo [BOARDING_START, doors_close] que ocupa cada grupo de
# embarque. Prioridad embarque primero, grupos posteriores después.
BOARDING_WINDOW_FRACTIONS = {
    BoardingGroup.PRIORITY: (0.00, 0.15),
    BoardingGroup.GROUP_1: (0.15, 0.30),
    BoardingGroup.GROUP_2: (0.30, 0.50),
    BoardingGroup.GROUP_3: (0.50, 0.70),
    BoardingGroup.GROUP_4: (0.70, 0.85),
    BoardingGroup.GROUP_5: (0.85, 1.00),
}


def _boarding_window(flight, boarding_group):
    """
    Ventana de embarque [inicio, fin] de un grupo para un vuelo.

    El embarque va desde BOARDING_START (los pasajeros de prioridad empiezan
    antes) hasta el cierre de puertas (doors close). La ventana del grupo es
    una fracción de ese tramo.
    """
    boarding_start = flight.get_milestone(FlightMilestone.BOARDING_START)
    doors_close = flight.scheduled_departure - timedelta(minutes=15)

    span = (doors_close - boarding_start).total_seconds()

    start_frac, end_frac = BOARDING_WINDOW_FRACTIONS.get(
        boarding_group,
        BOARDING_WINDOW_FRACTIONS[BoardingGroup.GROUP_5],
    )

    window_start = boarding_start + timedelta(seconds=span * start_frac)
    window_end = boarding_start + timedelta(seconds=span * end_frac)

    return window_start, window_end


@dataclass
class PassengerJourneyContext:
    booking: Booking
    airport_layout: AirportLayout

    arrival_time: datetime
    check_in_arrival: datetime
    security_arrival: datetime

    checkin_location: object
    security_location: object
    gate_location: object

    events: list[SimulationEvent]


class PassengerJourney:
    """
    Generates and coordinates the journey of a passenger.

    The journey is divided into three stages:

        1. prepare()
           Passenger arrives and reaches the check-in counter.

        2. continue_after_checkin()
           Passenger passes check-in and reaches security.

        3. continue_after_security()
           Passenger leaves security and walks to the gate.

    The global SimulationRunner should use these stages to
    coordinate shared airport resources chronologically.

    run() is kept as a convenience method for single-passenger
    tests and backwards compatibility.
    """

    def __init__(
        self,
        walking_model: WalkingModel | None = None,
        stress_model: StressModel | None = None,
        queue_service_model: QueueServiceModel | None = None,
    ):
        self.walking_model = walking_model or WalkingModel()
        self.stress_model = stress_model or StressModel()
        self.queue_service_model = queue_service_model or QueueServiceModel()

        self.waiting_simulator = PassengerWaitingSimulator(
            stress_model=self.stress_model,
        )

        self.movement = PassengerMovement(
            walking_model=self.walking_model,
            stress_model=self.stress_model,
        )

    # ==========================================================
    # PREPARE JOURNEY
    # ==========================================================

    def prepare(
        self,
        booking: Booking,
        airport_layout: AirportLayout,
    ) -> PassengerJourneyContext:
        passenger = booking.passenger
        flight = booking.flight

        events: list[SimulationEvent] = []

        airport_code = flight.origin_airport.iata_code
        flight_number = flight.flight_number

        entrance = airport_layout.get_location("entrance")
        check_in = airport_layout.get_location("check_in")
        security = airport_layout.get_location("security")
        gate = airport_layout.get_gate_location(flight.gate.gate_code)

        def base_payload() -> dict:
            return {
                "flight": flight,
                "flight_number": flight_number,
                "airport": airport_code,
            }

        # ======================================================
        # ARRIVAL AT AIRPORT
        # ======================================================

        arrival_time = flight.scheduled_departure - timedelta(
            minutes=passenger.arrival_margin
        )

        payload = base_payload()
        payload.update(
            {
                "arrival_margin": passenger.arrival_margin,
                "stress": passenger.current_stress,
            }
        )

        events.append(
            SimulationEvent(
                event_time=arrival_time,
                event_type=EventType.ARRIVE_AIRPORT,
                entity=passenger,
                payload=payload,
            )
        )

        # ======================================================
        # ENTRANCE → CHECK-IN
        # ======================================================

        movement = self.movement.move(
            passenger=passenger,
            origin=entrance,
            destination=check_in,
        )

        check_in_arrival = arrival_time + timedelta(seconds=movement.walking_time)

        payload = base_payload()
        payload.update(
            {
                "distance": movement.distance,
                "walking_speed": movement.walking_speed,
                "walking_time": movement.walking_time,
                "stress": movement.final_stress,
            }
        )

        events.append(
            SimulationEvent(
                event_time=check_in_arrival,
                event_type=EventType.ARRIVE_CHECK_IN,
                entity=passenger,
                payload=payload,
            )
        )

        # ======================================================
        # RETURN CONTEXT (arrival + check-in reached)
        # ======================================================
        # El check-in (con cola compartida) y la llegada posterior a
        # seguridad se completan en continue_after_checkin(), donde la
        # cola de mostrador es coordinada cronológicamente por el runner.
        return PassengerJourneyContext(
            booking=booking,
            airport_layout=airport_layout,
            arrival_time=arrival_time,
            check_in_arrival=check_in_arrival,
            security_arrival=check_in_arrival,
            checkin_location=check_in,
            security_location=security,
            gate_location=gate,
            events=events,
        )

    # ==========================================================
    # CONTINUE AFTER CHECK-IN
    # ==========================================================

    def continue_after_checkin(
        self,
        context: PassengerJourneyContext,
        checkin_result,
    ) -> PassengerJourneyContext:
        """
        Complete the check-in stage and the walk to security.

        ``checkin_result`` is the output of a shared CheckInQueue
        (service_start / service_time / queue_length / ...). This emits
        CHECK_IN_COMPLETED at the end of service and ARRIVE_SECURITY
        after walking to the checkpoint, and returns the context with a
        finalized ``security_arrival``.
        """
        passenger = context.booking.passenger
        flight = context.booking.flight

        events: list[SimulationEvent] = list(context.events)

        airport_code = flight.origin_airport.iata_code
        flight_number = flight.flight_number

        def base_payload() -> dict:
            return {
                "flight": flight,
                "flight_number": flight_number,
                "airport": airport_code,
            }

        # ======================================================
        # CHECK-IN COMPLETED
        # ======================================================

        check_in_completed = checkin_result.service_end
        queue_wait = checkin_result.waiting_time

        # ======================================================
        # WAIT STRESS (check-in)
        # ======================================================
        # Mirando la parte de seguridad: mientras espera en la cola de
        # check-in, el pasajero siente presión según el tiempo que le queda
        # hasta el cierre de embarque. El waiting simulator muta
        # passenger.current_stress y el payload captura el resultado.

        checkin_waiting_result = None

        if queue_wait > 0:
            boarding_close = flight.scheduled_departure - timedelta(minutes=15)

            time_remaining = (boarding_close - check_in_completed).total_seconds()

            checkin_waiting_result = self.waiting_simulator.wait(
                passenger=passenger,
                wait_time=queue_wait,
                time_remaining=time_remaining,
                required_time=SECURITY_TO_GATE_BUFFER_SECONDS,
            )

        payload = base_payload()
        payload.update(
            {
                "queue_wait": queue_wait,
                "service_time": checkin_result.service_time,
                "queue_length": checkin_result.queue_length,
                "checkin_occupancy": checkin_result.occupancy,
                "checkin_congested": checkin_result.congested,
                "duration": checkin_result.service_time,
                "stress": passenger.current_stress,
            }
        )

        if checkin_waiting_result is not None:
            payload.update(
                {
                    "time_pressure": checkin_waiting_result.time_pressure,
                    "wait_stress": checkin_waiting_result.final_stress,
                }
            )

        events.append(
            SimulationEvent(
                event_time=check_in_completed,
                event_type=EventType.CHECK_IN_COMPLETED,
                entity=passenger,
                payload=payload,
            )
        )

        # ======================================================
        # CHECK-IN → SECURITY
        # ======================================================

        movement = self.movement.move(
            passenger=passenger,
            origin=context.checkin_location,
            destination=context.security_location,
        )

        security_arrival = check_in_completed + timedelta(
            seconds=movement.walking_time
        )

        payload = base_payload()
        payload.update(
            {
                "distance": movement.distance,
                "walking_speed": movement.walking_speed,
                "walking_time": movement.walking_time,
                "stress": movement.final_stress,
            }
        )

        events.append(
            SimulationEvent(
                event_time=security_arrival,
                event_type=EventType.ARRIVE_SECURITY,
                entity=passenger,
                payload=payload,
            )
        )

        # ======================================================
        # RETURN UPDATED CONTEXT
        # ======================================================

        context.security_arrival = security_arrival
        context.events = events
        return context

    # ==========================================================
    # CONTINUE AFTER SECURITY
    # ==========================================================

    def continue_after_security(
        self,
        context: PassengerJourneyContext,
        security_result,
    ) -> list[SimulationEvent]:
        passenger = context.booking.passenger
        flight = context.booking.flight

        events: list[SimulationEvent] = list(context.events)

        airport_code = flight.origin_airport.iata_code
        flight_number = flight.flight_number

        gate = context.gate_location
        security = context.security_location

        def base_payload() -> dict:
            return {
                "flight": flight,
                "flight_number": flight_number,
                "airport": airport_code,
            }

        # ======================================================
        # SECURITY STARTED
        # ======================================================

        security_started = security_result.service_start

        payload = base_payload()
        payload.update(
            {
                "queue_wait": security_result.waiting_time,
                "service_time": security_result.service_time,
                "queue_length": security_result.queue_length,
                "security_occupancy": security_result.occupancy,
                "security_capacity": getattr(
                    security_result,
                    "capacity",
                    None,
                ),
                "security_congested": security_result.congested,
                "stress": passenger.current_stress,
            }
        )

        events.append(
            SimulationEvent(
                event_time=security_started,
                event_type=EventType.SECURITY_STARTED,
                entity=passenger,
                payload=payload,
            )
        )

        # ======================================================
        # WAIT STRESS
        # ======================================================
        #
        # While waiting in the security queue, stress reacts to
        # how much time the passenger has left until boarding
        # closes. The waiting simulator mutates
        # passenger.current_stress, and SECURITY_COMPLETED below
        # captures the resulting value.

        waiting_result = None

        if security_result.waiting_time > 0:
            boarding_close = flight.scheduled_departure - timedelta(minutes=15)

            time_remaining = (boarding_close - security_started).total_seconds()

            required_time = SECURITY_TO_GATE_BUFFER_SECONDS

            waiting_result = self.waiting_simulator.wait(
                passenger=passenger,
                wait_time=security_result.waiting_time,
                time_remaining=time_remaining,
                required_time=required_time,
            )

        # ======================================================
        # SECURITY COMPLETED
        # ======================================================

        security_completed = security_result.service_end

        payload = base_payload()
        payload.update(
            {
                "queue_wait": security_result.waiting_time,
                "service_time": security_result.service_time,
                "queue_length": security_result.queue_length,
                "security_occupancy": security_result.occupancy,
                "security_capacity": getattr(
                    security_result,
                    "capacity",
                    None,
                ),
                "security_congested": security_result.congested,
                "stress": passenger.current_stress,
            }
        )

        if waiting_result is not None:
            payload.update(
                {
                    "time_pressure": waiting_result.time_pressure,
                    "wait_stress": waiting_result.final_stress,
                }
            )

        events.append(
            SimulationEvent(
                event_time=security_completed,
                event_type=EventType.SECURITY_COMPLETED,
                entity=passenger,
                payload=payload,
            )
        )

        # ======================================================
        # SECURITY → GATE
        # ======================================================

        movement = self.movement.move(
            passenger=passenger,
            origin=security,
            destination=gate,
            stress_event=StressEvent.REACHED_GATE,
        )

        gate_arrival = security_completed + timedelta(seconds=movement.walking_time)

        # ======================================================
        # ARRIVE AT GATE
        # ======================================================

        payload = base_payload()
        payload.update(
            {
                "gate": flight.gate.gate_code,
                "distance": movement.distance,
                "walking_speed": movement.walking_speed,
                "walking_time": movement.walking_time,
                "stress": movement.final_stress,
            }
        )

        events.append(
            SimulationEvent(
                event_time=gate_arrival,
                event_type=EventType.ARRIVE_GATE,
                entity=passenger,
                payload=payload,
            )
        )

        # ======================================================
        # BOARDING RESULT
        # ======================================================

        boarding_close = flight.scheduled_departure - timedelta(minutes=15)

        boarding_group = context.booking.boarding_group

        if boarding_group is not None:
            group_window_start, group_window_end = _boarding_window(
                flight,
                boarding_group,
            )
        else:
            group_window_start = boarding_close
            group_window_end = boarding_close

        if gate_arrival <= boarding_close:
            # El pasajero embarca cuando llega a puerta o, si llegó antes de
            # que llamen a su grupo, cuando se abre la ventana de su grupo.
            # Así la secuencia de embarque respeta la prioridad del grupo.
            boarded_at = max(gate_arrival, group_window_start)

            events.append(
                SimulationEvent(
                    event_time=boarded_at,
                    event_type=EventType.PASSENGER_BOARDED,
                    entity=passenger,
                    payload={
                        **base_payload(),
                        "gate": flight.gate.gate_code,
                        "boarding_group": (
                            boarding_group.value if boarding_group else None
                        ),
                        "group_window_start": group_window_start,
                        "group_window_end": group_window_end,
                        "boarding_deadline": boarding_close,
                        "status": "boarded",
                        "stress": movement.final_stress,
                    },
                )
            )

        else:
            events.append(
                SimulationEvent(
                    event_time=gate_arrival,
                    event_type=EventType.MISSED_FLIGHT,
                    entity=passenger,
                    payload={
                        **base_payload(),
                        "gate": flight.gate.gate_code,
                        "boarding_group": (
                            boarding_group.value if boarding_group else None
                        ),
                        "group_window_start": group_window_start,
                        "group_window_end": group_window_end,
                        "boarding_deadline": boarding_close,
                        "status": "missed_flight",
                        "reason": "arrived_after_boarding_close",
                        "stress": movement.final_stress,
                    },
                )
            )

        # ======================================================
        # SORT EVENTS
        # ======================================================

        events.sort(key=lambda event: event.event_time)

        return events

    # ==========================================================
    # COMPLETE JOURNEY
    # ==========================================================

    def after_boarding(
        self,
        booking: Booking,
        airport_layout: AirportLayout,
        landed_time: datetime,
        stress_event: StressEvent | None = None,
    ) -> list[SimulationEvent]:
        """
        Genera la fase de llegada de un pasajero que ya embarcó.

        La simulación de salida termina en PASSENGER_BOARDED; esta fase
        completa el ciclo hasta que el pasajero sale a la calle en el
        aeropuerto de destino:

            AIRCRAFT_LANDED  →  EXIT_AIRCRAFT  →  EXIT_AIRPORT

        - El desembarque ocurre `landed_time` más un delta proporcional a
          la fila del asiento (los de adelante salen antes).
        - Tras desembarcar, el pasajero camina desde la recogida de
          equipaje hacia la salida, según su velocidad de marcha.

        Los pasajeros que NO embarcaron (MISSED_FLIGHT) no pasan por aquí.
        """

        passenger = booking.passenger
        flight = booking.flight

        events: list[SimulationEvent] = []

        def base_payload() -> dict:
            return {
                "flight": flight,
                "flight_number": flight.flight_number,
                "airport": airport_layout.airport_code,
            }

        # ------------------------------------------------------
        # DESEMBARQUE
        # ------------------------------------------------------

        # La fila del asiento (ej. "12F" -> 12) ordena la salida del avión.
        row = 30
        if booking.seat is not None:
            row_digits = "".join(
                ch for ch in booking.seat.seat_number if ch.isdigit()
            )
            if row_digits:
                row = int(row_digits)

        deboarding_seconds = 15.0 + row * 3.0
        exit_aircraft_time = landed_time + timedelta(seconds=deboarding_seconds)

        payload = base_payload()
        payload.update(
            {
                "destination_airport": flight.destination_airport.iata_code,
                "deboarding_seconds": deboarding_seconds,
            }
        )

        events.append(
            SimulationEvent(
                event_time=exit_aircraft_time,
                event_type=EventType.EXIT_AIRCRAFT,
                entity=passenger,
                payload=payload,
            )
        )

        # ------------------------------------------------------
        # CAMINATA HASTA LA SALIDA
        # ------------------------------------------------------

        baggage_claim = airport_layout.get_location("baggage_claim")
        exit_location = airport_layout.get_location("exit")

        movement = self.movement.move(
            passenger=passenger,
            origin=baggage_claim,
            destination=exit_location,
            stress_event=stress_event,
        )

        exit_airport_time = exit_aircraft_time + timedelta(
            seconds=movement.walking_time
        )

        payload = base_payload()
        payload.update(
            {
                "destination_airport": flight.destination_airport.iata_code,
                "distance": movement.distance,
                "walking_speed": movement.walking_speed,
                "walking_time": movement.walking_time,
                "stress": movement.final_stress,
                "checked_baggage": booking.checked_baggage,
            }
        )

        events.append(
            SimulationEvent(
                event_time=exit_airport_time,
                event_type=EventType.EXIT_AIRPORT,
                entity=passenger,
                payload=payload,
            )
        )

        return events

    # ==========================================================
    # COMPLETE JOURNEY
    # ==========================================================

    def run(
        self,
        booking: Booking,
        airport_layout: AirportLayout,
        security_queue: SecurityQueue | None = None,
        checkin_queue: CheckInQueue | None = None,
    ) -> list[SimulationEvent]:
        """
        Convenience method that executes the complete passenger
        journey.

        If a SecurityQueue / CheckInQueue is supplied, it is used.

        If no queue is supplied, defaults are created. This is
        useful for tests involving a single passenger.

        The global SimulationRunner should NOT rely on this
        method when multiple passengers share airport resources.
        It should use prepare(), continue_after_checkin() and
        continue_after_security() instead.
        """

        context = self.prepare(
            booking=booking,
            airport_layout=airport_layout,
        )

        # ------------------------------------------------------
        # DEFAULT CHECK-IN QUEUE
        # ------------------------------------------------------

        if checkin_queue is None:
            checkin_queue = CheckInQueue(
                queue_service_model=self.queue_service_model,
            )

        checkin_result = checkin_queue.process(
            passenger=booking.passenger,
            arrival_time=context.check_in_arrival,
        )

        context = self.continue_after_checkin(
            context=context,
            checkin_result=checkin_result,
        )

        # ------------------------------------------------------
        # DEFAULT SECURITY QUEUE
        # ------------------------------------------------------

        if security_queue is None:
            security_queue = SecurityQueue(
                queue_service_model=self.queue_service_model,
            )

        # ------------------------------------------------------
        # SECURITY
        # ------------------------------------------------------

        security_result = security_queue.process(
            passenger=booking.passenger,
            arrival_time=context.security_arrival,
        )

        # ------------------------------------------------------
        # CONTINUE JOURNEY
        # ------------------------------------------------------

        return self.continue_after_security(
            context=context,
            security_result=security_result,
        )
