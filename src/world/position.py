from dataclasses import dataclass
from math import hypot


@dataclass(slots=True)
class Position:
    x: float
    y: float

    def distance_to(self, other: "Position") -> float:
        """Calculate the Euclidean distance to another position."""
        return hypot(self.x - other.x, self.y - other.y)


if __name__ == "__main__":
    pos1 = Position(0, 0)
    pos2 = Position(3, 4)
    print(f"Distance from {pos1} to {pos2}: {pos1.distance_to(pos2)}")
