from enum import Enum


class EventType(Enum):
    CREATED = "Created"

    MOBILE_CHECK_IN = "Mobile_Check_In"

    LEAVE_HOME = "Leave_Home"
    ARRIVE_AIRPORT = "Arrive_Airport"

    ARRIVE_CHECK_IN = "Arrive_Check_In"
    CHECK_IN_COMPLETED = "Check_In_Completed"

    SECURITY_STARTED = "Security_Started"
    SECURITY_COMPLETED = "Security_Completed"

    ARRIVE_GATE = "Arrive_Gate"

    BOARDING_STARTED = "Boarding_Started"
    PASSENGER_BOARDED = "Passenger_Boarded"

    AIRCRAFT_TAKE_OFF = "Aircraft_Take_Off"
    AIRCRAFT_LANDED = "Aircraft_Landed"

    EXIT_AIRCRAFT = "Exit_Aircraft"
    EXIT_AIRPORT = "Exit_Airport"
