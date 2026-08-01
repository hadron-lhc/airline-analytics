from bisect import bisect_right
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime

from ..world.flight import Flight
from ..world.passenger import Passenger
from ..world.simulation_world import SimulationWorld
from ..enums.simulation_enums import EventType
from ..enums.world_enums import PassengerState

from .clock import SimulationClock
from .engine import SimulationEngine
from .event import SimulationEvent
from .result import SimulationResult


@dataclass(frozen=True, slots=True)
class ReplayFrame:
    index: int
    time: datetime
    event_type: EventType
    entity_kind: str
    entity_id: str


_SHORT_STATES = {
    PassengerState.AT_HOME: "At home",
    PassengerState.GOING_TO_AIRPORT: "Going airport",
    PassengerState.AT_AIRPORT: "At airport",
    PassengerState.CHECK_IN: "Check-in",
    PassengerState.AT_SECURITY: "Security",
    PassengerState.WAITING_GATE: "Gate",
    PassengerState.BOARDING: "Boarding",
    PassengerState.ON_FLIGHT: "Flying",
    PassengerState.ARRIVED: "Arrived",
    PassengerState.AT_DESTINATION_AIRPORT: "Destination",
    PassengerState.EXITED_AIRPORT: "Exited",
}


def _format_idle(delta) -> str:
    total_min = int(delta.total_seconds() // 60)
    hours, minutes = divmod(total_min, 60)
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _entity_info(event: SimulationEvent) -> tuple[str, str]:
    entity = event.entity
    if isinstance(entity, Passenger):
        return "passenger", str(entity.passenger_id)
    if isinstance(entity, Flight):
        return "flight", entity.flight_number
    return type(entity).__name__, str(entity)


@dataclass(slots=True)
class SimulationReplay:
    """Reproductor de la simulación.

    Trabaja sobre un SimulationResult con `initial_world` y re-ejecuta los
    eventos (deterministas) sobre una copia del mundo inicial. Mantiene el
    estado actual en `current_world`, `current_event` y `current_index`.
    """

    result: SimulationResult

    _index: int = field(default=0, init=False)
    _world: SimulationWorld | None = field(default=None, init=False, repr=False)
    _bound_events: list[SimulationEvent] = field(default_factory=list, init=False, repr=False)
    _clock: SimulationClock | None = field(default=None, init=False, repr=False)
    _engine: SimulationEngine | None = field(default=None, init=False, repr=False)
    _timeline: list[ReplayFrame] = field(default_factory=list, init=False, repr=False)
    _times: list[datetime] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self):
        if self.result.initial_world is None:
            raise ValueError(
                "SimulationResult has no initial_world. "
                "Run the simulation via run_simulation() or capture "
                "deepcopy(world) before engine.run() and pass it to the result."
            )
        self._build_timeline()
        self.reset()

    # ── Estado ──────────────────────────────────────────────

    @property
    def current_index(self) -> int:
        return self._index

    @property
    def current_world(self) -> SimulationWorld:
        return self._world

    @property
    def current_event(self) -> SimulationEvent | None:
        if self._index == 0:
            return None
        return self._bound_events[self._index - 1]

    @property
    def current_events(self) -> list[SimulationEvent]:
        return self._bound_events[: self._index]

    @property
    def current_result(self) -> SimulationResult:
        return SimulationResult(
            world=self.current_world,
            events=self.current_events,
            initial_world=self.result.initial_world,
        )

    @property
    def current_time(self) -> datetime:
        return self._clock.current_time

    @property
    def frame_count(self) -> int:
        return len(self.result.events)

    @property
    def start_time(self) -> datetime | None:
        return self.result.events[0].event_time if self.result.events else None

    @property
    def end_time(self) -> datetime | None:
        return self.result.events[-1].event_time if self.result.events else None

    @property
    def timeline(self) -> list[ReplayFrame]:
        return self._timeline

    @property
    def progress(self) -> float:
        if self.frame_count == 0:
            return 0.0
        return self._index / self.frame_count

    @property
    def time_progress(self) -> float:
        if not self.result.events:
            return 0.0
        start, end = self.start_time, self.end_time
        span = (end - start).total_seconds()
        if span <= 0:
            return 0.0
        return (self.current_time - start).total_seconds() / span

    # ── Navegación ──────────────────────────────────────────

    def reset(self) -> None:
        self._index = 0
        self._world = deepcopy(self.result.initial_world)
        self._bound_events = self._bind_events()
        start = self.start_time or datetime.now()
        self._clock = SimulationClock(current_time=start)
        self._engine = SimulationEngine(world=self._world, clock=self._clock)

    def has_next(self) -> bool:
        return self._index < self.frame_count

    def step(self) -> None:
        if not self.has_next():
            raise StopIteration("Replay finished")
        event = self._bound_events[self._index]
        self._clock.advance(event.event_time - self._clock.current_time)
        self._engine.dispatch(event)
        self._index += 1

    def seek(self, index: int) -> None:
        if index < 0 or index > self.frame_count:
            raise IndexError(f"index must be between 0 and {self.frame_count}")
        if index < self._index:
            self.reset()
        while self._index < index:
            self.step()

    def at(self, time: datetime) -> None:
        if not self.result.events:
            return
        self.seek(bisect_right(self._times, time))
        if time > self._clock.current_time:
            self._clock.advance_to(time)

    # ── Estado del mundo ────────────────────────────────────

    def world_statistics(self) -> dict:
        passengers = self._world.passengers
        flights = self._world.flights
        return {
            "time": self._clock.current_time,
            "passengers_by_state": dict(
                Counter(p.state.value for p in passengers)
            ),
            "flights_by_status": dict(Counter(f.status.value for f in flights)),
        }

    def summary(self) -> dict:
        stats = self.world_statistics()
        current = self.current_event
        next_event = (
            self._bound_events[self._index]
            if self._index < self.frame_count
            else None
        )
        return {
            "current_time": self._clock.current_time,
            "current_event": current.event_type if current else None,
            "event_time": current.event_time if current else None,
            "next_event": next_event.event_type if next_event else None,
            "next_event_time": next_event.event_time if next_event else None,
            "idle": (
                self._clock.current_time - current.event_time
                if current
                else None
            ),
            "processed_events": self.current_index,
            "total_events": self.frame_count,
            "event_progress": self.progress,
            "time_progress": self.time_progress,
            "passengers_by_state": stats["passengers_by_state"],
        }

    def print_summary(self, summary: dict | None = None) -> None:
        data = summary if summary is not None else self.summary()

        print("Simulation Time")
        print("─────────────────────────────")
        print()
        print(f"Current time: {data['current_time']:%H:%M}")
        print()
        print("Current state established by:")
        event = data["current_event"]
        if event:
            print(f"{event.value.replace('_', ' ')} @ {data['event_time']:%H:%M}")
        else:
            print("(initial world)")
        print()
        if data["next_event"]:
            print("Next event:")
            print(
                f"{data['next_event'].value.replace('_', ' ')} "
                f"@ {data['next_event_time']:%H:%M}"
            )
        else:
            print("Next event: (fin)")
        print()
        if data["idle"] is not None:
            print("Idle for:")
            print(_format_idle(data["idle"]))
            print()
        print("Events processed:")
        print(f"{data['processed_events']} / {data['total_events']}")
        print()
        print("Progress:")
        print(f"Time:   {data['time_progress']:.0%}")
        print(f"Events: {data['event_progress']:.0%}")
        print()
        print("Passengers")
        print("───────────")
        print()
        for state in PassengerState:
            count = data["passengers_by_state"].get(state.value, 0)
            if count:
                label = _SHORT_STATES[state]
                print(f"{label}{'.' * max(1, 21 - len(label))}{count}")

    # ── Internos ────────────────────────────────────────────

    def _bind_events(self) -> list[SimulationEvent]:
        """Re-vincula los eventos a las entidades copiadas de `current_world`.

        Los eventos de `result.events` apuntan a los objetos originales del
        mundo; al re-ejecutar sobre la copia de trabajo hay que rebindear cada
        evento (y su payload) a las copias para que los handlers muten el mundo
        del replay y no los objetos originales.
        """
        passengers_by_id = {p.passenger_id: p for p in self._world.passengers}
        flights_by_number = {f.flight_number: f for f in self._world.flights}

        bound: list[SimulationEvent] = []
        for event in self.result.events:
            entity = event.entity
            if isinstance(entity, Passenger):
                entity_copy = passengers_by_id[entity.passenger_id]
            elif isinstance(entity, Flight):
                entity_copy = flights_by_number[entity.flight_number]
            else:
                entity_copy = entity

            payload = {}
            flight = event.payload.get("flight")
            if flight is not None:
                payload["flight"] = flights_by_number[flight.flight_number]

            bound.append(
                SimulationEvent(
                    event_time=event.event_time,
                    event_type=event.event_type,
                    entity=entity_copy,
                    payload=payload,
                )
            )
        return bound

    def _build_timeline(self) -> None:
        frames: list[ReplayFrame] = []
        times: list[datetime] = []
        for index, event in enumerate(self.result.events):
            times.append(event.event_time)
            kind, entity_id = _entity_info(event)
            frames.append(
                ReplayFrame(
                    index=index,
                    time=event.event_time,
                    event_type=event.event_type,
                    entity_kind=kind,
                    entity_id=entity_id,
                )
            )
        self._timeline = frames
        self._times = times
