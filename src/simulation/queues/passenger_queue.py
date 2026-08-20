from dataclasses import dataclass, field

from ...world.passenger import Passenger


@dataclass(slots=True)
class PassengerQueue:
    """
    Simple FIFO queue for passengers waiting for a service.
    """

    name: str
    passengers: list[Passenger] = field(default_factory=list)

    def add(self, passenger: Passenger) -> None:
        """Add a passenger to the end of the queue."""
        self.passengers.append(passenger)

    def pop(self) -> Passenger | None:
        """Remove and return the first passenger in the queue."""
        if not self.passengers:
            return None

        return self.passengers.pop(0)

    def __len__(self) -> int:
        return len(self.passengers)

    @property
    def is_empty(self) -> bool:
        return len(self.passengers) == 0

    def position_of(self, passenger: Passenger) -> int:
        """
        Return the passenger's position in the queue.

        First passenger = 1.
        """
        try:
            return self.passengers.index(passenger) + 1
        except ValueError:
            return -1
