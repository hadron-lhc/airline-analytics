from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ...world.passenger import Passenger
from ...world.models.queue_service_model import QueueServiceModel


@dataclass(slots=True)
class SecurityQueueResult:
    arrival_time: datetime
    service_start: datetime
    service_end: datetime

    waiting_time: float
    service_time: float

    queue_length: int
    occupancy: int

    congested: bool


@dataclass(slots=True)
class SecurityQueue:
    """
    Shared airport security checkpoint.

    capacity:
        Maximum number of passengers simultaneously
        inside the security checkpoint.

    service_points:
        Number of passengers that can be processed
        simultaneously.

    server_available_times:
        Time at which each security service point
        becomes available.

        Example with 4 service points:

            [
                10:00:45,
                10:00:52,
                10:01:03,
                10:00:48,
            ]

        The next passenger will use the service point
        that becomes available first.
    """

    capacity: int = 20
    service_points: int = 4

    queue_service_model: QueueServiceModel = field(default_factory=QueueServiceModel)

    server_available_times: list[datetime | None] = field(default_factory=list)

    pending_starts: list[datetime] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        """
        Initialize one availability slot per service point.
        """

        if self.service_points <= 0:
            raise ValueError("service_points must be greater than zero")

        if self.capacity <= 0:
            raise ValueError("capacity must be greater than zero")

        if not self.server_available_times:
            self.server_available_times = [None for _ in range(self.service_points)]

        elif len(self.server_available_times) != self.service_points:
            raise ValueError(
                "server_available_times must contain exactly service_points entries"
            )

    def _active_service_count(
        self,
        current_time: datetime,
    ) -> int:
        """
        Return the number of service points currently busy.
        """

        return sum(
            1
            for available_time in self.server_available_times
            if available_time is not None and available_time > current_time
        )

    def _settle_pending(self, current_time: datetime) -> None:
        """
        Drop from the queue the passengers whose service has
        already started at ``current_time``.

        ``pending_starts`` records, for each passenger who had
        to wait, the exact instant their service is scheduled
        to begin. Once that instant passes, they are no longer
        waiting and must not count towards the queue length.
        """

        self.pending_starts = [
            starts_at for starts_at in self.pending_starts if starts_at > current_time
        ]

    def _waiting_passenger_count(self, current_time: datetime) -> int:
        """
        Return the number of passengers currently waiting for a
        service point at ``current_time``.

        ``pending_starts`` is the set of scheduled service-start
        times of passengers who had to queue. After discarding
        those who have already begun service, its length is the
        number of passengers still in line.
        """

        self._settle_pending(current_time)

        return len(self.pending_starts)

    def _calculate_service_time(self, passenger: Passenger) -> float:
        """
        Hook: service time per service point. Subclasses override
        this to model a different kind of queue.
        """
        return self.queue_service_model.calculate_security_time(passenger)

    def process(
        self,
        passenger: Passenger,
        arrival_time: datetime,
    ) -> SecurityQueueResult:
        """
        Process one passenger through the shared security queue.

        The service points behave like independent servers.

        If at least one service point is free at arrival_time,
        the passenger starts immediately.

        Otherwise the passenger waits until the service point
        with the earliest availability becomes free.

        Importantly, future reservations are respected.
        This prevents multiple waiting passengers from being
        assigned to the same service point at the same time.
        """

        # ==================================================
        # CURRENT STATE
        # ==================================================

        # Passengers already waiting for a service point (people ahead
        # in the queue), settled so those who have begun service are
        # no longer counted.
        queue_length = self._waiting_passenger_count(arrival_time)

        # ==================================================
        # DETERMINE SERVICE POINT
        # ==================================================

        free_server_index = next(
            (
                index
                for index, available_time in enumerate(self.server_available_times)
                if available_time is None or available_time <= arrival_time
            ),
            None,
        )

        # ==================================================
        # IMMEDIATE SERVICE
        # ==================================================

        if free_server_index is not None:
            service_start = arrival_time

        # ==================================================
        # WAIT FOR EARLIEST SERVER
        # ==================================================

        else:
            free_server_index = min(
                range(self.service_points),
                key=lambda index: self.server_available_times[index],
            )

            service_start = self.server_available_times[free_server_index]

            if service_start is None:
                raise RuntimeError("Invalid security server state")

        # ==================================================
        # SERVICE TIME
        # ==================================================

        service_time = self._calculate_service_time(passenger)

        service_end = service_start + timedelta(seconds=service_time)

        # ==================================================
        # WAITING TIME
        # ==================================================

        waiting_time = (service_start - arrival_time).total_seconds()

        # ==================================================
        # REGISTER SERVER
        # ==================================================

        self.server_available_times[free_server_index] = service_end

        # A passenger who had to wait joins the queue. Their scheduled
        # service-start time lets us drop them once they begin service.
        if waiting_time > 0:
            self.pending_starts.append(service_start)

        # ==================================================
        # OCCUPANCY
        # ==================================================

        occupancy = self._active_service_count(arrival_time)

        # A passenger waiting inside the checkpoint
        # also contributes to physical occupancy.

        if waiting_time > 0:
            occupancy += 1

        # ==================================================
        # CONGESTION
        # ==================================================

        congested = waiting_time > 0 or queue_length > 0 or occupancy >= self.capacity

        # ==================================================
        # RESULT
        # ==================================================

        return SecurityQueueResult(
            arrival_time=arrival_time,
            service_start=service_start,
            service_end=service_end,
            waiting_time=waiting_time,
            service_time=service_time,
            queue_length=queue_length,
            occupancy=occupancy,
            congested=congested,
        )
