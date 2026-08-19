import random
from dataclasses import dataclass

from ..passenger import Passenger
from ..airport_location import AirportLocation


@dataclass(slots=True)
class WalkingModel:
    random_variation: float = 0.02

    def _fitness_variation_factor(self, fitness: float) -> float:
        """
        Fitness modifies the passenger's natural walking speed.

        fitness = 0.0 -> 0.95
        fitness = 0.5 -> 1.00
        fitness = 1.0 -> 1.05
        """
        return 0.95 + fitness * 0.10

    def _distraction_variation_factor(
        self,
        distraction_proneness: float,
    ) -> float:
        """
        Highly distracted passengers tend to walk slightly slower.

        distraction = 0.0 -> 1.00
        distraction = 0.5 -> 0.97
        distraction = 1.0 -> 0.94
        """
        return 1.0 - 0.06 * distraction_proneness

    def _stress_variation_factor(
        self,
        stress_level: float,
        stress_resilience: float,
    ) -> float:
        """
        Stress can reduce walking efficiency.

        The effect is stronger when the passenger has low
        stress resilience.
        """
        stress_effect = stress_level * (1.0 - stress_resilience)

        return 1.0 - 0.05 * stress_effect

    def calculate_effective_speed(
        self,
        passenger: Passenger,
    ) -> float:
        """
        Calculate the passenger's current walking speed.

        The speed is based on:
        - base walking speed
        - fitness
        - distraction proneness
        - current stress
        - stress resilience
        - small random variation
        """

        base_speed = passenger.walking_speed

        if base_speed <= 0:
            raise ValueError("Base walking speed must be greater than zero.")

        random_factor = random.uniform(
            1.0 - self.random_variation,
            1.0 + self.random_variation,
        )

        fitness_factor = self._fitness_variation_factor(passenger.traits.fitness)

        distraction_factor = self._distraction_variation_factor(
            passenger.traits.distraction_proneness
        )

        stress_factor = self._stress_variation_factor(
            passenger.current_stress,
            passenger.traits.stress_resilience,
        )

        total_factor = (
            random_factor * fitness_factor * distraction_factor * stress_factor
        )

        effective_speed = base_speed * total_factor

        return effective_speed

    def calculate_time(
        self,
        distance: float,
        walking_speed: float,
    ) -> float:
        """Calculate walking time in seconds."""

        if distance < 0:
            raise ValueError("Distance cannot be negative.")

        if walking_speed <= 0:
            raise ValueError("Walking speed must be greater than zero.")

        return distance / walking_speed

    def calculate_walking_time(
        self,
        passenger: Passenger,
        origin: AirportLocation,
        destination: AirportLocation,
    ) -> float:
        """
        Calculate walking time between two airport locations.

        The passenger's current state determines the effective
        walking speed.
        """

        distance = origin.position.distance_to(destination.position)

        effective_speed = self.calculate_effective_speed(passenger)

        passenger.current_speed = effective_speed

        return self.calculate_time(
            distance,
            effective_speed,
        )
