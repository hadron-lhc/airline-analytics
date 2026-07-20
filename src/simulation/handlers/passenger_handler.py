from ...enums.simulation_enums import EventType
from ...enums.world_enums import PassengerState


class PassengerHandler:
    _handlers = {
        EventType.LEAVE_HOME: "_handle_leave_home",
        EventType.ARRIVE_AIRPORT: "_handle_arrive_airport",
        EventType.CHECK_IN_COMPLETED: "_handle_checkin_completed",
        EventType.SECURITY_COMPLETED: "_handle_security_completed",
        EventType.BOARDING_STARTED: "_handle_boarding_started",
        EventType.PASSENGER_BOARDED: "_handle_passenger_boarded",
        EventType.AIRCRAFT_TAKE_OFF: "_handle_aircraft_take_off",
        EventType.AIRCRAFT_LANDED: "_handle_aircraft_landed",
        EventType.EXIT_AIRCRAFT: "_handle_exit_aircraft",
        EventType.EXIT_AIRPORT: "_handle_exit_airport",
    }

    def process(self, event):
        handler_name = self._handlers.get(event.event_type)
        if handler_name:
            getattr(self, handler_name)(event)

    def _handle_leave_home(self, event):
        event.entity.state = PassengerState.GOING_TO_AIRPORT

    def _handle_arrive_airport(self, event):
        passenger = event.entity
        flight = event.payload.get("flight")
        passenger.state = PassengerState.AT_AIRPORT
        if flight:
            passenger.current_airport = flight.origin_airport

    def _handle_checkin_completed(self, event):
        passenger = event.entity
        passenger.checked_in = True
        passenger.state = PassengerState.AT_SECURITY

    def _handle_security_completed(self, event):
        passenger = event.entity
        flight = event.payload.get("flight")
        passenger.current_gate = flight.gate
        passenger.state = PassengerState.WAITING_GATE

    def _handle_boarding_started(self, event):
        if event.entity.state == PassengerState.WAITING_GATE:
            event.entity.state = PassengerState.BOARDING

    def _handle_passenger_boarded(self, event):
        passenger = event.entity
        passenger.state = PassengerState.ON_FLIGHT
        passenger.boarded = True
        passenger.current_gate = None

    def _handle_aircraft_take_off(self, event):
        event.entity.state = PassengerState.ON_FLIGHT

    def _handle_aircraft_landed(self, event):
        passenger = event.entity
        flight = event.payload.get("flight")
        passenger.state = PassengerState.ARRIVED
        if flight:
            passenger.current_airport = flight.destination_airport.iata_code

    def _handle_exit_aircraft(self, event):
        event.entity.state = PassengerState.AT_DESTINATION_AIRPORT

    def _handle_exit_airport(self, event):
        passenger = event.entity
        passenger.state = PassengerState.EXITED_AIRPORT
        if passenger.current_flight:
            passenger.last_flight = passenger.current_flight
        passenger.current_flight = None


passenger_handler = PassengerHandler()
