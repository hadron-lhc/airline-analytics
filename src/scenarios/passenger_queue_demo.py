from ..simulation.queues.passenger_queue import PassengerQueue
from ..simulation.generators.passenger_factory import generate_passengers
from ..world.models.queue_service_model import QueueServiceModel


def main():
    passengers = generate_passengers(20)

    queue = PassengerQueue(name="security")
    service_model = QueueServiceModel()

    for passenger in passengers:
        queue.add(passenger)

    print("-" * 70)
    print("SECURITY QUEUE")
    print("-" * 70)
    print(f"Passengers: {len(queue)}")
    print()

    wait_time = 0.0

    for passenger in queue.passengers:
        position = queue.position_of(passenger)

        service_time = service_model.calculate_security_time(passenger)

        print(
            f"{passenger.first_name} "
            f"{passenger.last_name:<25}"
            f"position={position:<3} "
            f"wait={wait_time / 60:>5.1f} min "
            f"service={service_time:>5.1f} sec"
        )

        wait_time += service_time

    print()
    print("-" * 70)
    print(f"Total queue clearing time: {wait_time / 60:.1f} min")
    print("-" * 70)


if __name__ == "__main__":
    main()
