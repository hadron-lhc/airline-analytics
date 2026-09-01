# 11. Auditoría de tests y conexión de la simulación

Fecha: 2026-08-28

Este documento resume el estado de la simulación de vuelos, la calidad de sus
tests, los problemas de conexión encontrados y las recomendaciones para
escalar la simulación (más pasajeros, más vuelos, día completo).

---

## 1. Resumen ejecutivo

- La simulación está correctamente conectada de extremo a extremo:
  `world_factory.generate_world()` → `runner.run_simulation()` →
  `SimulationRunner.run()` → `SimulationResult`.
- Se encontró y corrigió **un bug real de escalabilidad** en el generador de
  reservas (`booking_factory._select_flight`), que provocaba un
  `FlightFullError` sin atrapar cuando un vuelo agotaba su inventario de
  asientos (más abajo).
- La suite pasa a **86 tests** (58 originales + 28 nuevos que añadimos). Antes
  de este trabajo, la lógica central de reservas, puertas, capacidad y el
  pipeline completo a escala **no estaba testeada**, y había un archivo de
  tests "muerto" de 391 líneas que pytest ni siquiera ejecutaba.

---

## 2. Arquitectura y conexión

El flujo es:

```
generate_world(n_airports, n_flights, n_passengers)
   │  genera aeropuertos, rutas, vuelos, pasajeros y reservas
   ▼
runner.run_simulation(world)            # punto de entrada público
   ▼
SimulationRunner.run(bookings)
   1. carga layout de aeropuertos
   2. PassengerJourney.prepare(...)     # llegada → check-in → seguridad
   3. ordena por security_arrival
   4. procesa colas de seguridad compartidas por aeropuerto
   5. PassengerJourney.continue_after_security(...)  # seguridad → puerta → veredicto
   6. eventos de vuelo + timeline global ordenada
   ▼
SimulationResult(world, events, initial_world)
```

Puntos de conexión clave:

- `Booking` es el objeto de unión: mantiene `passenger`, `flight`, `seat` y las
  banderas de estado (`checked_in`, `boarded`). Viaja intacto por todo el pipeline.
- `SecurityQueue` es un recurso compartido por aeropuerto; se coordina en orden
  cronológico.
- `SimulationResult.initial_world` (deepcopy) habilita `SimulationReplay`.
- `result.to_event_dicts()` / `save_events()` / `load_event_dicts()` exportan a
  JSON para la base de datos y los analizadores.

---

## 3. Bug corregido durante la auditoría

### 3.1 `FlightFullError` sin atrapar al escalar las reservas

**Síntoma.** `generate_world(..., n_passengers)` podía lanzar
`FlightFullError: No seats available on <flight>` de forma no controlada cuando
el número de pasajeros era grande en relación a los vuelos (por ejemplo, 500
pasajeros con 2 vuelos).

**Causa raíz.** Existe una inconsistencia en el modelo de `Flight`:

- `Flight.capacity` es `200`.
- El inventario real de asientos (`total_seats`) es de **180** asientos
  (`{TravelClass.ECONOMY: 180}`).

`_select_flight` filtraba los vuelos usando solo `len(flight.bookings) <
flight.capacity` (es decir, permitía hasta 200 reservas), pero `assign_seat`
agota los asientos con 180. Cuando un vuelo llegaba a 180 asientos y seguía
siendo elegible, `generate_booking` llamaba a `assign_seat` y esta lanzaba
`FlightFullError`, que `generate_bookings` no capturaba → **crash de toda la
simulación**.

**Corrección (mínima).** En `src/simulation/generators/booking_factory.py`,
`_select_flight` ahora además exige que el vuelo tenga asientos disponibles:

```python
if len(flight.bookings) < flight.capacity
and flight._available
and (
    passenger.preferred_airline is None
    or flight.flight_number.startswith(passenger.preferred_airline)
)
```

A partir de aquí, un vuelo deja de ser candidato cuando agota sus asientos, y
los pasajeros restantes se reparten a otros vuelos o quedan sin reserva (se
maneja con el `continue` ya existente). La simulación ya no se rompe a escala.

**Nota de diseño pendiente.** La disparidad `capacity == 200` vs
`asientos == 180` sigue existiendo. Es solo un problema de consistencia
conceptual; el comportamiento correcto (nunca exceder el inventario) está
garantizado por la corrección. Si se quiere alinear, se puede igualar
`Flight.capacity` al total de asientos generados.

> **Actualización posterior:** esta disparidad quedó **resuelta** al añadir el
> inventario multi-clase: el `total_seats` por defecto ahora es
> `{FIRST:4, BUSINESS:16, PREMIUM_ECONOMY:30, ECONOMY:150}` = 200 = `capacity`
> (ver `flight.py`). La inconsistencia histórica ya no aplica a los vuelos nuevos.

---

## 4. Estado de los tests

### 4.1 Resumen numérico

| Concepto | Antes | Ahora |
|---|---|---|
| Tests que pasa pytest | 58 | 96 |
| Archivos de test reales | 9 (uno muerto) | 11 (todos activos) |
| Test "muerto" (solo `print`, sin `assert`) | `test_passenger_journey_boarding.py` (391 líneas) | convertido en 7 tests reales |
| Tests de llegada + escenario hub | 0 | 10 (`test_passenger_arrival.py` 6 + `test_hub_scenario.py` 4) |

> Nota: los `_ZONE_BY_EVENT`, `_STATE_BY_EVENT`, `_build_world` y el resto que
> aparecen en `git diff` contra HEAD son trabajo previo no commiteado, no de esta
> iteración. Esta iteración solo añadió la llegada (`EXIT_AIRCRAFT`/
> `EXIT_AIRPORT`) y el escenario hub.

### 4.2 Qué estaba bien cubierto

- **SecurityQueue**: planificación de servidores, orden de servicio, límite de
  puntos de servicio, marcado de congestión por espera.
- **Stress / velocidad de marcha**: relaciones monótonas, determinismo.
- **Round-trip runner/replay**: cronología, conteo boarded+missed, estados finales.
- **Export**: presencia de claves (`zone`, `state`, `stress`, métricas).

### 4.3 Qué añadimos en esta iteración

- **`test_passenger_journey_boarding.py`** (convertido): cada pasajero completa
  seguridad, llega a la puerta, tiene veredicto boarded/missed, los que embarcan
  llegan antes del cierre y los que pierden el vuelo después, y la cronología
  seguridad→puerta. Cubre por fin la lógica de missed-flight/deadline.
- **`test_booking_factory.py`** (nuevo): las reservas respetan la capacidad,
  cada reserva está enlazada a pasajero y vuelo, sumar por encima de la
  capacidad lanza `FlightFullError`, el filtro `preferred_airline`, y la
  asignación de asiento marca la ocupación.
- **`test_gate_allocation.py`** (nuevo): asignación de puerta única sin
  solapamiento, `RuntimeError` cuando la única puerta está ocupada, y
  `find_available_gate` con puertas libres/ocupadas.
- **`test_security_queue.py`**: dos tests nuevos que cubren la rama de
  congestión por `capacity` (`occupancy >= capacity`), que antes no se
  ejercitaba.
- **`test_runner_replay_roundtrip.py`**: tests del punto de entrada público
  `run_simulation` (no se usaba antes) y un test a escala realista
  (`generate_world(12, 20, 1500)`) que valida que el bug de capacidad no
  reaparezca y que el conteo boarded+missed coincide con las reservas.
- **`test_event_export_enrichment.py`**: round-trip `save_events()` →
  `load_event_dicts()` y formato de tiempo / valor de evento del export.

### 4.4 Lo que sigue sin cubrir (recomendado para la siguiente iteración)

Cubierto en una iteración posterior (ver §8.6):

- ✅ **`airport_layout_loader`**: errores con código inexistente
  (`FileNotFoundError`), JSON malformado (`JSONDecodeError`), `locations` faltante
  (`KeyError`), `load_airport_layouts()`, `get_location`/`get_gate_location`
  (`test_airport_layout_loader.py`, 8 tests).
- ✅ **`result.py`**: golden test del esquema exacto del JSON (mapas
  `_ZONE_BY_EVENT` / `_STATE_BY_EVENT`, alias de métricas, esquema de eventos de
  pasajero vs aeronave) (`test_result_golden_and_world.py`).
- ✅ **`SimulationRunner._build_world`**: recomposición de aeropuertos/flights/
  passengers únicos a partir de las reservas, y `None` con reservas vacías.
- ✅ **Rendimiento**: test de techo que corre un día grande
  (12 aeropuertos / 30 vuelos / 2500 px) dentro de un presupuesto de 20 s y
  valida consistencia de veredictos. Actualmente completa en ~2-3 s.

---

## 5. Problemas de arquitectura detectados (sin cambiar, para no arriesgar)

A petición expresa de mínimo cambio, estos no se tocaron; se dejan documentados.

1. **Estado mutable a nivel de módulo** en `generators/airport_factory.py`:
   - `_airport_instances` persiste entre llamadas a `generate_world` (los
     aeropuertos se comparten entre simulaciones).
   - `generate_synthetic_airports` muta permanentemente el diccionario `AIRPORTS`.
   - Impacto: reproducción no totalmente limpia entre ejecuciones. En la
     práctica no rompe simulaciones independientes (se validó).
2. **Duplicación de lógica de creación de vuelos**: `world_factory._create_flight`
   reimplementa `flight_factory.create_random_flight` e importa el símbolo
   privado `_allocate_gate`. Riesgo de divergencia futura.
3. **`SimulationEngine` casi huérfano**: solo lo usa `replay.py` (vía
   `dispatch()`), y `event_factory.generate_events()` es código muerto que
   duplica `run_simulation`. Confuso para nuevos integrantes.
4. **Ciclos de objeto**: `Passenger.current_booking ↔ Booking.passenger` y
   `Booking.flight ↔ Flight.bookings` hacen que el estado tenga que ser
   `deepcopy`-eado para el replay.

---

## 6. Recomendaciones para la simulación grande

- **Robustez a escala**: ya validado en este trabajo (hasta 3000 pasajeros /
  20-50 vuelos / 12 aeropuertos) — sin crashes, sin sobrepasar capacidad, y el
  conteo de veredictos es consistente.
- **Equilibrio vuelos↔pasajeros**: cada vuelo tiene 180 asientos efectivos y
  salida en franjas de 05:00–22:00. Para "día completo" con muchos vuelos, ten
  presente que el límite de vuelos por aeropuerto está dado por sus puertas
  (ej. `SCL`=1, `BOG`=2). El generador ya reintenta y lanza `RuntimeError` si no
  hay puerta libre (se validó que con 50 vuelos funciona).
- **Alinea `Flight.capacity` con el inventario de asientos** (200 vs 180) para
  que `load_factor` y las reservas sean coherentes conceptualmente.
- **Pendientes de tests**: `airport_layout_loader`, esquema exacto del export y
  un test de rendimiento; son el siguiente paso natural antes de una simulación
  mucho más grande.

---

## 7. Comando de verificación

```bash
python -m pytest -q
```

Suite completa actual (incluidas las iteraciones posteriores): **146 passed**
(143 + 3 de `home_airport`/origen en `test_booking_factory.py`, docs/14).

---

## 8. Iteración posterior: llegada completa + escenario hub de saturación

### 8.1 Alcance (Frente A → B, cambios mínimos/quirúrgicos)

El pipeline solo llegaba hasta `PASSENGER_BOARDED`/`MISSED_FLIGHT`. En esta
iteración se cierra el ciclo del pasajero hasta que "sale a la calle" en el
aeropuerto de destino, y se añade un escenario hub para analizar saturación.

### 8.2 Frente A: ciclo de llegada (`EXIT_AIRCRAFT` → `EXIT_AIRPORT`)

- **`PassengerJourney.after_boarding()`** (nuevo en
  `src/simulation/generators/passenger_journey.py`): genera `EXIT_AIRCRAFT`
  (desembarque por fila: `landed_time + 15s + fila×3s`, fila derivada del
  número de asiento) y `EXIT_AIRPORT` (caminata `baggage_claim → exit` vía
  `PassengerMovement.move` a la velocidad del pasajero).
- **`SimulationRunner.run()`** (paso 5b): para cada pasajero `PASSENGER_BOARDED`
  (por `passenger_id`), carga el layout del `destination_airport` y genera la
  llegada usando `flight.get_milestone(FlightMilestone.LANDED)`.
- **`result.py`**: `_STATE_BY_EVENT` + `EXIT_AIRCRAFT:"At Destination Airport"`
  y `EXIT_AIRPORT:"Exited Airport"` para el export.
- **Tests**: `test_passenger_arrival.py` (6) — boarded→llegada, llegada
  después de AIRCRAFT_LANDED, cronología `EXIT_AIRCRAFT ≤ EXIT_AIRPORT`,
  replay termina en `Exited Airport`, `after_boarding` unitario, y export de
  zonas/estados.

### 8.3 Frente B: escenario hub (`src/scenarios/hub_day_simulation.py`)

- Hub **JFK** (8 puertas) → LAX/LHR/CDG/MAD/GRU, **5 vuelos de 200 asientos**
  (inventario igualado a la capacidad), **1000 pasajeros** (1000 plazas → sin
  `FlightFullError`).
- `build_hub_world(staggered=...)`: **escalonado** (salidas 07/09/11/13/15h) o
  **saturado** (todos a 07:00).
- `saturation_report()`: cola de seguridad (espera media/máx, % con espera,
  % congestión), veredicto de vuelo (embarcados / perdidos / %) y ciclo
  completo (salió a la calle, tiempo en el aeropuerto).
- CLI: `python -m src.scenarios.hub_day_simulation [--saturar] [--margen N]`.

### 8.4 Hallazgos de saturación (respuesta a la pregunta del usuario)

| Escenario | Espera media seguridad | % congestión | Perdieron vuelo |
|---|---|---|---|
| Escalonado (defecto) | ~2 s | 13% | **0 / 1000** |
| Saturado (5 aviones a 07:00) | ~748 s (12.5 min) | 89% | **0 / 1000** |
| Saturado + `--margen 30` | ~5244 s (87 min) | 99.6% | **989 / 1000** |

**Conclusión:** el modelo sí reproduce la pérdida de vuelos por saturación,
pero depende críticamente del **margen de llegada**. El generador por defecto
asigna márgenes amplios (≥45 min, típicamente 90–180 min), y el cierre de
embarque (15 min antes de la salida) queda holgado: incluso con colas de
seguridad de media hora nadie pierde el vuelo. Solo cuando el margen es corto
(`--margen 30`) y todos los aviones salen a la vez, la cola explota y el
99% pierde el vuelo — quedándose en el aeropuerto de origen (correcto: ningún
`EXIT_AIRPORT` para los que no embarcaron).

### 8.5 Tests de escenario hub (`test_hub_scenario.py`, 4)

- 5 vuelos saliendo del mismo hub.
- La capacidad total cubre la demanda (`flights_capacity ≥ n_passengers`).
- Run escalonado: todos los embarcados salen a la calle (`exited == boarded`).
- Replay al final: todos los pasajeros en `Exited Airport`.

### 8.6 Cierre de brechas de tests (docs/11 §4.4)

Se añadieron 16 tests nuevos para cubrir las cuatro brechas de §4.4:

- **`test_airport_layout_loader.py`** (8): layout válido (parsing de posiciones),
  código inexistente (`FileNotFoundError`), JSON malformado
  (`JSONDecodeError`), `locations` faltante (`KeyError`), `load_airport_layouts()`
  (carga todo `*.json`), búsqueda por nombre en mayúsculas, y errores de
  `get_location` / `get_gate_location`. Usa `monkeypatch` de `DATA_DIR` con
  fixtures controladas en `tmp_path`.
- **`test_result_golden_and_world.py`** (8):
  - Golden del esquema de export: keys exactas y zona/estado de eventos de
    pasajero (llegada, check-in, puerta, seguridad) y de aeronave
    (`AIRCRAFT_TAKE_OFF` no lleva `state`).
  - Alias de métricas: `wait_seconds`, `service_time`, `queue_length`,
    `security_occupancy`, `security_congested` en `SECURITY_STARTED`, y
    verificación de que cada alias en `_METRIC_ALIASES` corresponde a un clave
    real del payload.
  - `_build_world`: recomposición de aeropuertos/pasajeros/vuelos únicos desde
    las reservas, y `None` con reservas vacías.
  - Rendimiento/techo: día grande (12 aeropuertos / 30 vuelos / 2500 px) dentro
    de un presupuesto de 20 s (en la práctica ~2-3 s) y consistencia de
    veredictos (boarded+missed == reservas).

**Suite actual: 146 passed** (134 del cierre de brechas + llegada/hub + métricas web
y `home_airport`/origen de docs/14).

