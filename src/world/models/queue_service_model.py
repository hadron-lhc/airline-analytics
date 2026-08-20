import random

from dataclasses import dataclass

from ..passenger import Passenger


@dataclass(slots=True)
class QueueServiceModel:
    """
    Model the amount of time a passenger occupies a service point.
    """

    base_service_time: float = 45.0
    random_variation: float = 0.15

    def calculate_security_time(
        self,
        passenger: Passenger,
    ) -> float:
        """
        Calculate the security processing time for a passenger.

        Returns:
            Processing time in seconds.
        """

        variation = random.uniform(
            1.0 - self.random_variation,
            1.0 + self.random_variation,
        )

        # More distracted passengers may take slightly longer.
        distraction_factor = 1.0 + passenger.traits.distraction_proneness * 0.10

        # Experienced travelers tend to move through security
        # slightly more efficiently.
        experience_factor = 1.0 - passenger.traits.travel_experience * 0.015

        service_time = (
            self.base_service_time * variation * distraction_factor * experience_factor
        )

        return max(service_time, 15.0)
