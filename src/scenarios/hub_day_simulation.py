"""Escenario "hub": un aeropuerto grande con 5 aviones y 1000 pasajeros.

Construye un mundo donde todos los vuelos salen de un mismo hub (por defecto
JFK, 8 puertas) hacia 5 destinos distintos. Luego ejecuta la simulación
completa (incluida la fase de llegada hasta que el pasajero sale a la calle)
y muestra métricas de saturación: colas de seguridad, esperas, ocupación y
porcentaje de pasajeros que pierden el vuelo.
"""

from datetime import datetime, timedelta

from src.enums.world_enums import FlightMilestone
from src.enums.simulation_enums import EventType
from src.simulation.generators.airport_factory import get_or_create_airport
from src.simulation.generators.flight_factory import _allocate_gate
from src.simulation.generators.passenger_factory import generate_passengers
from src.simulation.generators.booking_factory import generate_bookings
from src.simulation.runner import run_simulation
from src.simulation.result import SimulationResult
from src.world.flight import Flight
from src.world.simulation_world import SimulationWorld

HUB_CODE = "JFK"

# Destinos con layout disponible, distintos del hub.
DESTINATIONS = ["LAX", "LHR", "CDG", "MAD", "GRU"]

# # en asientos por vuelo: 200 x 5 = 1000 plazas.
SEATS_PER_FLIGHT = 200


def build_hub_world(
    hub_code: str = HUB_CODE,
    destinations: list[str] | None = None,
    n_passengers: int = 1000,
    simulation_date: datetime | None = None,
    staggered: bool = True,
    seed: int | None = None,
) -> SimulationWorld:
    """Construye un mundo con n vuelos saliendo de un único hub.

    - staggered=True: salidas escalonadas a lo largo del día.
    - staggered=False: TODOS los vuelos salen a la misma hora (produce un
      pico de saturación en la cola de seguridad del hub).
    - seed: si se pasa, vuelve reproducible el mundo (mismos pasajeros,
      mismas asignaciones de asiento y de puertas).
    """

    if simulation_date is None:
        simulation_date = datetime(2026, 7, 13)

    if seed is not None:
        from src.simulation.generators.airport_factory import reset_airports
        from src.simulation.generators.passenger_factory import (
            seed_passenger_factory,
        )

        reset_airports()
        seed_passenger_factory(seed)

    if destinations is None:
        destinations = DESTINATIONS

    hub = get_or_create_airport(hub_code)

    flights = []

    for index, dest_code in enumerate(destinations):
        destination = get_or_create_airport(dest_code)

        # Tiempo de vuelo aproximado según la duración media de una ruta.
        duration_min = 240 + index * 30

        if staggered:
            scheduled_departure = simulation_date + timedelta(
                hours=7 + index * 2,
                minutes=0,
            )
        else:
            scheduled_departure = simulation_date + timedelta(hours=7, minutes=0)

        scheduled_arrival = scheduled_departure + timedelta(minutes=duration_min)

        gate = _allocate_gate(hub, scheduled_departure)

        airline = ("AR", "AA", "DL", "UA", "IB")[index % 5]
        flight_number = f"{airline}{1000 + index}"

        flight = Flight(
            flight_number=flight_number,
            origin_airport=hub,
            destination_airport=destination,
            scheduled_departure=scheduled_departure,
            scheduled_arrival=scheduled_arrival,
            gate=gate,
            capacity=SEATS_PER_FLIGHT,
        )

        # Igualamos el inventario de asientos a la capacidad para que
        # quepan todos los pasajeros de la demanda del hub, repartidos en
        # varias clases para producir datos de clase/equipaje variados.
        from src.enums.world_enums import TravelClass

        flight.total_seats = {
            TravelClass.FIRST: 4,
            TravelClass.BUSINESS: 16,
            TravelClass.PREMIUM_ECONOMY: 30,
            TravelClass.ECONOMY: SEATS_PER_FLIGHT - 50,
        }
        flight.__post_init__()

        flights.append(flight)

    passengers = generate_passengers(n=n_passengers)

    bookings = generate_bookings(
        passengers=passengers,
        flights=flights,
    )

    return SimulationWorld(
        airports=[hub] + [f.destination_airport for f in flights],
        flights=flights,
        passengers=passengers,
        bookings=bookings,
    )


def saturation_report(result: SimulationResult) -> None:
    """Imprime métricas de saturación a partir de los eventos generados."""

    events = result.events

    # --- Cola de seguridad ---
    waits = []
    congested = 0
    total_security = 0

    for event in events:
        if event.event_type != EventType.SECURITY_COMPLETED:
            continue
        total_security += 1
        wait = event.payload.get("queue_wait", 0)
        waits.append(wait)
        if event.payload.get("security_congested"):
            congested += 1

    print("\n========== SATURACIÓN — COLAS DE SEGURIDAD ==========")
    print(f"  Pasajeros procesados por seguridad: {total_security}")
    if waits:
        print(f"  Espera media:                       {sum(waits) / len(waits):6.1f} s")
        print(f"  Espera máxima:                      {max(waits):6.1f} s")
        print(f"  Pasajeros con espera > 0:           {sum(1 for w in waits if w > 0)}")
        print(
            f"  % congestión (seguridad):           "
            f"{100 * congested / len(waits):5.1f}%"
        )

    # --- Cola de mostrador de check-in ---
    ck_waits = []
    ck_congested = 0
    total_checkin = 0

    for event in events:
        if event.event_type != EventType.CHECK_IN_COMPLETED:
            continue
        total_checkin += 1
        wait = event.payload.get("queue_wait", 0)
        ck_waits.append(wait)
        if event.payload.get("checkin_congested"):
            ck_congested += 1

    print("\n========== SATURACIÓN — COLAS DE CHECK-IN ==========")
    print(f"  Pasajeros procesados por check-in: {total_checkin}")
    if ck_waits:
        print(f"  Espera media:                       {sum(ck_waits) / len(ck_waits):6.1f} s")
        print(f"  Espera máxima:                      {max(ck_waits):6.1f} s")
        print(
            f"  Pasajeros con espera > 0:           "
            f"{sum(1 for w in ck_waits if w > 0)}"
        )
        print(
            f"  % congestión (check-in):            "
            f"{100 * ck_congested / len(ck_waits):5.1f}%"
        )

    # --- Veredicto de vuelo ---
    boarded = sum(1 for e in events if e.event_type == EventType.PASSENGER_BOARDED)
    missed = sum(1 for e in events if e.event_type == EventType.MISSED_FLIGHT)

    print("\n========== VEREDICTO DE VUELO ==========")
    total_booked = boarded + missed
    print(f"  Pasajeros con reserva:              {total_booked}")
    print(f"  Embarcados:                         {boarded}")
    print(f"  Perdieron el vuelo:                 {missed}")
    if total_booked:
        print(f"  % que perdió el vuelo:              "
              f"{100 * missed / total_booked:5.1f}%")
        print(f"  % que embarcó:                      "
              f"{100 * boarded / total_booked:5.1f}%")
    else:
        print("  (sin reservas)")

    # --- Embarque por grupos ---
    groups = {}
    for event in events:
        if event.event_type == EventType.PASSENGER_BOARDED:
            g = event.payload.get("boarding_group")
            groups[g] = groups.get(g, 0) + 1

    print("\n========== EMBARQUE POR GRUPOS ==========")
    if groups:
        for g in sorted(groups, key=lambda x: (x is None, x or "")):
            print(f"  Grupo {g}: {groups[g]} embarcados")
    else:
        print("  (sin pasajeros embarcados)")

    # --- Ciclo completo hasta salir a la calle ---
    exited = sum(1 for e in events if e.event_type == EventType.EXIT_AIRPORT)

    print("\n========== CICLO COMPLETO ==========")
    print(f"  Pasajeros que salieron a la calle:  {exited}")

    # --- Tiempo medio en el aeropuerto (llegada -> salir a la calle) ---
    from src.world.passenger import Passenger

    per_passenger = {}
    for event in events:
        if not isinstance(event.entity, Passenger):
            continue
        pid = str(event.entity.passenger_id)
        if event.event_type == EventType.ARRIVE_AIRPORT:
            per_passenger.setdefault(pid, {})["arrive"] = event.event_time
        elif event.event_type == EventType.EXIT_AIRPORT:
            per_passenger.setdefault(pid, {})["exit"] = event.event_time

    times = []
    for data in per_passenger.values():
        if "arrive" in data and "exit" in data:
            times.append((data["exit"] - data["arrive"]).total_seconds() / 60)

    if times:
        print(
            f"  Tiempo medio en el aeropuerto:      "
            f"{sum(times) / len(times):6.1f} min"
        )
        print(f"  Tiempo máximo en el aeropuerto:     {max(times):6.1f} min")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Escenario hub: un aeropuerto con 5 aviones y 1000 pasajeros."
    )
    parser.add_argument(
        "--saturar",
        action="store_true",
        help="Hace salir los 5 aviones a la misma hora para saturar la "
        "cola de seguridad (defecto: salidas escalonadas).",
    )
    parser.add_argument(
        "--margen",
        type=int,
        default=None,
        help="Margen de llegada fija para todos los pasajeros (minutos). "
        "Valores bajos (<=45) con --saturar producen pérdidas de vuelo.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Semilla para reproducir el mundo (mismos pasajeros y puertas).",
    )

    args = parser.parse_args()

    staggered = not args.saturar

    print("=" * 62)
    print("  HUB DAY SIMULATION")
    print(f"  Hub: {HUB_CODE} | 5 aviones | 1000 pasajeros")
    print(f"  Modo: {'saturado (salidas simultáneas)' if args.saturar else 'escalonado'}")
    if args.seed is not None:
        print(f"  Semilla: {args.seed}")
    print("=" * 62)

    world = build_hub_world(staggered=staggered, seed=args.seed)

    if args.margen is not None:
        for passenger in world.passengers:
            passenger.arrival_margin = args.margen
        print(f"  Margen de llegada forzado: {args.margen} min")
        print("=" * 62)

    print(f"""
World:
  Airports:   {len(world.airports)}
  Flights:    {len(world.flights)}
  Passengers: {len(world.passengers)}
  Bookings:   {len(world.bookings)}
""")

    print("Vuelos del hub:")
    for flight in world.flights:
        print(
            f"  {flight.flight_number}  "
            f"{flight.origin_airport.iata_code} → "
            f"{flight.destination_airport.iata_code}  "
            f"salida {flight.scheduled_departure.strftime('%H:%M')}  "
            f"gate {flight.gate.gate_code}  "
            f"px {flight.passenger_count}/{flight.capacity}"
        )

    print("\n========== RUNNING SIMULATION ==========")
    result = run_simulation(world)

    saturation_report(result)

    print("\n========== EVENTOS POR TIPO ==========")
    counts = {}
    for event in result.events:
        counts[event.event_type.value] = counts.get(event.event_type.value, 0) + 1
    for key in sorted(counts):
        print(f"  {key:<22} {counts[key]:>5}")

    print(f"\n  Total eventos: {len(result.events)}")


if __name__ == "__main__":
    main()
