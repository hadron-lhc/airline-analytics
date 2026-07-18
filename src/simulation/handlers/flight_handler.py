from ...enums.simulation_enums import EventType
from ...enums.world_enums import FlightStatus, PassengerState


class FlightHandler:
    _handlers = {
        EventType.BOARDING_STARTED: "_handle_boarding_started",
        EventType.AIRCRAFT_TAKE_OFF: "_handle_aircraft_take_off",
        EventType.AIRCRAFT_LANDED: "_handle_aircraft_landed",
    }

    def process(self, event):
        handler_name = self._handlers.get(event.event_type)
        if handler_name:
            getattr(self, handler_name)(event)

    def _print(self, event):
        print(
            f"[{event.event_time}] [FLIGHT] {event.event_type.value} → "
            f"{event.entity.flight_number} ({event.entity.status.value})"
        )

    def _handle_boarding_started(self, event):
        event.entity.status = FlightStatus.BOARDING
        passengers = event.payload.get("passengers", [])
        for p in passengers:
            if p.state == PassengerState.WAITING_GATE:
                p.state = PassengerState.BOARDING
        self._print(event)

    def _handle_aircraft_take_off(self, event):
        event.entity.status = FlightStatus.DEPARTED
        self._print(event)

    def _handle_aircraft_landed(self, event):
        event.entity.status = FlightStatus.LANDED
        self._print(event)


flight_handler = FlightHandler()
