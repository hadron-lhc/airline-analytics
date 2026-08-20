from ..simulation.passenger_movement import PassengerMovement
from ..simulation.generators.passenger_factory import create_random_passenger
from ..loaders.airport_layout_loader import load_airport_layout


def main():
    passenger = create_random_passenger()
    airport = load_airport_layout("LAX")

    movement = PassengerMovement()

    entrance = airport.get_location("entrance")
    checkin = airport.get_location("check_in")
    security = airport.get_location("security")
    gate = airport.get_location("gate_C1")

    route = [entrance, checkin, security, gate]

    for i, j in zip(route, route[1:]):
        result = movement.move(passenger, i, j)

        print("----------------------------------------------")
        print(f"Passenger: {passenger.first_name} {passenger.last_name}")
        print("----------------------------------------------")
        print(f"Route: {result.origin} → {result.destination}")
        print(f"Distance: {result.distance:.1f} m")
        print(f"Initial stress: {result.initial_stress:.2f}")
        print(f"Final stress: {result.final_stress:.2f}")
        print(f"Walking speed: {result.walking_speed:.2f} m/s")
        print(f"Walking time: {result.walking_time / 60:.2f} minutes")


if __name__ == "__main__":
    main()
