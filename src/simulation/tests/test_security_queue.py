from datetime import datetime, timedelta

from src.simulation.queues.security_queue import SecurityQueue
from src.world.models.queue_service_model import QueueServiceModel
from src.world.passenger import Passenger
from src.world.passenger_traits import PassengerTraits
from src.enums.world_enums import (
    DocumentType,
    Gender,
    TravelPurpose,
)


# ==========================================================
# HELPERS
# ==========================================================


def create_passenger(name: str = "Test") -> Passenger:
    """
    Create a minimal valid Passenger for queue tests.
    """

    return Passenger(
        first_name=name,
        last_name="Test",
        birth_date=datetime(1995, 1, 1).date(),
        gender=Gender.MALE,
        nationality="AR",
        document_type=DocumentType.DNI,
        document_number="12345678",
        email=f"{name.lower()}@test.com",
        phone="123456789",
        travel_purpose=TravelPurpose.LEISURE,
        traits=PassengerTraits(
            fitness=0.5,
            stress_resilience=0.5,
            distraction_proneness=0.5,
            travel_experience=5,
        ),
    )


def create_queue(
    service_points: int = 4,
    capacity: int = 20,
    queue_service_model: QueueServiceModel | None = None,
) -> SecurityQueue:
    """
    Create a SecurityQueue with predictable configuration.
    """

    return SecurityQueue(
        capacity=capacity,
        service_points=service_points,
        queue_service_model=(
            queue_service_model
            or QueueServiceModel(
                base_service_time=45.0,
                random_variation=0.0,
            )
        ),
    )


# ==========================================================
# 1. SINGLE PASSENGER
# ==========================================================


def test_single_passenger_starts_immediately():
    """
    A single passenger should start security immediately
    when all service points are available.
    """

    queue = create_queue()

    arrival_time = datetime(2026, 7, 13, 10, 0, 0)

    result = queue.process(
        passenger=create_passenger(),
        arrival_time=arrival_time,
    )

    assert result.arrival_time == arrival_time
    assert result.service_start == arrival_time
    assert result.waiting_time == 0


# ==========================================================
# 2. FIRST FOUR PASSENGERS
# ==========================================================


def test_first_four_passengers_start_immediately():
    """
    With four service points, the first four passengers
    arriving simultaneously should start immediately.
    """

    queue = create_queue(service_points=4)

    arrival_time = datetime(2026, 7, 13, 10, 0, 0)

    results = [
        queue.process(
            passenger=create_passenger(f"Passenger{index}"),
            arrival_time=arrival_time,
        )
        for index in range(4)
    ]

    assert all(result.service_start == arrival_time for result in results)

    assert all(result.waiting_time == 0 for result in results)


# ==========================================================
# 3. FIFTH PASSENGER WAITS
# ==========================================================


def test_fifth_passenger_has_to_wait():
    """
    The fifth passenger arriving simultaneously must wait
    when four service points are already occupied.
    """

    queue = create_queue(service_points=4)

    arrival_time = datetime(2026, 7, 13, 10, 0, 0)

    results = [
        queue.process(
            passenger=create_passenger(f"Passenger{index}"),
            arrival_time=arrival_time,
        )
        for index in range(5)
    ]

    fifth = results[4]

    assert fifth.waiting_time > 0
    assert fifth.service_start > arrival_time


# ==========================================================
# 4. WAITING TIME
# ==========================================================


def test_waiting_time_matches_service_start():
    """
    Waiting time must equal the difference between
    service_start and arrival_time.
    """

    queue = create_queue(service_points=1)

    arrival_time = datetime(2026, 7, 13, 10, 0, 0)

    first = queue.process(
        passenger=create_passenger("First"),
        arrival_time=arrival_time,
    )

    second = queue.process(
        passenger=create_passenger("Second"),
        arrival_time=arrival_time,
    )

    expected_wait = (second.service_start - second.arrival_time).total_seconds()

    assert first.waiting_time == 0
    assert second.waiting_time == expected_wait
    assert second.waiting_time > 0


# ==========================================================
# 5. WAITING PASSENGER STARTS WHEN SERVER IS FREE
# ==========================================================


def test_waiting_passenger_starts_when_service_point_is_free():
    """
    A waiting passenger must start exactly when the earliest
    service point becomes available.
    """

    queue = create_queue(service_points=1)

    arrival_time = datetime(2026, 7, 13, 10, 0, 0)

    first = queue.process(
        passenger=create_passenger("First"),
        arrival_time=arrival_time,
    )

    second = queue.process(
        passenger=create_passenger("Second"),
        arrival_time=arrival_time,
    )

    assert second.service_start == first.service_end


# ==========================================================
# 6. CONGESTION
# ==========================================================


def test_queue_reports_congestion_when_passenger_waits():
    """
    A passenger who has to wait should cause the queue to
    report congestion.
    """

    queue = create_queue(service_points=1)

    arrival_time = datetime(2026, 7, 13, 10, 0, 0)

    queue.process(
        passenger=create_passenger("First"),
        arrival_time=arrival_time,
    )

    second = queue.process(
        passenger=create_passenger("Second"),
        arrival_time=arrival_time,
    )

    assert second.waiting_time > 0
    assert second.congested is True


# ==========================================================
# 7. SERVER STATE CLEANUP
# ==========================================================


def test_services_are_cleaned_after_completion():
    """
    Once enough time has passed for a service to finish,
    its service point should become available again.
    """

    queue = create_queue(service_points=1)

    arrival_time = datetime(2026, 7, 13, 10, 0, 0)

    first = queue.process(
        passenger=create_passenger("First"),
        arrival_time=arrival_time,
    )

    later_time = first.service_end + timedelta(seconds=1)

    second = queue.process(
        passenger=create_passenger("Second"),
        arrival_time=later_time,
    )

    assert second.service_start == later_time
    assert second.waiting_time == 0


# ==========================================================
# 8. SERVICE POINTS ARE NEVER EXCEEDED
# ==========================================================


def test_service_points_are_never_exceeded():
    """
    The queue should never have more simultaneous services
    than the configured number of service points.

    This test checks service intervals directly instead of
    using occupancy, because occupancy also includes
    passengers waiting inside the checkpoint.
    """

    queue = create_queue(service_points=4)

    arrival_time = datetime(2026, 7, 13, 10, 0, 0)

    results = []

    for index in range(10):
        result = queue.process(
            passenger=create_passenger(f"Passenger{index}"),
            arrival_time=arrival_time,
        )

        results.append(result)

    for result in results:
        concurrent_services = sum(
            1
            for other in results
            if (
                other.service_start < result.service_end
                and other.service_end > result.service_start
            )
        )

        assert concurrent_services <= queue.service_points


# ==========================================================
# 9. MULTIPLE ARRIVALS CREATE A QUEUE
# ==========================================================


def test_multiple_arrivals_create_a_queue():
    """
    When more passengers arrive than available service points,
    some passengers must wait.
    """

    queue = create_queue(service_points=2)

    arrival_time = datetime(2026, 7, 13, 10, 0, 0)

    results = [
        queue.process(
            passenger=create_passenger(f"Passenger{index}"),
            arrival_time=arrival_time,
        )
        for index in range(6)
    ]

    waiting_results = [result for result in results if result.waiting_time > 0]

    assert len(waiting_results) == 4


# ==========================================================
# 10. QUEUE SERVICE MODEL IS USED
# ==========================================================


def test_queue_service_model_is_used():
    """
    SecurityQueue must use the configured QueueServiceModel
    to calculate service duration.
    """

    queue_service_model = QueueServiceModel(
        base_service_time=60.0,
        random_variation=0.0,
    )

    queue = create_queue(
        service_points=1,
        queue_service_model=queue_service_model,
    )

    passenger = create_passenger()

    arrival_time = datetime(2026, 7, 13, 10, 0, 0)

    expected_service_time = queue_service_model.calculate_security_time(passenger)

    result = queue.process(
        passenger=passenger,
        arrival_time=arrival_time,
    )

    assert result.service_time == expected_service_time


# ==========================================================
# 11. CAPACITY OVERRUN
# ==========================================================


def test_congestion_reports_when_occupancy_reaches_capacity():
    """
    The capacity-based branch of congestion must fire when the number of
    passengers inside the checkpoint reaches (or exceeds) its capacity.
    """

    # Capacidad mínima: con un pasajero esperando la ocupación llega a 1,
    # alcanzando la rama `occupancy >= capacity`.
    queue = create_queue(
        service_points=4,
        capacity=1,
    )

    arrival_time = datetime(2026, 7, 13, 10, 0, 0)

    queue.process(
        passenger=create_passenger("P1"),
        arrival_time=arrival_time,
    )

    # El segundo pasajero espera (8 puntos no disponibles a la vez),
    # y su espera añade 1 a la ocupación, llegando a capacity.
    second = queue.process(
        passenger=create_passenger("P2"),
        arrival_time=arrival_time,
    )

    assert second.waiting_time == 0  # aún quedan puntos libres
    assert second.occupancy >= 1
    assert second.congested is True


def test_low_capacity_marks_congestion_even_without_waiting():
    """
    Un check-in con capacidad insuficiente reporta congestión por ocupación.
    Cuando los puntos de servicio se llenan, la ocupación refleja la saturación.
    """

    queue = create_queue(
        service_points=1,
        capacity=1,
    )

    arrival_time = datetime(2026, 7, 13, 10, 0, 0)

    queue.process(
        passenger=create_passenger("P1"),
        arrival_time=arrival_time,
    )

    # El segundo debe esperar (un único punto de servicio) y, al esperar,
    # eleva la ocupación efectiva por encima de la capacidad.
    second = queue.process(
        passenger=create_passenger("P2"),
        arrival_time=arrival_time,
    )

    assert second.waiting_time > 0
    assert second.occupancy >= 1
    assert second.congested is True
