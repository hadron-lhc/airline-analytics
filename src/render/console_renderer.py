from collections import Counter
from datetime import datetime

from ..enums.world_enums import FlightStatus, PassengerState
from ..world.simulation_world import SimulationWorld


_PASSENGER_ORDER = [
    (PassengerState.AT_HOME, "At home"),
    (PassengerState.GOING_TO_AIRPORT, "Travelling"),
    (PassengerState.AT_AIRPORT, "At airport"),
    (PassengerState.CHECK_IN, "Check-in"),
    (PassengerState.AT_SECURITY, "Security"),
    (PassengerState.WAITING_GATE, "Gate"),
    (PassengerState.BOARDING, "Boarding"),
    (PassengerState.ON_FLIGHT, "Flying"),
    (PassengerState.ARRIVED, "Arrived"),
    (PassengerState.AT_DESTINATION_AIRPORT, "Destination"),
    (PassengerState.EXITED_AIRPORT, "Exited"),
]

_FLIGHT_LABELS = {
    FlightStatus.SCHEDULED: "Scheduled",
    FlightStatus.BOARDING: "Boarding",
    FlightStatus.DEPARTED: "Flying",
    FlightStatus.LANDED: "Landed",
    FlightStatus.CANCELLED: "Cancelled",
}


class ConsoleRenderer:
    """Capa de presentación del estado del mundo.

    Independiente del replay: recibe un `SimulationWorld` (por ejemplo
    `replay.current_world`) y devuelve un texto. No imprime, no analiza:
    solo embellece los datos.
    """

    def __init__(self, width: int = 66):
        self.width = width

    def render_airport(
        self,
        world: SimulationWorld,
        airport_code: str,
        time: datetime | None = None,
    ) -> str:
        top = "═" * self.width
        sep = "─" * self.width

        if not any(a.iata_code == airport_code for a in world.airports):
            return "\n".join([top, f"Airport {airport_code} not found", top])

        flights = [
            f
            for f in world.flights
            if f.origin_airport.iata_code == airport_code
            or f.destination_airport.iata_code == airport_code
        ]

        time_str = time.strftime("%H:%M") if time else "—"

        lines = [
            top,
            f"Time: {time_str}",
            "",
            f"Airport: {airport_code}",
            "",
            "Flights",
            sep,
        ]
        if flights:
            lines.extend(f"{f.flight_number:<8}{_FLIGHT_LABELS[f.status]}" for f in flights)
        else:
            lines.append("(no flights)")

        counts = Counter(p.state for p in world.passengers)
        lines.append("")
        lines.append("Passengers")
        lines.append(sep)
        for state, label in _PASSENGER_ORDER:
            n = counts[state]
            if n:
                lines.append(f"{label}{'.' * max(1, 21 - len(label))}{n}")
        lines.append(top)
        return "\n".join(lines)
