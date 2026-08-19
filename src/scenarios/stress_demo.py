from ..simulation.generators.passenger_factory import create_random_passenger
from ..world.models.stress_model import StressModel
from ..world.models.walking_model import WalkingModel
from ..enums.world_enums import StressEvent


def main():
    passenger_1 = create_random_passenger()
    passenger_2 = create_random_passenger()

    passenger_1.stress_resilience = 0.1
    passenger_2.stress_resilience = 0.9

    stress_model = StressModel()
    walking_model = WalkingModel()

    for passenger in [passenger_1, passenger_2]:
        # Estado inicial
        passenger.current_stress = stress_model.calculate_initial_stress(
            passenger.traits.stress_resilience
        )

        print("----------------------------------------------")
        print(f"Passenger: {passenger.first_name} {passenger.last_name}")
        print(f"Stress resilience: {passenger.traits.stress_resilience:.2f}")
        print(f"Base walking speed: {passenger.walking_speed:.2f} m/s")
        print("----------------------------------------------")

        print(f"Initial stress: {passenger.current_stress:.2f}")

        # Calcular velocidad inicial
        passenger.current_speed = walking_model.calculate_effective_speed(passenger)

        print(f"Initial speed: {passenger.current_speed:.2f} m/s")

        print()

        # Simular eventos
        events = [
            StressEvent.WAITING,
            StressEvent.TIME_PRESSURE,
            StressEvent.RUNNING_LATE,
            StressEvent.REACHED_GATE,
        ]

        for event in events:
            passenger.current_stress = stress_model.apply_event(
                passenger,
                event,
            )

            passenger.current_speed = walking_model.calculate_effective_speed(passenger)

            print(f"{event.name}")
            print(f"  Stress: {passenger.current_stress:.2f}")
            print(f"  Speed:  {passenger.current_speed:.2f} m/s")
            print()


if __name__ == "__main__":
    main()
