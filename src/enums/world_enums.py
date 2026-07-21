from enum import Enum, auto

# Passengers


class DocumentType(Enum):
    DNI = "Dni"
    PASSPORT = "Passport"
    ID_CARD = "Id_card"
    INE = "Ine"
    AADHAAR = "Aadhaar"
    RG = "Rg"
    CEDULA = "Cédula"


class PassengerState(Enum):
    AT_HOME = "At Home"
    GOING_TO_AIRPORT = "Going to Airport"
    AT_AIRPORT = "At Airport"
    CHECK_IN = "Check In"
    AT_SECURITY = "At Security"
    WAITING_GATE = "Waiting Gate"
    BOARDING = "Boarding"
    ON_FLIGHT = "On Flight"
    ARRIVED = "Arrived"
    AT_DESTINATION_AIRPORT = "At Destination Airport"
    EXITED_AIRPORT = "Exited Airport"


class LoyaltyLevel(Enum):
    NONE = "None"
    SILVER = "Silver"
    GOLD = "Gold"
    PLATINUM = "Platinum"


class Gender(Enum):
    MALE = "M"
    FEMALE = "F"


class FlightStatus(Enum):
    SCHEDULED = "Scheduled"
    BOARDING = "Boarding"
    DEPARTED = "Departed"
    LANDED = "Landed"
    CANCELLED = "Cancelled"


class FlightMilestone(Enum):
    CHECKIN_OPEN = auto()
    CHECKIN_CLOSE = auto()
    BOARDING_START = auto()
    DOORS_CLOSED = auto()
    TAKE_OFF = auto()
    LANDED = auto()


class FlightFullError(Exception):
    pass


# BookingStatus, BoardingGroup, TravelClass


class BookingStatus(Enum):
    RESERVED = "Reserved"
    CONFIRMED = "Confirmed"
    CHECKED_IN = "Checked_in"
    CANCELLED = "Cancelled"
    NO_SHOW = "No_show"
    COMPLETED = "Completed"


class TravelClass(Enum):
    ECONOMY = "Economy"
    PREMIUM_ECONOMY = "Premium Economy"
    BUSINESS = "Business"
    FIRST = "First"


class BoardingGroup(Enum):
    PRIORITY = "Priority"
    GROUP_1 = "Group_1"
    GROUP_2 = "Group_2"
    GROUP_3 = "Group_3"
    GROUP_4 = "Group_4"
    GROUP_5 = "Group_5"


class CurrencyType(Enum):
    USD = "U.S.Dollar"
    EUR = "Euro"
    JPY = "Japanese.Yen"
    GBP = "British.Pound"
    CNY = "Chinese.Yuan"
    AUD = "Australian.Dollar"
    CAD = "Canadian.Dollar"
    CHF = "Swiss.Franc"
    HKD = "Hong.Kong.Dollar"
    SGD = "Singapure.Dollar"
