from dataclasses import dataclass


@dataclass(slots=True)
class PassengerTraits:
    fitness: float
    stress_resilience: float
    distraction_proneness: float
    travel_experience: int
