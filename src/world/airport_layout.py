from dataclasses import dataclass
from .airport_location import AirportLocation


@dataclass(slots=True)
class AirportLayout:
    airport_code: str
    width: float
    height: float
    locations: dict[str, AirportLocation]

    def get_location(self, location_code: str) -> AirportLocation | None:
        return self.locations.get(location_code)
