import random
from dataclasses import dataclass

from ...enums.world_enums import StressEvent


@dataclass(slots=True)
class StressModel:
    stress_impacts: dict[StressEvent, float] = None

    def __post_init__(self):
        if self.stress_impacts is None:
            self.stress_impacts = {
                StressEvent.WAITING: 0.02,
                StressEvent.TIME_PRESSURE: 0.08,
                StressEvent.RUNNING_LATE: 0.15,
                StressEvent.REACHED_GATE: -0.10,
            }

    def _clamp(
        self,
        value: float,
        minimum: float = 0.0,
        maximum: float = 1.0,
    ) -> float:
        return max(minimum, min(value, maximum))

    def calculate_initial_stress(
        self,
        stress_resilience: float,
    ) -> float:
        base_stress = random.uniform(0.20, 0.35)

        resilience_effect = stress_resilience * 0.10

        return self._clamp(base_stress - resilience_effect)

    def apply_event(
        self,
        current_stress: float,
        event: StressEvent,
        stress_resilience: float,
    ) -> float:
        impact = self.stress_impacts.get(event, 0.0)

        effective_impact = impact * (1.0 - stress_resilience)

        return self._clamp(current_stress + effective_impact)

    def calculate_time_pressure(
        self,
        time_remaining: float,
        required_time: float,
    ) -> float:
        if required_time <= 0:
            raise ValueError("Required time must be greater than zero.")

        if time_remaining <= 0:
            return 1.0

        margin = time_remaining / required_time

        if margin >= 2.0:
            return 0.0

        if margin <= 1.0:
            return 1.0

        return 2.0 - margin

    def recover(
        self,
        current_stress: float,
        duration_minutes: float,
        stress_resilience: float,
        time_pressure: float,
    ) -> float:
        """
        Update stress during a waiting period.

        Low time pressure allows the passenger to recover.
        Moderate pressure stops recovery and may increase stress.
        High pressure increases stress faster.
        """

        if duration_minutes <= 0:
            return current_stress

        time_pressure = self._clamp(time_pressure)

        # Comfortable waiting allows stress recovery (capped at moderate
        # pressure — once the passenger feels pressed, recovery stops).
        recovery = 0.0
        if time_pressure <= 0.5:
            recovery_rate = 0.01 * duration_minutes * (0.5 + stress_resilience)
            recovery_modifier = 1.0 - time_pressure * 2.0
            recovery = recovery_rate * max(recovery_modifier, 0.0)

        # Time pressure increases stress proportionally to wait duration.
        stress_increase = 0.0
        if time_pressure > 0.1:
            stress_increase += 0.02 * duration_minutes * time_pressure

        # Under extreme pressure, stress rises faster.
        if time_pressure > 0.8:
            stress_increase += 0.03 * duration_minutes * (time_pressure - 0.8) * 5.0

        # Queue friction: standing in line is mildly draining even when the
        # wait is comfortable (far below recovery, so calm waits still relax).
        queue_friction = 0.004 * duration_minutes

        return self._clamp(current_stress - recovery + stress_increase + queue_friction)
