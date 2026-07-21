from ...enums.simulation_enums import EventType
from ...enums.world_enums import FlightMilestone
from ...world.flight import Flight
from ..event import SimulationEvent


# Relación entre los hitos operativos del vuelo y los eventos de simulación
MILESTONE_EVENT_MAP = {
    FlightMilestone.BOARDING_START: EventType.BOARDING_STARTED,
    FlightMilestone.TAKE_OFF: EventType.AIRCRAFT_TAKE_OFF,
    FlightMilestone.LANDED: EventType.AIRCRAFT_LANDED,
}


# Orden cronológico del ciclo del vuelo
FLIGHT_MILESTONES = [
    FlightMilestone.BOARDING_START,
    FlightMilestone.TAKE_OFF,
    FlightMilestone.LANDED,
]


def generate_flight_journey(flight: Flight) -> list[SimulationEvent]:
    """
    Genera los eventos operativos de un vuelo.

    El vuelo es la única entidad responsable de sus propios eventos:
    - inicio de boarding
    - despegue
    - aterrizaje

    Los pasajeros tienen sus propios eventos mediante Booking.
    """

    events = []

    for milestone in FLIGHT_MILESTONES:
        event = SimulationEvent(
            event_time=flight.get_milestone(milestone),
            event_type=MILESTONE_EVENT_MAP[milestone],
            entity=flight,
            payload={},
        )

        events.append(event)

    return events


def show_events(events: list[SimulationEvent]):
    for event in events:
        print(
            f"[{event.event_time}] "
            f"{event.event_type.value:<25} "
            f"Flight: {event.entity.flight_number}"
        )


if __name__ == "__main__":
    from datetime import datetime

    from ...world.airport import Airport
    from ...world.gate import Gate

    flight = Flight(
        flight_number="AR130",
        origin_airport=Airport(
            iata_code="EZE",
            name="Aeropuerto de Ezeiza",
            gates=[],
        ),
        destination_airport=Airport(
            iata_code="MIA",
            name="Aeropuerto Internacional de Miami",
            gates=[],
        ),
        scheduled_departure=datetime(2026, 7, 13, 12, 0),
        scheduled_arrival=datetime(2026, 7, 13, 21, 30),
        gate=Gate(gate_code="A1"),
    )

    events = generate_flight_journey(flight)

    show_events(events)
