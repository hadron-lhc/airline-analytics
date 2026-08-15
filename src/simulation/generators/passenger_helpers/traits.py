import random

from ....enums.world_enums import TravelPurpose


def generate_fitness(age: int) -> float:
    """
    Generates fitness as a value between 0 and 1.

    Age influences the distribution, but does not determine fitness.
    """

    if age < 30:
        mean = 0.68
        std = 0.16

    elif age < 50:
        mean = 0.62
        std = 0.18

    elif age < 65:
        mean = 0.54
        std = 0.18

    else:
        mean = 0.45
        std = 0.17

    fitness = random.gauss(mean, std)

    return max(0.0, min(1.0, fitness))


def generate_stress_resilience(
    age: int,
    fitness: float,
    travel_experience: int,
) -> float:
    age_factor = min(age / 70, 1.0)
    experience_factor = travel_experience / 10

    value = (
        0.25
        + 0.20 * age_factor
        + 0.30 * experience_factor
        + 0.15 * fitness
        + random.gauss(0, 0.10)
    )

    return max(0.0, min(1.0, value))


def generate_travel_experience(
    age: int,
    travel_purpose: TravelPurpose,
) -> int:
    """
    Genera un índice de experiencia viajando de 0 a 10.

    La experiencia depende principalmente de la edad,
    con una pequeña influencia del propósito del viaje.
    """

    # Experiencia base según edad.
    if age <= 25:
        base = random.gauss(2.5, 1.5)

    elif age <= 40:
        base = random.gauss(4.5, 1.7)

    elif age <= 60:
        base = random.gauss(6.0, 1.7)

    else:
        base = random.gauss(6.0, 2.0)

    # El propósito aporta una pequeña influencia.
    purpose_modifier = {
        TravelPurpose.BUSINESS: 1.2,
        TravelPurpose.VISITING: 0.6,
        TravelPurpose.LEISURE: 0.0,
        TravelPurpose.FAMILY: 0.2,
    }

    experience = base + purpose_modifier[travel_purpose]

    # Limitar al rango válido.
    experience = max(0.0, min(10.0, experience))

    return round(experience)
