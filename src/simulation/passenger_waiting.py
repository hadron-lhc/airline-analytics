from dataclasses import dataclass

from ..world.passenger import Passenger
from ..world.models.stress_model import StressModel


@dataclass(slots=True)
class WaitingResult:
    wait_time: float
    time_pressure: float
    initial_stress: float
    final_stress: float


class PassengerWaitingSimulator:
    def __init__(
        self,
        stress_model: StressModel | None = None,
    ):
        self.stress_model = stress_model or StressModel()

    def wait(
        self,
        passenger: Passenger,
        wait_time: float,
        time_remaining: float,
        required_time: float,
    ) -> WaitingResult:
        """
        Simulate a passenger waiting in a queue.

        Stress is updated according to the time pressure
        experienced during the waiting period.
        """

        if wait_time < 0:
            raise ValueError("Wait time cannot be negative.")

        initial_stress = passenger.current_stress

        time_pressure = self.stress_model.calculate_time_pressure(
            time_remaining=time_remaining,
            required_time=required_time,
        )

        final_stress = self.stress_model.recover(
            current_stress=passenger.current_stress,
            duration_minutes=wait_time / 60.0,
            stress_resilience=passenger.traits.stress_resilience,
            time_pressure=time_pressure,
        )

        passenger.current_stress = final_stress

        return WaitingResult(
            wait_time=wait_time,
            time_pressure=time_pressure,
            initial_stress=initial_stress,
            final_stress=final_stress,
        )
