import random
from ....enums.world_enums import TravelPurpose


def generate_distraction(
    travel_purpose: TravelPurpose,
    travel_experience: int,
) -> float:
    base = random.betavariate(2.2, 3.0)

    purpose_modifier = {
        TravelPurpose.BUSINESS: -0.10,
        TravelPurpose.LEISURE: 0.05,
        TravelPurpose.FAMILY: 0.05,
        TravelPurpose.VISITING: 0.00,
    }

    experience_modifier = (5 - travel_experience) * 0.015

    distraction = base + purpose_modifier[travel_purpose] + experience_modifier

    return max(0.0, min(1.0, distraction))
