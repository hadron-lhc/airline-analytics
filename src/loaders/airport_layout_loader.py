import json
from pathlib import Path

from ..world.airport_layout import AirportLayout
from ..world.airport_location import AirportLocation
from ..world.position import Position

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "airports"


def load_airport_layout(airport_code: str) -> AirportLayout:
    path = DATA_DIR / f"{airport_code.upper()}.json"

    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    locations = {
        code: AirportLocation(
            code=code,
            position=Position(x=loc["x"], y=loc["y"]),
        )
        for code, loc in data["locations"].items()
    }

    return AirportLayout(
        airport_code=data["airport_code"],
        width=data["width"],
        height=data["height"],
        locations=locations,
    )


def load_airport_layouts() -> dict[str, AirportLayout]:
    layouts = {}
    for path in sorted(DATA_DIR.glob("*.json")):
        code = path.stem.upper()
        layouts[code] = load_airport_layout(code)
    return layouts
