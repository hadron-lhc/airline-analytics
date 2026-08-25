from datetime import timedelta

from ...enums.simulation_enums import EventType
from ...world.booking import Booking
from ...world.models.stress_model import StressModel
from ...world.models.walking_model import WalkingModel
from ...world.airport_layout import AirportLayout
from ..event import SimulationEvent
from ..passenger_movement import PassengerMovement


class PassengerJourney:
    def __init__(
        self,
        walking_model: WalkingModel | None = None,
        stress_model: StressModel | None = None,
    ):
        self.movement = PassengerMovement(
            walking_model=walking_model,
            stress_model=stress_model,
        )

    def run(
        self,
        booking: Booking,
        airport_layout: AirportLayout,
    ) -> list[SimulationEvent]:
        passenger = booking.passenger
        flight = booking.flight

        events: list[SimulationEvent] = []

        airport_code = flight.origin_airport.iata_code
        flight_number = flight.flight_number

        entrance = airport_layout.get_location("entrance")
        check_in = airport_layout.get_location("check_in")
        security = airport_layout.get_location("security")
        gate = airport_layout.get_gate_location(flight.gate.gate_code)

        # --------------------------------------------------
        # COMMON EVENT CONTEXT
        # --------------------------------------------------

        def base_payload() -> dict:
            return {
                "flight": flight_number,
                "airport": airport_code,
            }

        # --------------------------------------------------
        # ARRIVAL AT AIRPORT
        # --------------------------------------------------

        arrival_time = flight.scheduled_departure - timedelta(minutes=120)

        passenger.current_stress = self.movement.stress_model.calculate_initial_stress(
            passenger.traits.stress_resilience
        )

        payload = base_payload()
        payload.update(
            {
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

        # --------------------------------------------------
        # ENTRANCE → CHECK-IN
        # --------------------------------------------------

        movement = self.movement.move(
            passenger,
            entrance,
            check_in,
        )

        check_in_arrival = arrival_time + timedelta(seconds=movement.walking_time)

        payload = base_payload()
        payload.update(
            {
                "distance": movement.distance,
                "walking_speed": movement.walking_speed,
                "walking_time": movement.walking_time,
                "stress": passenger.current_stress,
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

        # --------------------------------------------------
        # CHECK-IN
        # --------------------------------------------------

        check_in_duration = timedelta(minutes=4)

        check_in_completed = check_in_arrival + check_in_duration

        payload = base_payload()
        payload.update(
            {
                "duration": check_in_duration.total_seconds(),
                "stress": passenger.current_stress,
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

        # --------------------------------------------------
        # CHECK-IN → SECURITY
        # --------------------------------------------------

        movement = self.movement.move(
            passenger,
            check_in,
            security,
        )

        security_arrival = check_in_completed + timedelta(seconds=movement.walking_time)

        payload = base_payload()
        payload.update(
            {
                "distance": movement.distance,
                "walking_speed": movement.walking_speed,
                "walking_time": movement.walking_time,
                "stress": passenger.current_stress,
            }
        )

        events.append(
            SimulationEvent(
                event_time=security_arrival,
                event_type=EventType.SECURITY_STARTED,
                entity=passenger,
                payload=payload,
            )
        )

        # --------------------------------------------------
        # SECURITY
        # --------------------------------------------------

        security_duration = timedelta(seconds=45)

        security_completed = security_arrival + security_duration

        payload = base_payload()
        payload.update(
            {
                "duration": security_duration.total_seconds(),
                "stress": passenger.current_stress,
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

        # --------------------------------------------------
        # SECURITY → GATE
        # --------------------------------------------------

        movement = self.movement.move(
            passenger,
            security,
            gate,
        )

        gate_arrival = security_completed + timedelta(seconds=movement.walking_time)

        payload = base_payload()
        payload.update(
            {
                "gate": flight.gate.gate_code,
                "distance": movement.distance,
                "walking_speed": movement.walking_speed,
                "walking_time": movement.walking_time,
                "stress": passenger.current_stress,
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

        return events
