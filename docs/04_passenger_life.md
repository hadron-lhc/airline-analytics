# Passenger Lifecycle

Este documento describe el ciclo de vida de un pasajero dentro del simulador.

El pasajero no decide cuándo ocurren los eventos del mundo.

El simulador es quien genera los eventos.

El pasajero únicamente reacciona a ellos cambiando de estado.

---

# Conceptos

## Evento

Un evento representa un hecho que ocurre en un instante determinado.

Ejemplos:

- Passenger leaves home
- Passenger arrives at airport
- Boarding starts
- Aircraft departs
- Aircraft lands

Los eventos ocurren en un instante.

No tienen duración.

---

## Estado

El estado representa la condición actual del pasajero.

Siempre existe exactamente un estado activo.

Ejemplos:

- AT_HOME
- AT_AIRPORT
- WAITING_CHECK_IN
- WAITING_SECURITY
- WAITING_GATE
- BOARDING
- ON_FLIGHT
- EXITING_AIRPORT

Los estados poseen duración.

---

## Transición

Una transición ocurre cuando un evento modifica el estado del pasajero.

Ejemplo

Evento:

LEAVE_HOME

↓

Estado:

TRAVELING_TO_AIRPORT

↓

(40 minutos)

↓

Evento:

ARRIVE_AIRPORT

↓

Estado:

AT_AIRPORT

---

# Ciclo de vida

CREATED
│
│ Passenger creado por el generador
▼
AT_HOME
│
│ Evento:
│ LEAVE_HOME
▼
TRAVELING_TO_AIRPORT
│
│ Evento:
│ ARRIVE_AIRPORT
▼
AT_AIRPORT
│
├───────────────────────────┐
│                           │
│                           │
▼                           ▼
WAITING_CHECK_IN     MOBILE_CHECK_IN
│                           │
└───────┬───────────────────┘
        │
        ▼
WAITING_SECURITY
        │
        │ Evento:
        │ SECURITY_COMPLETED
        ▼
WAITING_GATE
        │
        │ Evento:
        │ BOARDING_STARTED
        ▼
BOARDING
        │
        │ Evento:
        │ PASSENGER_BOARDED
        ▼
ON_BOARD
        │
        │ Evento:
        │ AIRCRAFT_TAKEOFF
        ▼
ON_FLIGHT
        │
        │ Evento:
        │ AIRCRAFT_LANDED
        ▼
DISEMBARKING
        │
        │ Evento:
        │ EXIT_AIRCRAFT
        ▼
AT_DESTINATION_AIRPORT
        │
        │ Evento:
        │ EXIT_TERMINAL
        ▼
FINISHED

---

# Eventos que afectan al pasajero

- LEAVE_HOME
- ARRIVE_AIRPORT
- CHECK_IN_COMPLETED
- SECURITY_COMPLETED
- BOARDING_STARTED
- PASSENGER_BOARDED
- AIRCRAFT_DEPARTED
- AIRCRAFT_LANDED
- EXIT_AIRCRAFT
- EXIT_TERMINAL

---

# Estados posibles

- CREATED
- AT_HOME
- TRAVELING_TO_AIRPORT
- AT_AIRPORT
- WAITING_CHECK_IN
- MOBILE_CHECK_IN
- WAITING_SECURITY
- WAITING_GATE
- BOARDING
- ON_FLIGHT
- DISEMBARKING
- AT_DESTINATION_AIRPORT
- FINISHED

---

# Reglas

- Un pasajero solo puede estar en un estado a la vez.
- Todo cambio de estado debe ser provocado por un evento.
- Un evento ocurre en un instante.
- Un estado puede durar desde segundos hasta varias horas.
- El reloj de la simulación avanza de evento en evento.
