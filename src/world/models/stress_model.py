from dataclasses import dataclass

from ...enums.world_enums import StressEvent
from ..passenger import Passenger


@dataclass(slots=True)
class StressModel:
    recovery_rate: float = 0.02
    accumulation_rate: float = 0.08

    STRESS_IMPACTS = {
        StressEvent.TIME_PRESSURE: 0.08,
        StressEvent.WAITING: 0.05,
        StressEvent.SECURITY: 0.04,
        StressEvent.RUNNING_LATE: 0.15,
        StressEvent.REACHED_GATE: -0.08,
    }

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))

    def apply_event(
        self,
        passenger: Passenger,
        event: StressEvent,
    ) -> float:
        impact = self.STRESS_IMPACTS[event]

        resilience = passenger.traits.stress_resilience

        effective_impact = impact * (1 - resilience * 0.5)

        passenger.current_stress = self._clamp(
            passenger.current_stress + effective_impact
        )

        return passenger.current_stress

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))

    def calculate_initial_stress(
        self,
        stress_resilience: float,
    ) -> float:
        """
        Calculate the passenger's initial stress level.
        """

        base_stress = 0.30

        resilience_effect = (0.5 - stress_resilience) * 0.20

        return self._clamp(base_stress + resilience_effect)

    def apply_stress(
        self,
        passenger: Passenger,
        amount: float,
    ) -> float:
        """
        Increase the passenger's current stress.

        Stress resilience reduces the impact of stressful events.
        """

        resilience = passenger.traits.stress_resilience

        effective_amount = amount * (1.0 - resilience * 0.5)

        passenger.current_stress = self._clamp(
            passenger.current_stress + effective_amount
        )

        return passenger.current_stress

    def recover(
        self,
        passenger: Passenger,
        elapsed_minutes: float,
    ) -> float:
        """
        Reduce stress over time.
        """

        if elapsed_minutes < 0:
            raise ValueError("Elapsed minutes cannot be negative.")

        resilience = passenger.traits.stress_resilience

        recovery = self.recovery_rate * elapsed_minutes * (0.5 + resilience)

        passenger.current_stress = self._clamp(passenger.current_stress - recovery)

        return passenger.current_stress
