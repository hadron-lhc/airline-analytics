from src.world.models.walking_model import WalkingModel
from src.world.models.stress_model import StressModel
from src.world.passenger import Passenger
from src.world.passenger_traits import PassengerTraits
from src.enums.world_enums import DocumentType, Gender, TravelPurpose


def create_passenger(
    stress_resilience=0.5,
    current_stress=0.2,
) -> Passenger:
    return Passenger(
        first_name="Test",
        last_name="Passenger",
        birth_date=__import__("datetime").date(1995, 1, 1),
        gender=Gender.MALE,
        nationality="AR",
        document_type=DocumentType.DNI,
        document_number="12345678",
        email="test@test.com",
        phone="123456789",
        travel_purpose=TravelPurpose.LEISURE,
        traits=PassengerTraits(
            fitness=0.5,
            stress_resilience=stress_resilience,
            distraction_proneness=0.5,
            travel_experience=5,
        ),
        walking_speed=1.2,
        current_stress=current_stress,
    )


def build_walking_model():
    return WalkingModel(random_variation=0.0)


def test_higher_stress_reduces_walking_speed():
    model = build_walking_model()

    calm = create_passenger(current_stress=0.1)
    stressed = create_passenger(current_stress=0.9)

    calm_speed = model.calculate_effective_speed(calm)
    stressed_speed = model.calculate_effective_speed(stressed)

    assert stressed_speed < calm_speed


def test_stress_factor_is_deterministic():
    model = build_walking_model()

    passenger = create_passenger(current_stress=0.6)

    first = model.calculate_effective_speed(passenger)
    second = model.calculate_effective_speed(passenger)

    assert first == second


def test_high_resilience_buffers_stress_impact():
    model = build_walking_model()

    low_resilience = create_passenger(
        stress_resilience=0.0,
        current_stress=0.9,
    )
    high_resilience = create_passenger(
        stress_resilience=1.0,
        current_stress=0.9,
    )

    low_speed = model.calculate_effective_speed(low_resilience)
    high_speed = model.calculate_effective_speed(high_resilience)

    assert high_speed > low_speed


def test_fitness_increases_walking_speed():
    model = build_walking_model()

    low_fitness = create_passenger(current_stress=0.2)
    low_fitness.traits.fitness = 0.0

    high_fitness = create_passenger(current_stress=0.2)
    high_fitness.traits.fitness = 1.0

    assert (
        model.calculate_effective_speed(high_fitness)
        > model.calculate_effective_speed(low_fitness)
    )


def test_stress_model_initial_stress_within_range():
    model = StressModel()

    for _ in range(50):
        stress = model.calculate_initial_stress(stress_resilience=0.5)
        assert 0.0 <= stress <= 1.0


def test_time_pressure_raises_stress_when_late():
    model = StressModel()

    # Comfortable: plenty of time -> no pressure
    assert model.calculate_time_pressure(time_remaining=400, required_time=100) == 0.0

    # Critical: no time left -> maximum pressure
    assert model.calculate_time_pressure(time_remaining=50, required_time=100) == 1.0
