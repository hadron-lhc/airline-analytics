from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID, uuid4

from .enums import PassengerState, LoyaltyLevel, Gender, DocumentType


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
    document_number: int
    email: str
    phone: str

    # Travel Profile (Con valores por defecto)
    loyalty_level: LoyaltyLevel = field(default=LoyaltyLevel.NONE)
    preferred_airline: str | None = None
    preferred_seat: str = "Window"
    online_checkin_probability: float = 0.5
    baggage_probability: float = 0.5
    arrival_margin: int = 120
    walking_speed: float = 1.2
    travel_experience: int = 3

    # Simulation State
    state: PassengerState = field(default=PassengerState.CREATED)
    current_airport: str = None
    current_flight: str = None
    current_gate: str = None
    seat_number: str = None
    boarding_time: datetime | None = None
