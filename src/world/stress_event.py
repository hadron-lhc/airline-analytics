from enum import Enum, auto


class StressEvent(Enum):
    WAITING = auto()
    TIME_PRESSURE = auto()
    RUNNING_LATE = auto()
    REACHED_GATE = auto()
