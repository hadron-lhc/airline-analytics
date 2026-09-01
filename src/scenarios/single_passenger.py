from datetime import date, datetime

from ..world.passenger import Passenger
from ..world.flight import Flight
from ..world.airport import Airport
from ..world.gate import Gate
from ..enums.world_enums import Gender, DocumentType, TravelPurpose
from ..world.passenger_traits import PassengerTraits

from ..simulation.generators.booking_factory import generate_booking
from ..simulation.simulation_runner import SimulationRunner
from ..simulation.replay import SimulationReplay


def show_summary(passenger):
    print("\n" + "=" * 50)
    print(f"Passenger: {passenger.first_name} {passenger.last_name}")
    print(f"Final state: {passenger.state.value}")
    print(f"Current airport: {passenger.current_airport}")
    current_flight = (
        passenger.current_booking.flight.flight_number
        if passenger.current_booking
        else passenger.last_flight
    )
    print(f"Current flight: {current_flight}")
    boarded = (
        passenger.boarded
        or (passenger.current_booking and passenger.current_booking.boarded)
    )
    checked_in = (
        passenger.checked_in
        or (passenger.current_booking and passenger.current_booking.checked_in)
    )
    print(f"Boarded: {boarded}")
    print(f"Checked in: {checked_in}")
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
        travel_purpose=TravelPurpose.LEISURE,
        traits=PassengerTraits(
            fitness=0.4,
            stress_resilience=0.5,
            distraction_proneness=0.3,
            travel_experience=5,
        ),
    )

    # === Primer vuelo =======

    # De: Argentina, Ezeiza
    # Hasta: Miami
    # Tiempo estimado: 9:30 hs

    flight_0 = Flight(
        flight_number="AR130",
        origin_airport=Airport(iata_code="EZE", name="Aeropuerto de Ezeiza", gates=[]),
        destination_airport=Airport(
            iata_code="MIA", name="Aeropuerto Internacional de Miami", gates=[]
        ),
        scheduled_departure=datetime(2026, 7, 13, 12, 0, 0),
        scheduled_arrival=datetime(2026, 7, 13, 21, 30, 0),
        gate=Gate(gate_code="A1"),
    )

    booking = generate_booking(passenger_0, flight_0)

    runner = SimulationRunner()
    result = runner.run([booking])

    replay = SimulationReplay(result)
    while replay.has_next():
        replay.step()

    final_passenger = replay.current_world.passengers[0]

    print(f"Events generated: {len(result.events)}")

    show_summary(final_passenger)


if __name__ == "__main__":
    main()
