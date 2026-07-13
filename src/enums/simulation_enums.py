from enum import Enum


class EventType(Enum):
    CREATED = "Created"
    MOBILE_CHECK_IN = "Mobile_Check_In"
    LEAVE_HOME = "Leave_Home"
    ARRIVE_AIRPORT = "Arrive_Airport"
    CHECK_IN_COMPLETED = "Check_In_Completed"  # Solo si no lo hizo en casa
    SECURITY_COMPLETED = "Security_Completed"
    BOARDING_STARTED = "Boarding_Started"
    PASSENGER_BOARDED = "Passenger_Boarded"
    AIRCRAFT_TAKE_OFF = "Aircraft_Take_Off"
    AIRCRAFT_LANDED = "Aircraft_Landed"
    EXIT_AIRCRAFT = "Exit_Aircraft"
    EXIT_AIRPORT = "Exit_Airport"


class StatesType(Enum):
    CREATED = "Created"
    AT_HOME = "At_Home"
    TRAVELING_TO_AIRPORT = "Traveling_to_Airport"
    AT_AIRPORT = "At_Airport"
    WAITING_CHECK_IN = "Waiting_Check_In"
    WAITING_SECURITY = "Waiting_Security"
    WAITING_GATE = "Waiting_Gate"
    BOARDING = "Boarding"
    ON_BOARD = "On_Board"
    ON_FLIGHT = "On_Flight"
    DISEMBARKING = "Disembarking"
    AT_DESTINATION_AIRPORT = "At_Destination_Airport"
    FINISHED = "Finished"
