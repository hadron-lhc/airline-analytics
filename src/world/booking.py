from __future__ import annotations
from dataclasses import dataclass, field
from uuid import UUID, uuid4
from datetime import datetime

from .passenger import Passenger
from .seat import Seat
from ..enums.world_enums import BookingStatus, BoardingGroup, TravelClass, CurrencyType

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .flight import Flight


@dataclass(slots=True)
class Booking:
    passenger: Passenger
    flight: Flight

    booking_date: datetime

    booking_status: BookingStatus

    travel_class: TravelClass

    ticket_price: float
    currency: CurrencyType

    booking_id: UUID = field(default_factory=uuid4, init=False)

    seat: Seat | None = None

    checked_baggage: int = 0
    carry_on_baggage: int = 1

    boarding_group: BoardingGroup | None = None

    boarding_time: datetime | None = None
    checked_in: bool = False
    boarded: bool = False

    pnr: str = ""
