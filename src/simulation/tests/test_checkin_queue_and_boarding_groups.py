from datetime import datetime, timedelta

from src.simulation.world_factory import generate_world
from src.simulation.simulation_runner import SimulationRunner
from src.simulation.generators.passenger_journey import (
    _boarding_window,
)
from src.simulation.queues.checkin_queue import CheckInQueue
from src.world.models.queue_service_model import QueueServiceModel
from src.world.passenger import Passenger
from src.world.passenger_traits import PassengerTraits
from src.enums.world_enums import (
    BoardingGroup,
    DocumentType,
    Gender,
    TravelPurpose,
    FlightMilestone,
)
from src.enums.simulation_enums import EventType


def _make_flight():
    world = generate_world(
        n_airports=2,
        n_flights=1,
        n_passengers=1,
        simulation_date=datetime(2026, 7, 13),
        seed=1,
    )
    return world.flights[0]


def _make_passenger(online_checkin=0.5, baggage=0.5) -> Passenger:
    return Passenger(
        first_name="A",
        last_name="B",
        birth_date=datetime(1990, 1, 1).date(),
        gender=Gender.MALE,
        nationality="AR",
        document_type=DocumentType.DNI,
        document_number="12345678",
        email="a@b.com",
        phone="1234",
        travel_purpose=TravelPurpose.BUSINESS,
        traits=PassengerTraits(
            fitness=0.5,
            stress_resilience=0.5,
            distraction_proneness=0.3,
            travel_experience=5,
        ),
        online_checkin_probability=online_checkin,
        baggage_probability=baggage,
    )


# ---------------------------------------------------------------------------
# A1 — Cola de mostrador de check-in
# ---------------------------------------------------------------------------


def test_checkin_queue_congests_with_few_service_points():
    world = generate_world(
        n_airports=2,
        n_flights=1,
        n_passengers=10,
        simulation_date=datetime(2026, 7, 13),
        seed=2,
    )

    queue = CheckInQueue(service_points=2)

    arrival = datetime(2026, 7, 13, 10, 0, 0)

    results = [
        queue.process(
            passenger=b.passenger,
            arrival_time=arrival,
        )
        for b in world.bookings
    ]

    assert len(results) == 10

    waits = [r.waiting_time for r in results]

    assert any(w > 0 for w in waits)
    assert any(r.congested for r in results)

    # Los dos primeros encuentran mostrador libre; a partir del tercero
    # empieza a formarse cola.
    waiting_indices = [i for i, r in enumerate(results) if r.waiting_time > 0]
    assert len(waiting_indices) >= 1
    assert min(waiting_indices) >= 2


def test_online_checkin_is_faster_than_counter():
    model = QueueServiceModel()

    online_px = _make_passenger(online_checkin=1.0, baggage=0.0)
    counter_px = _make_passenger(online_checkin=0.0, baggage=1.0)

    online_times = [
        model.calculate_checkin_time(online_px, online=True) for _ in range(50)
    ]
    counter_times = [
        model.calculate_checkin_time(counter_px, online=False) for _ in range(50)
    ]

    assert max(online_times) < min(counter_times)


def test_checkin_queue_variation_defaults_work_on_world():
    world = generate_world(
        n_airports=2,
        n_flights=1,
        n_passengers=5,
        simulation_date=datetime(2026, 7, 13),
        seed=3,
    )

    runner = SimulationRunner()
    result = runner.run(world.bookings)

    completed = [
        e
        for e in result.events
        if e.event_type == EventType.CHECK_IN_COMPLETED
    ]

    assert len(completed) == len(world.bookings)

    for e in completed:
        assert "queue_wait" in e.payload
        assert "service_time" in e.payload
        assert "checkin_occupancy" in e.payload
        assert "checkin_congested" in e.payload


# ---------------------------------------------------------------------------
# A3 — Embarque por grupos
# ---------------------------------------------------------------------------


def test_boarding_window_orders_groups_correctly():
    flight = _make_flight()

    priority_start, _ = _boarding_window(flight, BoardingGroup.PRIORITY)
    group2_start, _ = _boarding_window(flight, BoardingGroup.GROUP_2)
    group5_start, group5_end = _boarding_window(flight, BoardingGroup.GROUP_5)

    doors_close = flight.scheduled_departure - timedelta(minutes=15)

    assert priority_start < group2_start < group5_start
    assert group5_end <= doors_close


def test_boarding_window_within_boarding_span():
    flight = _make_flight()
    boarding_start = flight.get_milestone(FlightMilestone.BOARDING_START)

    for group in BoardingGroup:
        start, end = _boarding_window(flight, group)
        assert boarding_start <= start < end


def test_boarded_event_carries_group_and_respects_window():
    world = generate_world(
        n_airports=2,
        n_flights=1,
        n_passengers=20,
        simulation_date=datetime(2026, 7, 13),
        seed=4,
    )

    runner = SimulationRunner()
    result = runner.run(world.bookings)

    boarded = [
        e
        for e in result.events
        if e.event_type == EventType.PASSENGER_BOARDED and e.payload.get("boarding_group")
    ]

    assert boarded

    for e in boarded:
        assert e.event_time >= e.payload["group_window_start"]
        assert e.event_time <= e.payload["boarding_deadline"]


def test_export_includes_boarding_group():
    world = generate_world(
        n_airports=2,
        n_flights=1,
        n_passengers=20,
        simulation_date=datetime(2026, 7, 13),
        seed=4,
    )

    result = SimulationRunner().run(world.bookings)

    dicts = result.to_event_dicts()

    boarded = [
        d
        for d in dicts
        if d["event"] == EventType.PASSENGER_BOARDED.value
        and "boarding_group" in d
    ]

    assert len(boarded) == len(
        [e for e in result.events if e.event_type == EventType.PASSENGER_BOARDED]
    )
    assert all(d["boarding_group"] for d in boarded)
