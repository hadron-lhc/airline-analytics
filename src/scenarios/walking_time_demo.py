from ..world.models.walking_model import WalkingModel
from ..simulation.generators.passenger_factory import (
    generate_passengers,
)
from ..loaders.airport_layout_loader import load_airport_layout

model = WalkingModel()

passengers = generate_passengers(5)
airport_layout = load_airport_layout("LAX")


entrance = airport_layout.get_location("entrance")
checkin = airport_layout.get_location("check_in")
security = airport_layout.get_location("security")
gate_c1 = airport_layout.get_location("gate_C1")

distance_entrance_checkin = entrance.position.distance_to(checkin.position)
distance_checkin_security = checkin.position.distance_to(security.position)
distance_security_gate = security.position.distance_to(gate_c1.position)


for passenger in passengers:
    time_1 = model.calculate_time(distance_entrance_checkin, passenger.walking_speed)
    time_2 = model.calculate_time(distance_checkin_security, passenger.walking_speed)
    time_3 = model.calculate_time(distance_security_gate, passenger.walking_speed)

    print("----------------------------------------------")
    print(f"Passenger: {passenger.first_name} {passenger.last_name}")
    print(f"base walking speed: {passenger.walking_speed:.2f} m/s")
    print("----------------------------------------------")

    print(f"Entrance to Check-in: {time_1 / 60:.1f} minutes")
    effective_speed = model.calculate_speed(passenger.walking_speed)
    print(f"effective speed: {effective_speed:.2f} m/s")
    print()

    print(f"Check-in to Security: {time_2 / 60:.1f} minutes")
    effective_speed = model.calculate_speed(passenger.walking_speed)
    print(f"effective speed: {effective_speed:.2f} m/s")
    print()

    print(f"Security to Gate C1: {time_3 / 60:.1f} minutes")
    effective_speed = model.calculate_speed(passenger.walking_speed)
    print(f"effective speed: {effective_speed:.2f} m/s")

    print()
