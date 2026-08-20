from datetime import datetime, timedelta

from ..enums.simulation_enums import EventType
from ..enums.world_enums import StressEvent
from ..world.airport_layout import AirportLayout
from ..world.passenger import Passenger
from ..world.models.stress_model import StressModel
from ..world.models.walking_model import WalkingModel
from .event import SimulationEvent
from .passenger_movement import PassengerMovement


class PassengerJourney:
    def __init__(
        self,
        walking_model: WalkingModel | None = None,
        stress_model: StressModel | None = None,
    ):
        self.walking_model = walking_model or WalkingModel()
        self.stress_model = stress_model or StressModel()

        self.movement = PassengerMovement(
            walking_model=self.walking_model,
            stress_model=self.stress_model,
        )

    def run(
        self,
        passenger: Passenger,
        airport_layout: AirportLayout,
        start_time: datetime,
        gate_code: str = "gate_C1",
    ) -> list[SimulationEvent]:
        events: list[SimulationEvent] = []

        current_time = start_time

        entrance = airport_layout.get_location("entrance")
        checkin = airport_layout.get_location("check_in")
        security = airport_layout.get_location("security")
        gate = airport_layout.get_location(gate_code)

        # ---------------------------------------------------------
        # 1. ARRIVE AT AIRPORT
        # ---------------------------------------------------------

        events.append(
            SimulationEvent(
                event_time=current_time,
                event_type=EventType.ARRIVE_AIRPORT,
                entity=passenger,
                payload={
                    "airport": airport_layout.airport_code,
                    "stress": passenger.current_stress,
                },
            )
        )

        # ---------------------------------------------------------
        # 2. ENTRANCE → CHECK-IN
        # ---------------------------------------------------------

        movement = self.movement.move(
            passenger,
            entrance,
            checkin,
        )

        current_time += timedelta(seconds=movement.walking_time)

        events.append(
            SimulationEvent(
                event_time=current_time,
                event_type=EventType.ARRIVE_CHECK_IN,
                entity=passenger,
                payload={
                    "origin": movement.origin,
                    "destination": movement.destination,
                    "distance": movement.distance,
                    "walking_speed": movement.walking_speed,
                    "walking_time": movement.walking_time,
                    "stress_before": movement.initial_stress,
                    "stress_after": movement.final_stress,
                },
            )
        )

        # ---------------------------------------------------------
        # 3. CHECK-IN
        # ---------------------------------------------------------

        checkin_duration = 4.0 * 60.0

        checkin_start = current_time

        passenger.current_stress = self.stress_model.apply_event(
            passenger.current_stress,
            StressEvent.WAITING,
            passenger.traits.stress_resilience,
        )

        current_time += timedelta(seconds=checkin_duration)

        events.append(
            SimulationEvent(
                event_time=current_time,
                event_type=EventType.CHECK_IN_COMPLETED,
                entity=passenger,
                payload={
                    "start_time": checkin_start,
                    "duration": checkin_duration,
                    "stress": passenger.current_stress,
                },
            )
        )

        # ---------------------------------------------------------
        # 4. SECURITY QUEUE
        # ---------------------------------------------------------

        # Temporary queue simulation.
        # For the first timeline we use a fixed wait time.
        wait_time = 5.0 * 60.0

        stress_before = passenger.current_stress

        time_pressure = self.stress_model.calculate_time_pressure(
            time_remaining=25.0 * 60.0,
            required_time=15.0 * 60.0,
        )

        passenger.current_stress = self.stress_model.recover(
            current_stress=passenger.current_stress,
            duration_minutes=wait_time / 60.0,
            stress_resilience=passenger.traits.stress_resilience,
            time_pressure=time_pressure,
        )

        current_time += timedelta(seconds=wait_time)

        events.append(
            SimulationEvent(
                event_time=current_time,
                event_type=EventType.SECURITY_STARTED,
                entity=passenger,
                payload={
                    "wait_time": wait_time,
                    "time_pressure": time_pressure,
                    "stress_before": stress_before,
                    "stress_after": passenger.current_stress,
                },
            )
        )

        # ---------------------------------------------------------
        # 5. SECURITY
        # ---------------------------------------------------------

        security_duration = 50.0

        current_time += timedelta(seconds=security_duration)

        events.append(
            SimulationEvent(
                event_time=current_time,
                event_type=EventType.SECURITY_COMPLETED,
                entity=passenger,
                payload={
                    "duration": security_duration,
                    "stress": passenger.current_stress,
                },
            )
        )

        # ---------------------------------------------------------
        # 6. SECURITY → GATE
        # ---------------------------------------------------------

        movement = self.movement.move(
            passenger,
            security,
            gate,
        )

        current_time += timedelta(seconds=movement.walking_time)

        events.append(
            SimulationEvent(
                event_time=current_time,
                event_type=EventType.ARRIVE_GATE,
                entity=passenger,
                payload={
                    "origin": movement.origin,
                    "destination": movement.destination,
                    "distance": movement.distance,
                    "walking_speed": movement.walking_speed,
                    "walking_time": movement.walking_time,
                    "stress_before": movement.initial_stress,
                    "stress_after": movement.final_stress,
                },
            )
        )

        return events
