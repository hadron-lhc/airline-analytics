from src.simulation.generators.passenger_factory import (
    create_random_passenger,
    generate_passengers,
)
from src.simulation.generators.passenger_helpers.derived_behavior import (
    generate_arrival_margin,
    generate_walking_speed,
)
from src.enums.world_enums import TravelPurpose, LoyaltyLevel


def test_every_passenger_has_non_default_traits():
    passenger = create_random_passenger()

    assert passenger.traits is not None
    assert 0.0 <= passenger.traits.fitness <= 1.0
    assert 0.0 <= passenger.traits.stress_resilience <= 1.0
    assert 0.0 <= passenger.traits.distraction_proneness <= 1.0
    assert 0 <= passenger.traits.travel_experience <= 10


def test_derived_behavior_uses_traits():
    passenger = create_random_passenger()

    # Walking speed derives from traits and stays within the allowed range.
    assert 0.65 <= passenger.walking_speed <= 1.70

    # Arrival margin is always at least 45 minutes.
    assert passenger.arrival_margin >= 45

    # Initial stress is a normalized value.
    assert 0.0 <= passenger.current_stress <= 1.0


def test_walking_speed_increases_with_fitness():
    # Fitness only changes; all other inputs stay constant.
    low = generate_walking_speed(
        age=40,
        fitness=0.0,
        travel_experience=5,
        distraction_proneness=0.5,
    )
    high = generate_walking_speed(
        age=40,
        fitness=1.0,
        travel_experience=5,
        distraction_proneness=0.5,
    )

    assert high >= low


def test_business_passengers_arrive_earlier_than_leisure():
    # Controlling the shared inputs, only the purpose varies.
    business = generate_arrival_margin(
        travel_purpose=TravelPurpose.BUSINESS,
        travel_experience=5,
        distraction_proneness=0.5,
        stress_resilience=0.5,
    )
    leisure = generate_arrival_margin(
        travel_purpose=TravelPurpose.LEISURE,
        travel_experience=5,
        distraction_proneness=0.5,
        stress_resilience=0.5,
    )

    assert business <= leisure


def test_population_has_trait_variation():
    passengers = generate_passengers(50)

    speeds = {passenger.walking_speed for passenger in passengers}
    margins = {passenger.arrival_margin for passenger in passengers}

    assert len(speeds) > 1
    assert len(margins) > 1


def test_population_has_loyalty_distribution():
    passengers = generate_passengers(50)

    levels = {passenger.loyalty_level for passenger in passengers}

    for level in levels:
        assert isinstance(level, LoyaltyLevel)

    assert LoyaltyLevel.NONE in levels
