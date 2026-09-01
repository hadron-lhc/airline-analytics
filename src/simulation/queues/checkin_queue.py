import random

from ...world.passenger import Passenger
from .security_queue import SecurityQueue


class CheckInQueue(SecurityQueue):
    """
    Shared airport check-in counter.

    Reuses the multi-server queue logic of SecurityQueue but
    models checkout counter service instead of security screening:

    - Passengers who checked in online only stop at the bag-drop
      kiosk (fast).
    - Passengers who did not check in online use a full counter
      (slow).
    - A shared queue means congestion at check-in propagates to
      everyone who has not checked in online.

    service_points:
        Number of check-in agents working simultaneously.
    """

    service_points: int = 3

    def _calculate_service_time(self, passenger: Passenger) -> float:
        online = random.random() < passenger.online_checkin_probability
        return self.queue_service_model.calculate_checkin_time(
            passenger,
            online=online,
        )
