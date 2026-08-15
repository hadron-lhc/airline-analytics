from ....enums.world_enums import TravelPurpose, LoyaltyLevel
import random


def generate_arrival_margin(
    travel_purpose: TravelPurpose,
    travel_experience: int,
    distraction_proneness: float,
    stress_resilience: float,
) -> int:
    base_margin = {
        TravelPurpose.BUSINESS: 75,
        TravelPurpose.LEISURE: 180,
        TravelPurpose.FAMILY: 210,
        TravelPurpose.VISITING: 125,
    }[travel_purpose]

    experience_effect = (5 - travel_experience) * 5

    distraction_effect = (distraction_proneness - 0.5) * 30

    stress_effect = (0.5 - stress_resilience) * 20

    noise = random.gauss(0, 12)

    margin = (
        base_margin + experience_effect + distraction_effect + stress_effect + noise
    )

    return max(45, round(margin))


def generate_walking_speed(
    age: int,
    fitness: float,
    travel_experience: int,
    distraction_proneness: float,
) -> float:
    age_penalty = max(0, age - 30) * 0.004

    fitness_effect = (fitness - 0.5) * 0.45

    experience_effect = (travel_experience - 5) * 0.015

    distraction_effect = (distraction_proneness - 0.5) * 0.15

    speed = (
        1.20
        + fitness_effect
        + experience_effect
        - age_penalty
        - distraction_effect
        + random.gauss(0, 0.08)
    )

    return round(
        max(0.65, min(1.70, speed)),
        2,
    )


def generate_online_checkin_probability(
    travel_purpose: TravelPurpose,
    travel_experience: int,
    distraction_proneness: float,
) -> float:
    base = {
        TravelPurpose.BUSINESS: 0.90,
        TravelPurpose.LEISURE: 0.55,
        TravelPurpose.FAMILY: 0.50,
        TravelPurpose.VISITING: 0.80,
    }[travel_purpose]

    experience_effect = (travel_experience - 5) * 0.035

    distraction_effect = (distraction_proneness - 0.5) * 0.20

    probability = base + experience_effect - distraction_effect + random.gauss(0, 0.04)

    return max(0.05, min(0.99, probability))


def generate_baggage_probability(
    travel_purpose: TravelPurpose,
    distraction_proneness: float,
) -> float:
    base = {
        TravelPurpose.BUSINESS: 0.20,
        TravelPurpose.LEISURE: 0.75,
        TravelPurpose.FAMILY: 0.90,
        TravelPurpose.VISITING: 0.70,
    }[travel_purpose]

    distraction_effect = (distraction_proneness - 0.5) * 0.08

    probability = base + distraction_effect + random.gauss(0, 0.04)

    return max(0.05, min(0.99, probability))


def generate_loyalty_level(
    travel_experience: int,
    travel_purpose: TravelPurpose,
) -> LoyaltyLevel:
    if travel_experience <= 2:
        probabilities = {
            LoyaltyLevel.NONE: 0.95,
            LoyaltyLevel.SILVER: 0.05,
            LoyaltyLevel.GOLD: 0.0,
            LoyaltyLevel.PLATINUM: 0.0,
        }

    elif travel_experience <= 5:
        probabilities = {
            LoyaltyLevel.NONE: 0.75,
            LoyaltyLevel.SILVER: 0.22,
            LoyaltyLevel.GOLD: 0.03,
            LoyaltyLevel.PLATINUM: 0.0,
        }

    elif travel_experience <= 7:
        probabilities = {
            LoyaltyLevel.NONE: 0.50,
            LoyaltyLevel.SILVER: 0.35,
            LoyaltyLevel.GOLD: 0.13,
            LoyaltyLevel.PLATINUM: 0.02,
        }

    else:
        probabilities = {
            LoyaltyLevel.NONE: 0.30,
            LoyaltyLevel.SILVER: 0.35,
            LoyaltyLevel.GOLD: 0.25,
            LoyaltyLevel.PLATINUM: 0.10,
        }

    # Business travelers have a higher tendency to participate
    # in airline loyalty programs.
    if travel_purpose == TravelPurpose.BUSINESS:
        probabilities[LoyaltyLevel.NONE] *= 0.75

    levels = list(probabilities.keys())
    weights = list(probabilities.values())

    total = sum(weights)
    weights = [weight / total for weight in weights]

    return random.choices(
        population=levels,
        weights=weights,
        k=1,
    )[0]
