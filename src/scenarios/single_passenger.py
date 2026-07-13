from datetime import date, datetime, timedelta

from ..world.passenger import Passenger
from ..simulation.event import SimulationEvent
from ..enums.world_enums import Gender, DocumentType
from ..enums.simulation_enums import EventType, StatesType
from ..simulation.engine import SimulationEngine
from ..simulation.clock import SimulationClock


# ==== Nuestro primer pasajero ======

# Nombre: Juan
# Apellido: Maldacena
# Nacimiento: 10/09/1968

passsenger_0 = Passenger(
    first_name="Juan",
    last_name="Maldacena",
    birth_date=date(1968, 9, 10),
    gender=Gender.MALE,
    nationality="AR",
    document_type=DocumentType.DNI,
    document_number="19324548",
    email="juanmartinmaldacena@gmail.com",
    phone="+549221328901",
)

# ====== Lista de Eventos =======

# Orden de eventos
travel_plan = [
    EventType.CREATED,
    EventType.LEAVE_HOME,
    EventType.ARRIVE_AIRPORT,
    EventType.CHECK_IN_COMPLETED,
    EventType.SECURITY_COMPLETED,
    EventType.BOARDING_STARTED,
    EventType.PASSENGER_BOARDED,
    EventType.AIRCRAFT_TAKE_OFF,
    EventType.AIRCRAFT_LANDED,
    EventType.EXIT_AIRCRAFT,
    EventType.EXIT_AIRPORT,
]


def ejecutar_simulacion():
    # Crear el reloj de simulación
    clock = SimulationClock(current_time=datetime.now())

    # Crear el motor de simulación
    engine = SimulationEngine(clock=clock, events=[])

    # Crear eventos para el pasajero
    for i, event_type in enumerate(travel_plan):
        event_time = clock.current_time + timedelta(
            minutes=i * 10
        )  # Cada evento ocurre 10 minutos después del anterior
        event = SimulationEvent(
            event_time=event_time, event_type=event_type, entity=passsenger_0
        )
        engine.add_event(event)

    # Ejecutar la simulación
    engine.run()


if __name__ == "__main__":
    ejecutar_simulacion()
