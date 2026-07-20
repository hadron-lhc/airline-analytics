from dataclasses import dataclass

from ..enums.world_enums import SeatClass


@dataclass(slots=True)
class Seat:
    seat_number: str
    class_type: SeatClass
    ocuppied: bool = False


def generate_seats(capacity_by_class: dict[SeatClass, int]) -> list[Seat]:
    seats = []
    for seat_class, count in capacity_by_class.items():
        for i in range(1, count + 1):
            row = (i // 6) + 1
            letter = "ABCDEF"[i % 6]
            seats.append(Seat(f"{row}{letter}", seat_class))
    return seats
