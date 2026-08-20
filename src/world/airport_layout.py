from dataclasses import dataclass

from .airport_location import AirportLocation


@dataclass(slots=True)
class AirportLayout:
    airport_code: str
    width: float
    height: float
    locations: dict[str, AirportLocation]

    def get_location(self, location_code: str) -> AirportLocation:
        location = self.locations.get(location_code)

        if location is None:
            available = ", ".join(sorted(self.locations.keys()))

            raise ValueError(
                f"Location '{location_code}' not found in airport "
                f"'{self.airport_code}'. "
                f"Available locations: {available}"
            )

        return location

    def get_gate_location(self, gate_code: str) -> AirportLocation:
        return self.get_location(f"gate_{gate_code}")
