from enum import Enum

# Passengers


class DocumentType(Enum):
    DNI = "Dni"
    PASSPORT = "Passport"


class PassengerState(Enum):
    CREATED = "Created"
    AT_HOME = "At Home"
    GOING_TO_AIRPORT = "Going to Airport"
    CHECK_IN = "Check In"
    SECURITY = "Secutiry"
    WAITING_GATE = "Waiting Gate"
    BOARDING = "Boarding"
    ON_FLIGHT = "On Flight"
    ARRIVED = "Arrived"


class LoyaltyLevel(Enum):
    NONE = "None"
    SILVER = "Silver"
    GOLD = "Gold"
    PLATINUM = "Platinum"


class Gender(Enum):
    MALE = "M"
    FEMALE = "F"


class FlightStates(Enum):
    pass
