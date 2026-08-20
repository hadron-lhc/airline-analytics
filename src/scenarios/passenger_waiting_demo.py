from ..simulation.queues.passenger_queue import PassengerQueue
from ..simulation.generators.passenger_factory import generate_passengers
from ..world.models.queue_service_model import QueueServiceModel
from ..simulation.passenger_waiting import PassengerWaitingSimulator


def main():
    passengers = generate_passengers(20)

    queue = PassengerQueue(name="security")

    for passenger in passengers:
        queue.add(passenger)

    service_model = QueueServiceModel()
    waiting_simulator = PassengerWaitingSimulator()

    # Time until the passenger must reach the next milestone.
    time_remaining = 25 * 60

    # Estimated time required after security.
    required_time = 15 * 60

    print("-" * 85)
    print("SECURITY QUEUE + STRESS")
    print("-" * 85)
    print(f"Passengers: {len(queue)}")
    print(f"Time remaining: {time_remaining / 60:.1f} min")
    print(f"Required time:  {required_time / 60:.1f} min")
    print()

    wait_time = 0.0

    for passenger in queue.passengers:
        position = queue.position_of(passenger)

        service_time = service_model.calculate_security_time(passenger)

        current_time_remaining = max(
            time_remaining - wait_time,
            0.0,
        )

        result = waiting_simulator.wait(
            passenger=passenger,
            wait_time=wait_time,
            time_remaining=current_time_remaining,
            required_time=required_time,
        )
        print(
            f"{passenger.first_name} {passenger.last_name:<22}"
            f"position={position:<3} "
            f"wait={wait_time / 60:>5.1f} min "
            f"remaining={current_time_remaining / 60:>5.1f} min "
            f"pressure={result.time_pressure:.2f} "
            f"stress={result.initial_stress:.2f}"
            f" → {result.final_stress:.2f}"
        )
        wait_time += service_time


if __name__ == "__main__":
    main()
