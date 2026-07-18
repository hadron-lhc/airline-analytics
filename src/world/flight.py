from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..enums.world_enums import FlightStatus, FlightMilestone
from .airport import Airport
from .gate import Gate


@dataclass(slots=True)
class Flight:
    flight_number: str
    origin_airport: Airport
    destination_airport: Airport
    scheduled_departure: datetime
    scheduled_arrival: datetime
    gate: Gate
    status: FlightStatus = FlightStatus.SCHEDULED

    milestones: dict[FlightMilestone, datetime] = field(init=False)

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

    def get_milestone(self, milestone: FlightMilestone) -> datetime:
        return self.milestones[milestone]

    @property
    def handler(self):
        from ..simulation.handlers.flight_handler import flight_handler

        return flight_handler
