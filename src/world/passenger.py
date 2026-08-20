from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID, uuid4

from ..enums.world_enums import (
    Gender,
    DocumentType,
    LoyaltyLevel,
    PassengerState,
    TravelPurpose,
    SeatPreference,
)

from .passenger_traits import PassengerTraits

from .gate import Gate

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .booking import Booking


@dataclass(slots=True)
class Passenger:
    # Identity
    passenger_id: UUID = field(default_factory=uuid4, init=False)

    first_name: str
    last_name: str
    birth_date: date

    gender: Gender
    nationality: str

    document_type: DocumentType
    document_number: str

    email: str
    phone: str

    # Profile

    travel_purpose: TravelPurpose
    traits: PassengerTraits

    loyalty_level: LoyaltyLevel = LoyaltyLevel.NONE
    preferred_airline: str | None = None
    preferred_seat: SeatPreference = SeatPreference.WINDOW

    online_checkin_probability: float = 0.5
    baggage_probability: float = 0.5

    arrival_margin: int = 120
    walking_speed: float = 1.2
    stress_resilience: float = 0.5

    # Behavioral Traits

    punctuality: int = 0
    patience: int = 0
    risk_tolerance: int = 0

    # Simulation State

    state: PassengerState = PassengerState.AT_HOME

    current_speed: float = 0.0
    current_stress: float = 0.0

    current_airport: str | None = None
    current_gate: Gate | None = None

    current_booking: Booking | None = None

    last_flight: str | None = None
    flight_history: list[str] = field(default_factory=list)

    boarding_time: datetime | None = None

    checked_in: bool = False
    boarded: bool = False

    @property
    def age(self) -> int:
        today = date.today()
        return (
            today.year
            - self.birth_date.year
            - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        )
