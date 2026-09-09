from datetime import datetime

from src.simulation.generators.passenger_journey import PassengerJourney
from src.simulation.simulation_runner import SimulationRunner
from src.simulation.replay import SimulationReplay
from src.simulation.world_factory import generate_world
from src.simulation.runner import run_simulation
from src.enums.simulation_enums import EventType


def create_test_world(n_passengers=8):
    return generate_world(
        n_airports=2,
        n_flights=1,
        n_passengers=n_passengers,
        simulation_date=datetime(2026, 7, 13),
    )


def test_run_simulation_entry_point_produces_events():
    world = create_test_world()

    result = run_simulation(world)

    assert result.events
    assert result.world is not None


def test_run_simulation_captures_initial_world_and_replay_is_supported():
    """El punto de entrada público run_simulation debe capturar initial_world
    para que el resultado sea reproducible con SimulationReplay."""
    world = create_test_world()

    result = run_simulation(world)

    assert result.initial_world is not None
    assert len(result.initial_world.passengers) == len(world.bookings)

    replay = SimulationReplay(result)
    replay.seek(replay.frame_count)

    states = {p.state.value for p in replay.current_world.passengers}

    assert "Exited Airport" in states


def test_run_simulation_events_are_chronological_and_counted():
    world = create_test_world()

    result = run_simulation(world)

    times = [e.event_time for e in result.events]

    assert times == sorted(times)

    total = sum(
        1
        for e in result.events
        if e.event_type in (EventType.PASSENGER_BOARDED, EventType.MISSED_FLIGHT)
    )

    assert total == len(world.bookings)


def test_generate_world_at_realistic_scale_does_not_crash():
    """Valida el pipeline completo a un tamaño realista (el bug de capacidad
    habría hecho fallar generate_bookings con un vuelo lleno de asientos)."""
    from datetime import datetime

    world = generate_world(
        n_airports=12,
        n_flights=20,
        n_passengers=1500,
        simulation_date=datetime(2026, 7, 13),
    )

    result = run_simulation(world)

    for flight in world.flights:
        assert flight.passenger_count <= flight.capacity

    total = sum(
        1
        for e in result.events
        if e.event_type in (EventType.PASSENGER_BOARDED, EventType.MISSED_FLIGHT)
    )

    assert total == len(result.world.bookings)


def test_runner_generates_complete_timeline():
    world = create_test_world()

    runner = SimulationRunner()
    result = runner.run(world.bookings)

    event_types = {event.event_type for event in result.events}

    assert EventType.ARRIVE_AIRPORT in event_types
    assert EventType.ARRIVE_CHECK_IN in event_types
    assert EventType.CHECK_IN_COMPLETED in event_types
    assert EventType.ARRIVE_SECURITY in event_types
    assert EventType.SECURITY_STARTED in event_types
    assert EventType.SECURITY_COMPLETED in event_types
    assert EventType.ARRIVE_GATE in event_types

    total = sum(
        1
        for event in result.events
        if event.event_type in (EventType.PASSENGER_BOARDED, EventType.MISSED_FLIGHT)
    )
    assert total == len(world.bookings)


def test_runner_events_are_chronological():
    world = create_test_world()

    runner = SimulationRunner()
    result = runner.run(world.bookings)

    times = [event.event_time for event in result.events]

    assert times == sorted(times)


def test_runner_captures_initial_world():
    world = create_test_world()

    runner = SimulationRunner()
    result = runner.run(world.bookings)

    assert result.initial_world is not None
    assert len(result.initial_world.passengers) == len(world.bookings)


def test_replay_rebuilds_result_without_error():
    world = create_test_world()

    runner = SimulationRunner()
    result = runner.run(world.bookings)

    replay = SimulationReplay(result)

    assert replay.frame_count == len(result.events)
    assert replay.start_time == result.events[0].event_time
    assert replay.end_time == result.events[-1].event_time


def test_replay_frames_follow_chronological_order():
    world = create_test_world()

    runner = SimulationRunner()
    result = runner.run(world.bookings)

    replay = SimulationReplay(result)

    times = [frame.time for frame in replay.timeline]

    assert times == sorted(times)


def test_replay_mutates_world_state_through_handlers():
    world = create_test_world()

    runner = SimulationRunner()
    result = runner.run(world.bookings)

    replay = SimulationReplay(result)
    replay.seek(replay.frame_count)

    states = {passenger.state.value for passenger in replay.current_world.passengers}

    assert "Exited Airport" in states


def test_replay_advances_through_intermediate_states():
    world = create_test_world(n_passengers=20)

    runner = SimulationRunner()
    result = runner.run(world.bookings)

    replay = SimulationReplay(result)
    replay.seek(replay.frame_count // 2)

    states = {passenger.state.value for passenger in replay.current_world.passengers}

    assert states <= {
        "At Home",
        "At Airport",
        "Check In",
        "At Security",
        "Waiting Gate",
        "Boarding",
        "On Flight",
    }


def _world_fingerprint(world, result) -> str:
    """Fingerprint of determinism-sensitive data from a generated world."""
    names = sorted(
        f"{p.first_name}_{p.last_name}_{p.arrival_margin}"
        for p in world.passengers
    )
    events = [
        (e.event_type.value, e.event_time.isoformat())
        for e in result.events
    ]
    gates = sorted(
        e.payload.get("gate", "") for e in result.events if e.payload.get("gate")
    )
    boarding = sorted(
        e.payload.get("status", "")
        for e in result.events
        if e.event_type.value in ("Passenger_Boarded", "Missed_Flight")
    )
    return repr((names, events, gates, boarding))


def test_generate_world_same_seed_is_reproducible():
    """Dos mundos generados con la misma semilla deben ser idénticos, incluso
    en el mismo proceso (el estado global de aeropuertos no debe filtrarse)."""
    w1 = generate_world(n_airports=4, n_flights=3, n_passengers=60, seed=7)
    r1 = run_simulation(w1)

    w2 = generate_world(n_airports=4, n_flights=3, n_passengers=60, seed=7)
    r2 = run_simulation(w2)

    assert _world_fingerprint(w1, r1) == _world_fingerprint(w2, r2)


def test_generate_world_different_seed_differs():
    """Semillas distintas deben producir mundos distintos."""
    w1 = generate_world(n_airports=4, n_flights=3, n_passengers=60, seed=7)
    r1 = run_simulation(w1)

    w2 = generate_world(n_airports=4, n_flights=3, n_passengers=60, seed=8)
    r2 = run_simulation(w2)

    assert _world_fingerprint(w1, r1) != _world_fingerprint(w2, r2)
