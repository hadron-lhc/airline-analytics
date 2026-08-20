from ..simulation.generators.passenger_factory import create_random_passenger
from ..world.models.stress_model import StressModel


def main():
    passenger = create_random_passenger()
    model = StressModel()

    stress = passenger.current_stress
    resilience = passenger.traits.stress_resilience

    print("-" * 50)
    print("Passenger:", passenger.first_name, passenger.last_name)
    print(f"Stress resilience: {resilience:.2f}")
    print(f"Initial stress: {stress:.2f}")
    print("-" * 50)

    scenarios = [
        ("LOTS OF TIME", 60 * 30, 60 * 10),
        ("COMFORTABLE", 60 * 15, 60 * 10),
        ("TIME PRESSURE", 60 * 11, 60 * 10),
        ("RUNNING LATE", 60 * 5, 60 * 10),
    ]

    for name, time_remaining, required_time in scenarios:
        pressure = model.calculate_time_pressure(
            time_remaining=time_remaining,
            required_time=required_time,
        )

        new_stress = model.recover(
            current_stress=stress,
            duration_minutes=10,
            stress_resilience=resilience,
            time_pressure=pressure,
        )

        print(name)
        print(f"Time pressure: {pressure:.2f}")
        print(f"Stress: {stress:.2f} → {new_stress:.2f}")
        print()


if __name__ == "__main__":
    main()
