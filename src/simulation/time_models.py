from datetime import datetime, timedelta
import random

import numpy as np

from ..world.flight import Flight
from ..world.passenger import Passenger
from ..enums.world_enums import LoyaltyLevel


# =================
# FLIGHT TIMELINE
# ================


def calculate_flight_milestones(flight: Flight) -> dict[str, datetime]:
    """
    Devuelve los hitos operativos de un vuelo.
    Estos tiempos dependen del vuelo, no del pasajero.
    """

    departure = flight.scheduled_departure
    arrival = flight.scheduled_arrival

    return {
        "CHECKIN_OPEN": departure - timedelta(hours=3),
        "CHECKIN_CLOSE": departure - timedelta(hours=1),
        "BOARDING_START": departure - timedelta(minutes=45),
        "DOORS_CLOSE": departure - timedelta(minutes=20),
        "TAKE_OFF": departure,
        "LANDING": arrival,
    }


# ===================
# PASSENGER MODELS
# ==================


def simulate_passenger_arrival(
    passenger: Passenger,
    flight: Flight,
) -> datetime:
    """
    Calcula cuándo llega el pasajero al aeropuerto.
    """

    departure = flight.scheduled_departure

    target_margin = passenger.arrival_margin - passenger.travel_experience * 8

    factor = np.random.beta(3.5, 3.0)

    min_margin = 70
    max_margin = 240

    random_margin = min_margin + factor * (max_margin - min_margin)

    final_margin = (target_margin + random_margin) / 2

    return departure - timedelta(minutes=int(final_margin))


def simulate_checkin_duration(
    passenger: Passenger,
    flight: Flight,
) -> timedelta:
    """
    Tiempo desde que entra al área de check-in hasta que termina.
    """

    has_online_checkin = random.random() < passenger.online_checkin_probability

    has_baggage = random.random() < passenger.baggage_probability

    if has_online_checkin and not has_baggage:
        return timedelta()

    base_wait = 18 if passenger.loyalty_level == LoyaltyLevel.NONE else 6

    wait = np.random.lognormal(
        mean=np.log(base_wait),
        sigma=0.35,
    )

    process = 3.5 if has_baggage else 1.5

    return timedelta(minutes=int(wait + process))


def simulate_security_duration(
    passenger: Passenger,
    flight: Flight,
) -> timedelta:
    """
    Tiempo para atravesar seguridad.
    """

    base = 22

    experience_bonus = (passenger.travel_experience - 3) * 2

    scale = max(10, base - experience_bonus)

    security = np.random.lognormal(
        mean=np.log(scale),
        sigma=0.40,
    )

    return timedelta(minutes=int(security))


def simulate_boarding_duration(
    passenger: Passenger,
    flight: Flight,
) -> timedelta:
    """
    Tiempo desde que comienza el embarque
    hasta que el pasajero llega a su asiento.
    """

    if passenger.loyalty_level == LoyaltyLevel.PLATINUM:
        mean = 3

    elif passenger.loyalty_level == LoyaltyLevel.GOLD:
        mean = 5

    else:
        mean = 8

    boarding = np.random.normal(
        loc=mean,
        scale=1.5,
    )

    boarding = max(1, boarding)

    return timedelta(minutes=int(boarding))


def simulate_disembark_duration(
    passenger: Passenger,
    flight: Flight,
) -> timedelta:
    """
    Tiempo desde el aterrizaje hasta abandonar el avión.
    """

    disembark = np.random.normal(
        loc=12,
        scale=3,
    )

    disembark = max(3, disembark)

    return timedelta(minutes=int(disembark))


def simulate_exit_airport_duration(
    passenger: Passenger,
    flight: Flight,
) -> timedelta:
    """
    Tiempo desde abandonar el avión hasta salir del aeropuerto.
    """

    if passenger.baggage_probability > 0.5:
        mean = 25
    else:
        mean = 10

    exit_time = np.random.normal(
        loc=mean,
        scale=4,
    )

    exit_time = max(5, exit_time)

    return timedelta(minutes=int(exit_time))


def simulate_trip_to_airport(passenger):
    """
    Tiempo desde salir de casa hasta llegar al aeropuerto.
    """

    if passenger.travel_experience < 3:
        mean = 45
    elif passenger.travel_experience < 6:
        mean = 35
    else:
        mean = 25

    trip_time = np.random.normal(
        loc=mean,
        scale=5,
    )

    trip_time = max(10, trip_time)

    return timedelta(minutes=int(trip_time))
