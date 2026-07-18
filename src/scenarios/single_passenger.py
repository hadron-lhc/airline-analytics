from datetime import date, datetime

from ..world.passenger import Passenger
from ..world.flight import Flight
from ..world.airport import Airport
from ..world.gate import Gate
from ..enums.world_enums import Gender, DocumentType

from ..simulation.generators.passenger_journey import generate_passenger_journey
from ..simulation.engine import SimulationEngine
from ..simulation.clock import SimulationClock


def show_summary(passenger):
    print("\n" + "=" * 50)
    print(f"Passenger: {passenger.first_name} {passenger.last_name}")
    print(f"Final state: {passenger.state.value}")
    print(f"Current airport: {passenger.current_airport}")
    print(f"Current flight: {passenger.current_flight}")
    print(f"Boarded: {passenger.boarded}")
    print(f"Checked in: {passenger.checked_in}")
    print("=" * 50)


def main():
    # ==== Nuestro primer pasajero ======

    # Nombre: Juan
    # Apellido: Maldacena
    # Nacimiento: 10/09/1968

    passenger_0 = Passenger(
        first_name="Juan",
        last_name="Maldacena",
        birth_date=date(1968, 9, 10),
        gender=Gender.MALE,
        nationality="AR",
        document_type=DocumentType.DNI,
        document_number="19324548",
        email="juanmartinmaldacena@gmail.com",
        phone="+549221328901",
    )

    # === Primer vuelo =======

    # De: Argentina, Ezeiza
    # Hasta: Miami
    # Tiempo estimado: 9:30 hs

    flight_0 = Flight(
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

    events = generate_passenger_journey(passenger_0, flight_0)

    engine = SimulationEngine(
        clock=SimulationClock(current_time=datetime(2026, 7, 13, 0, 0, 0)),
        events=events,
    )

    engine.run()

    show_summary(passenger_0)


if __name__ == "__main__":
    main()
