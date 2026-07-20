from dataclasses import dataclass, field
from datetime import datetime, timedelta
import random

from ..enums.world_enums import (
    FlightStatus,
    FlightMilestone,
    FlightFullError,
    SeatClass,
)
from .airport import Airport
from .gate import Gate
from .passenger import Passenger
from .seat import Seat, generate_seats


@dataclass(slots=True)
class Flight:
    flight_number: str
    origin_airport: Airport
    destination_airport: Airport
    scheduled_departure: datetime
    scheduled_arrival: datetime
    gate: Gate
    status: FlightStatus = FlightStatus.SCHEDULED

    capacity: int = 200
    passengers: list[Passenger] = field(default_factory=list)

    milestones: dict[FlightMilestone, datetime] = field(init=False)

    total_seats: dict[SeatClass, int] = field(
        default_factory=lambda: {SeatClass.ECONOMY: 180}
    )
    _seats: list[Seat] = field(default_factory=list, init=False)
    _available: set[str] = field(default_factory=set, init=False)  # seat_numbers libres
    _occupied: dict[str, Passenger] = field(
        default_factory=dict, init=False
    )  # seat_num -> passenger

    def __post_init__(self):
        self.milestones = {
            FlightMilestone.CHECKIN_OPEN: self.scheduled_departure - timedelta(hours=2),
            FlightMilestone.CHECKIN_CLOSE: self.scheduled_departure
            - timedelta(minutes=30),
            FlightMilestone.BOARDING_START: self.scheduled_departure
            - timedelta(minutes=45),
            FlightMilestone.DOORS_CLOSED: self.scheduled_departure
            - timedelta(minutes=15),
            FlightMilestone.TAKE_OFF: self.scheduled_departure,
            FlightMilestone.LANDED: self.scheduled_arrival,
        }

        self._seats = generate_seats(self.total_seats)
        self._available = {s.seat_number for s in self._seats}

    def assign_seat(self, passenger, preferred_class=SeatClass.ECONOMY) -> Seat:
        candidates = [
            s for s in self._seats
            if s.seat_number in self._available and s.class_type == preferred_class
        ]
        if not candidates:
            candidates = [
                s for s in self._seats if s.seat_number in self._available
            ]
        if not candidates:
            raise FlightFullError(
                f"No seats available on {self.flight_number}"
            )
        seat = random.choice(candidates)
        self._available.remove(seat.seat_number)
        self._occupied[seat.seat_number] = passenger
        return seat

    def get_milestone(self, milestone: FlightMilestone) -> datetime:
        return self.milestones[milestone]

    def add_passenger(self, passenger):
        if len(self.passengers) >= self.capacity:
            raise FlightFullError(
                f"Flight {self.flight_number} is full ({len(self.passengers)}/{self.capacity})"
            )
        self.passengers.append(passenger)

    @property
    def handler(self):
        from ..simulation.handlers.flight_handler import flight_handler

        return flight_handler
