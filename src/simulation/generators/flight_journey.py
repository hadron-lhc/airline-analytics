from ...enums.simulation_enums import EventType
from ..event import SimulationEvent
from ...world.flight import Flight
from ...enums.world_enums import FlightMilestone


MILESTONE_EVENT_MAP = {
    FlightMilestone.BOARDING_START: EventType.BOARDING_STARTED,
    FlightMilestone.TAKE_OFF: EventType.AIRCRAFT_TAKE_OFF,
    FlightMilestone.LANDED: EventType.AIRCRAFT_LANDED,
}

FLIGHT_EVENT_ORDER = [
    EventType.BOARDING_STARTED,
    EventType.AIRCRAFT_TAKE_OFF,
    EventType.AIRCRAFT_LANDED,
]


def generate_flight_journey(flight: Flight, passengers: list = None) -> list[SimulationEvent]:
    events = []
    for event_type in FLIGHT_EVENT_ORDER:
        milestone = {v: k for k, v in MILESTONE_EVENT_MAP.items()}[event_type]
        payload = {}
        if event_type == EventType.BOARDING_STARTED and passengers is not None:
            payload["passengers"] = passengers
        event = SimulationEvent(
            event_time=flight.get_milestone(milestone),
            event_type=event_type,
            entity=flight,
            payload=payload,
        )
        events.append(event)
    return events


def show_events(events):
    for event in events:
        print(
            f"Event: {event.event_type.value}, Time: {event.event_time}, Flight: {event.entity.flight_number}"
        )


if __name__ == "__main__":
    from datetime import datetime
    from ...world.airport import Airport
    from ...world.gate import Gate

    flight = Flight(
        flight_number="AR130",
        origin_airport=Airport(
            iata_code="EZE", name="Aeropuerto de Ezeiza", gates=[]
        ),
        destination_airport=Airport(
            iata_code="MIA", name="Aeropuerto Internacional de Miami", gates=[]
        ),
        scheduled_departure=datetime(2026, 7, 13, 12, 0, 0),
        scheduled_arrival=datetime(2026, 7, 13, 21, 30, 0),
        gate=Gate(gate_code="A1"),
    )
    events = generate_flight_journey(flight)
    show_events(events)
