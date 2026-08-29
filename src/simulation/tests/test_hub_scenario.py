from datetime import datetime

from src.scenarios.hub_day_simulation import build_hub_world
from src.simulation.runner import run_simulation
from src.simulation.replay import SimulationReplay
from src.enums.simulation_enums import EventType


def test_hub_world_has_five_flights_from_single_hub():
    world = build_hub_world(
        n_passengers=100,
        simulation_date=datetime(2026, 7, 13),
    )

    assert len(world.flights) == 5

    origin = world.flights[0].origin_airport.iata_code

    for flight in world.flights:
        assert flight.origin_airport.iata_code == origin


def test_hub_world_capacity_fits_demand():
    world = build_hub_world(
        n_passengers=1000,
        simulation_date=datetime(2026, 7, 13),
    )

    total_seats = sum(flight.capacity for flight in world.flights)

    assert total_seats >= len(world.passengers)


def test_hub_staggered_run_takes_everyone_to_the_street():
    world = build_hub_world(
        n_passengers=200,
        simulation_date=datetime(2026, 7, 13),
        staggered=True,
    )

    result = run_simulation(world)

    boarded = sum(
        1 for e in result.events if e.event_type == EventType.PASSENGER_BOARDED
    )
    exited = sum(1 for e in result.events if e.event_type == EventType.EXIT_AIRPORT)

    assert boarded == len(world.bookings)
    assert exited == boarded


def test_hub_replay_ends_with_exited_passengers():
    world = build_hub_world(
        n_passengers=100,
        simulation_date=datetime(2026, 7, 13),
        staggered=True,
    )

    result = run_simulation(world)

    replay = SimulationReplay(result)
    replay.seek(replay.frame_count)

    states = {p.state.value for p in replay.current_world.passengers}

    assert states == {"Exited Airport"}
