from ..world.models.walking_model import WalkingModel
from ..simulation.generators.passenger_factory import create_random_passenger
from ..loaders.airport_layout_loader import load_airport_layout

model = WalkingModel()

passenger = create_random_passenger()
airport_layout = load_airport_layout("LAX")


checkin = airport_layout.get_location("check_in")
security = airport_layout.get_location("security")

distance = checkin.position.distance_to(security.position)


print(f"Passenger: {passenger.first_name} {passenger.last_name}")
print(f"Walking speed: {passenger.walking_speed:.2f} m/s")
print(f"Distance: {distance:.1f} m")

time = model.calculate_time(distance, passenger.walking_speed)

print(f"{time:.1f} seconds")
print(f"Walking time: {time / 60:.1f} minutes")
