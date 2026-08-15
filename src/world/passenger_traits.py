from dataclasses import dataclass


@dataclass(slots=True)
class PassengerTraits:
    """
    Stable behavioral traits of a passenger.

    These traits are relatively stable throughout the simulation.
    They influence, but do not directly determine, passenger behavior.
    """

    fitness: float
    stress_resilience: float
    distraction_proneness: float
    travel_experience: int
