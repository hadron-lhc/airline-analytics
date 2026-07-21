from ..world.passenger import Passenger
from ..world.flight import Flight


class SimulationLogger:
    def __init__(self):
        self._log = []

    def log(self, event):
        entity = event.entity
        time_str = event.event_time.strftime("%H:%M")
        event_name = event.event_type.value

        if isinstance(entity, Passenger):
            gate_str = entity.current_gate.gate_code if entity.current_gate else "None"
            seat = (
                entity.current_booking.seat
                if entity.current_booking and entity.current_booking.seat
                else None
            )
            seat_str = seat.seat_number if seat else "None"
            row = (
                f"{time_str:<6} {event_name:<22} "
                f"{entity.first_name + ' ' + entity.last_name:<22} "
                f"{entity.state.value:<22} "
                f"{gate_str} "
                f"{seat_str}"
            )
        elif isinstance(entity, Flight):
            row = (
                f"{time_str:<6} {event_name:<22} "
                f"{entity.flight_number:<22} "
                f"{entity.status.value:<18} "
                f"{''}"
            )
        else:
            row = f"{time_str:<6} {event_name:<22} {str(entity):<22}"

        self._log.append(row)
        print(row)

    def show_summary(self):
        print()
        print("\u2550" * 75)
        print("  COMPLETE TIMELINE")
        print("\u2550" * 75)
        header = (
            f"{'Time':<6} {'Event':<22} "
            f"{'Passenger/Flight':<22} "
            f"{'State':<18} "
            f"{'Gate':<6}"
            f"{'Seat':<6}"
        )
        print(header)
        print("\u2500" * 75)
        for row in self._log:
            print(row)
        print("\u2550" * 75)
