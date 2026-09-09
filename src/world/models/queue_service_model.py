import random

from dataclasses import dataclass

from ..passenger import Passenger


@dataclass(slots=True)
class QueueServiceModel:
    """
    Model the amount of time a passenger occupies a service point.
    """

    base_service_time: float = 130.0
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

    def calculate_checkin_time(
        self,
        passenger: Passenger,
        online: bool = False,
    ) -> float:
        """
        Calculate the check-in service time for a passenger.

        Online check-in (bag-drop kiosk) is much faster than a
        full check-in at the counter. Service time also grows if
        the passenger is checking bags.
        """
        variation = random.uniform(
            1.0 - self.random_variation,
            1.0 + self.random_variation,
        )

        baggage_factor = 1.0 + (passenger.baggage_probability * 0.25)

        if online:
            base = 55.0
        else:
            base = 180.0

        service_time = base * variation * baggage_factor

        return max(service_time, 20.0)
