from ...enums.simulation_enums import EventType
from ..event import SimulationEvent
from ..time_models import (
    simulate_passenger_arrival,
    simulate_checkin_duration,
    simulate_security_duration,
    simulate_boarding_duration,
    simulate_disembark_duration,
    simulate_exit_airport_duration,
    simulate_trip_to_airport,
)

from ...world.passenger import Passenger
from ...world.flight import Flight
from ...world.airport import Airport
from ...world.gate import Gate
from ...enums.world_enums import Gender, DocumentType, FlightMilestone


from datetime import datetime, date


def calculate_times(passenger, flight):
    travel_duration = simulate_trip_to_airport(passenger)

    arrival_airport = simulate_passenger_arrival(passenger, flight)

    checkin = arrival_airport + simulate_checkin_duration(passenger, flight)

    security = checkin + simulate_security_duration(passenger, flight)

    boarding = flight.get_milestone(FlightMilestone.BOARDING_START)

    boarded = boarding + simulate_boarding_duration(passenger, flight)

    takeoff = flight.get_milestone(FlightMilestone.TAKE_OFF)

    landed = flight.get_milestone(FlightMilestone.LANDED)

    exit_aircraft = landed + simulate_disembark_duration(passenger, flight)

    exit_airport = exit_aircraft + simulate_exit_airport_duration(passenger, flight)

    return {
        EventType.LEAVE_HOME: arrival_airport - travel_duration,
        EventType.ARRIVE_AIRPORT: arrival_airport,
        EventType.CHECK_IN_COMPLETED: checkin,
        EventType.SECURITY_COMPLETED: security,
        EventType.BOARDING_STARTED: boarding,
        EventType.PASSENGER_BOARDED: boarded,
        EventType.AIRCRAFT_TAKE_OFF: takeoff,
        EventType.AIRCRAFT_LANDED: landed,
        EventType.EXIT_AIRCRAFT: exit_aircraft,
        EventType.EXIT_AIRPORT: exit_airport,
    }


def generate_passenger_journey(passenger, flight):
    """
    "Si este pasajero viaja en este vuelo, ¿qué eventos deberían ocurrir?"
    """
    passenger.current_flight = flight.flight_number

    travel_plan = [
        EventType.LEAVE_HOME,
        EventType.ARRIVE_AIRPORT,
        EventType.CHECK_IN_COMPLETED,
        EventType.SECURITY_COMPLETED,
        EventType.BOARDING_STARTED,
        EventType.PASSENGER_BOARDED,
        EventType.AIRCRAFT_TAKE_OFF,
        EventType.AIRCRAFT_LANDED,
        EventType.EXIT_AIRCRAFT,
        EventType.EXIT_AIRPORT,
    ]

    times = calculate_times(passenger, flight)

    events = []

    for event_type in travel_plan:
        event = SimulationEvent(
            event_time=times[event_type],
            event_type=event_type,
            entity=passenger,
            payload={"flight": flight},
        )
        events.append(event)

    return events


def show_events(events):
    for event in events:
        print(
            f"Event: {event.event_type.value}, Time: {event.event_time}, Passenger: {event.entity.first_name} {event.entity.last_name}"
        )


if __name__ == "__main__":
    # Ejemplo de uso
    passenger = Passenger(
        first_name="Oliver",
        last_name="Simth",
        birth_date=date(200, 11, 12),
        gender=Gender.MALE,
        nationality="US",
        document_type=DocumentType.DNI,
        document_number="2391541",
        email="oliversith03@gmail.com",
        phone="+15551253124",
    )
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
    events = generate_passenger_journey(passenger, flight)

    show_events(events)
