from datetime import datetime

from src.simulation.passenger_waiting import PassengerWaitingSimulator
from src.simulation.world_factory import generate_world
from src.simulation.simulation_runner import SimulationRunner
from src.simulation.replay import SimulationReplay
from src.world.passenger import Passenger
from src.world.passenger_traits import PassengerTraits
from src.enums.world_enums import DocumentType, Gender, TravelPurpose
from src.enums.simulation_enums import EventType


def create_passenger(stress_resilience=0.5, current_stress=0.4) -> Passenger:
    return Passenger(
        first_name="Wait",
        last_name="Test",
        birth_date=datetime(1990, 1, 1).date(),
        gender=Gender.MALE,
        nationality="AR",
        document_type=DocumentType.DNI,
        document_number="98765432",
        email="wait@test.com",
        phone="123",
        travel_purpose=TravelPurpose.LEISURE,
        traits=PassengerTraits(
            fitness=0.5,
            stress_resilience=stress_resilience,
            distraction_proneness=0.5,
            travel_experience=5,
        ),
        current_stress=current_stress,
    )


def test_waiting_simulator_mutates_passenger_stress():
    passenger = create_passenger()

    simulator = PassengerWaitingSimulator()

    before = passenger.current_stress

    result = simulator.wait(
        passenger=passenger,
        wait_time=300,
        time_remaining=100,
        required_time=600,
    )

    assert passenger.current_stress != before
    assert result.final_stress == passenger.current_stress


def test_comfortable_waiting_reduces_stress():
    simulator = PassengerWaitingSimulator()

    passenger = create_passenger(current_stress=0.4)

    result = simulator.wait(
        passenger=passenger,
        wait_time=300,
        time_remaining=3600,
        required_time=600,
    )

    assert result.time_pressure == 0.0
    assert result.final_stress <= passenger.current_stress


def test_critical_time_pressure_blocks_recovery():
    simulator = PassengerWaitingSimulator()

    passenger = create_passenger(current_stress=0.4)

    result = simulator.wait(
        passenger=passenger,
        wait_time=300,
        time_remaining=100,
        required_time=600,
    )

    assert result.time_pressure > 0.0


def test_security_wait_generates_time_pressure_in_run():
    # Force many passengers into the airport at the same time so
    # the shared security queue becomes congested.
    world = generate_world(
        n_airports=2,
        n_flights=1,
        n_passengers=30,
        simulation_date=datetime(2026, 7, 13),
    )

    for booking in world.bookings:
        booking.passenger.arrival_margin = 15

    runner = SimulationRunner()
    result = runner.run(world.bookings)

    replay = SimulationReplay(result)
    replay.seek(replay.frame_count)

    completed = [
        event
        for event in result.events
        if event.event_type == EventType.SECURITY_COMPLETED
    ]

    waited = [
        event for event in completed if event.payload.get("queue_wait", 0) > 0
    ]

    assert len(waited) > 0

    pressured = [
        event
        for event in waited
        if event.payload.get("time_pressure", 0.0) > 0.0
    ]

    assert len(pressured) > 0