from dataclasses import dataclass

from ..world.airport_location import AirportLocation
from ..world.passenger import Passenger
from ..world.models.stress_model import StressModel
from ..world.models.walking_model import WalkingModel
from ..enums.world_enums import StressEvent


@dataclass(slots=True)
class MovementResult:
    origin: str
    destination: str
    distance: float
    initial_stress: float
    final_stress: float
    walking_speed: float
    walking_time: float


class PassengerMovement:
    def __init__(
        self,
        walking_model: WalkingModel | None = None,
        stress_model: StressModel | None = None,
    ):
        self.walking_model = walking_model or WalkingModel()
        self.stress_model = stress_model or StressModel()

    def move(
        self,
        passenger: Passenger,
        origin: AirportLocation,
        destination: AirportLocation,
        stress_event: StressEvent | None = None,
    ) -> MovementResult:
        distance = origin.position.distance_to(destination.position)

        initial_stress = passenger.current_stress

        if stress_event is not None:
            passenger.current_stress = self.stress_model.apply_event(
                current_stress=passenger.current_stress,
                event=stress_event,
                stress_resilience=passenger.traits.stress_resilience,
            )

        current_speed = self.walking_model.calculate_effective_speed(passenger)

        walking_time = self.walking_model.calculate_time(
            distance,
            current_speed,
        )

        passenger.current_speed = current_speed

        return MovementResult(
            origin=origin.code,
            destination=destination.code,
            distance=distance,
            initial_stress=initial_stress,
            final_stress=passenger.current_stress,
            walking_speed=current_speed,
            walking_time=walking_time,
        )
