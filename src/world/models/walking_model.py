from dataclasses import dataclass


@dataclass(slots=True)
class WalkingModel:
    """
    A dataclass representing a walking model.

    Attributes:
        speed (float): The speed of walking in meters per second.
        step_length (float): The length of each step in meters.
        cadence (float): The number of steps taken per minute.
    """

    speed: float
    step_length: float
    cadence: float

    def calculate_speed(self) -> float:
        """
        Calculate the speed of walking based on step length and cadence.

        Returns:
            float: The calculated speed in meters per second.
        """
        return (self.step_length * self.cadence) / 60.0
