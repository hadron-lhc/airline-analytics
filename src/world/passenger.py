from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID, uuid4

from ..enums.world_enums import (
    Gender,
    DocumentType,
    LoyaltyLevel,
    PassengerState,
)
from .gate import Gate

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .booking import Booking


@dataclass(slots=True)
class Passenger:
    # ───────── Identity ─────────
    passenger_id: UUID = field(default_factory=uuid4, init=False)

    first_name: str
    last_name: str
    birth_date: date

    gender: Gender
    nationality: str

    document_type: DocumentType
    document_number: int

    email: str
    phone: str

    # ───────── Travel Profile ─────────

    loyalty_level: LoyaltyLevel = LoyaltyLevel.NONE
    preferred_airline: str | None = None
    preferred_seat: str = "Window"

    online_checkin_probability: float = 0.5
    baggage_probability: float = 0.5

    arrival_margin: int = 120
    walking_speed: float = 1.2
    travel_experience: int = 3

    # ───────── Simulation State ─────────

    state: PassengerState = PassengerState.AT_HOME

    current_airport: str | None = None
    current_gate: Gate | None = None

    current_booking: Booking | None = None

    last_flight: str | None = None
    flight_history: list[str] = field(default_factory=list)

    boarding_time: datetime | None = None

    checked_in: bool = False
    boarded: bool = False
