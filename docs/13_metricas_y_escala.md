# 13. Hacia dónde conviene ir: métricas más interesantes y una simulación más grande

Este informe parte del estado actual real (relevado con referencias `archivo:línea`)
y propone qué conviene hacer ahora para que **los datos cuenten historias** en vez de
ser "correctos pero planos".

---

## 1. Diagnóstico: qué medimos hoy y por qué es poco interesante

### Qué se mide hoy

- **Operativo**: embarcados, perdieron vuelo, `avg_origin_min` (tiempo origen→embarque)
  (`web/build_snapshots.py:272-368`).
- **Seguridad**: espera media/máx, % congestión, cola instantánea por aeropuerto
  (mismo archivo).
- **SQL**: 11 consultas de `sql/timeline_analysis.sql` (eventos por tipo, espera por
  seguridad, estrés por zona, márgenes, velocidad por tramo, ventanas de embarque,
  duración de viaje por vuelo, actividad horaria, ocupación de seguridad).

Es un buen piso. Pero hay dos límites estructurales:

1. **Todo está precalculado por pasajero** y casi no hay interacción que dependa del
   mundo: check-in dura 240 s para todos (`passenger_journey.py:165`), la decisión de
   embarcar/perder el vuelo es `gate_arrival <= departure - 15min`
   (`passenger_journey.py:397-430`). El único recurso real hoy es la cola de seguridad.
   → Las métricas se parecen entre pasajeros; no hay "historias".
2. **El modelo era chico y parejo**: 12 aeropuertos, 5 vuelos, 500 px por defecto
   (`world_factory.py:96-99`); el hub de JFK usa 5 vuelos y 1000 px
   (`hub_day_simulation.py:29,35`). Los vuelos salen en horas aleatorias parejas
   (`world_factory.py:49-50`) y no hay bancos de vuelos (picos).
   → Poco poder estadístico y curvas de congestión sin drama.
   - ⚠️ **Parcialmente rescuelta**: hoy `web/dist` es una red multi-aeropuerto de
     **3000 px / 60 vuelos / 12 aeropuertos** con pasajeros que "nacen" en su
     aeropuerto base (`home_airport`, docs/14). Sigue pendiente la **densidad**
     (bancos de vuelos y staffing por turno, §B2) y llegar a ~10k px (§B1).

**Dato clave para dimensionar**: el mismo `snapshots.json` de hoy (~2.5 MB con ~5k
eventos) crece a ~30-80 MB al escalar a 10k pasajeros; hay que blindar el build y la
web **antes** de correrlo (ver §4.3).

---

## 2. Polo A — Métricas más interesantes (enriquecer los datos)

Ordenamos por (impacto en el análisis) ÷ (costo con la arquitectura actual:

### A1. Check-in real con cola (costo bajo, impacto alto)
✅ **Implementado.** La decisión online/presencial ya varía la duración, y ahora existe
una **cola de mostrador compartida** por aeropuerto (`CheckInQueue`, una clase que
extiende `SecurityQueue` con `service_points=3`, `checkin_queue.py`). El pasajero
pasa por `ARRIVE_CHECK_IN` → `CHECK_IN_COMPLETED` con `queue_wait`,
`checkin_occupancy`, `checkin_congested` y `time_pressure`/`wait_stress` cuando
espera. El check-in online ahorra cola; el presencial se paga en espera.
- Eventos `ARRIVE_CHECK_IN` / `CHECK_IN_COMPLETED` con cola de mostrador por aeropuerto
  (`SimulationRunner._get_checkin_queue()`, pasos 3 → 5 en `run()`).
- `passenger_journey.py`: `prepare()` llega solo a check-in; `continue_after_checkin()`
  emite el completion + `ARRIVE_SECURITY` y arranca el estrés por espera.

Habilita: tiempo ahorrado por _online_, correlación modo↔margen de llegada, y hace que
la zona "Check In" de la web (`web/static/app.js`) muestre gente real.

### A2. Equipaje de verdad (costo bajo, impacto alto)
✅ `checked_baggage` ya se deriva de `baggage_probability` (1 pieza si
`random < baggage_probability`, `booking_factory.py:132-133`). Pendiente: la espera
en `baggage_claim` proporcional a la cola del vuelo y que el carry-on afecte la
velocidad de embarque. Propuesta:
- `checked_baggage` derivado de `travel_purpose`/clase; espera en `baggage_claim`
  proporcional a la cola del vuelo; carry-on que afecta velocidad de embarque.

Habilita: equipaje por motivo de viaje, picos del claim, tiempo extra de estadía en
destino, y la métrica ancillar `bags_per_passenger`.

### A3. Embarque por grupos (costo medio)
✅ `boarding_group` ya se asigna por clase/lealtad (PRIORITY para
First/Business/Platinum/Gold, resto GROUP_1..5, `booking_factory.py`).
✅ **Secuencia por grupo implementada** (`passenger_journey.py` `_boarding_window`):
cada grupo ocupa una fracción del tramo `[BOARDING_START, doors_close]`, y el
pasajero embarca en `max(gate_arrival, group_window_start)`, de modo que la
secuencia respeta la prioridad (PRIORITY primero, GROUP_5 último). El evento
`PASSENGER_BOARDED`/`MISSED_FLIGHT` lleva `boarding_group`, `group_window_start`
y `group_window_end`; `to_event_dicts()` exporta `boarding_group`.
- Pendiente (opcional): que el embarque **dure** según ocupación/prioridad y
  reaprovechar `FlightMilestone.DOORS_CLOSED` (hoy −15 min hardcodeado).

Habilita: duración de embarque por vuelo, puntualidad de salida, y hace que `MISSED_FLIGHT`
tenga gradación (¿llegó tarde por cola o por grupo?).

### A4. Evento DOORS_CLOSE + puntualidad (costo bajo)
`DOORS_CLOSE` no existe como evento; el criterio de embarque está hardcodeado −15 min.
Propuesta:
- Crear el evento y emitirlo; medir *wheels-off vs scheduled*, retardo de salida por
  puerta, y quienes llegan tras el cierre.

Habilita la métrica estrella **on-time performance** por vuelo/puerta/aeropuerto.

### A5. Cohorte por motivo de viaje (¡cierre de brecha!)
`travel_purpose` y `arrival_margin` ya se generan por propósito
(`passenger_factory.py`, `derived_behavior.py`). ✅ La ramificación a
otras decisiones ya existe: `travel_class` se deriva de propósito+lealtad,
`preferred_seat` de propósito, equipaje de `baggage_probability`, modo de
check-in de `online_checkin_probability`. Pendiente: la
sensibilidad de estrés por cohorte.

Habilita: **tablas de cohorte** Business vs Leisure vs Family vs Visiting en `sql/schema.sql`
y comparativas en la web (margen, espera, estrés, missed rate por corte).

### A6. Métricas de experiencia (SLA) (costo bajo, impacto visual alto)
El estrés ya viaja en cada evento (`stress`, `time_pressure`, `wait_stress`). Propuesta:
- KPI derivados: % pasajeros que llegan al embarque estresados, % que casi pierden el
  vuelo, % que exceden la espera objetivo en seguridad.
- Panel web de evaluación de servicio por aeropuerto (además de cola).

### A7. Métricas económicas (costo medio)
No hay ningún dato de dinero. Propuesta:
- Tarifa simple por ruta/clase y motivo + ingreso ancillar (equipaje, comercio ≥ A2).
- `load_factor` ya es calculable (`flight.passenger_count`/`capacity 200`).

Habilita: revenue/pax por vuelo y ruta, yield por motivo, carga vs masa, y el análisis
economic más "pegajoso" del proyecto. Sin afectar el motor espacial.

### A8. Comparación de escenarios con semillas (costo bajo)
Hoy cada corrida es un mundo. Propuesta:
- Fijar la semilla del RNG (`world_factory` ya es parametrizable) y correr N réplicas de
  escenarios (normal vs `--saturate` vs demora). Resumir con medio e intervalo (bootstrap).

Habilita: comparativas "¿cuánto cuesta el pico?" con significancia, no anécdotas.

### A9. Demoras, no-shows y conexiones (costo alto — requiere motor reactivo)
Los enums existen pero están muertos (`FlightStatus.CANCELLED`,
`BookingStatus.NO_SHOW` en `world_enums.py:47,84-85`); no hay evento asociado. Es lo más
interesante para análisis (árboles de propagación de demoras), pero **depende del motor
reactivo** de la §3. Se explica acá su valor pero se agenda al final.

---

## 3. Polo habilitador — Motor reactivo (el gran botón)

Hoy `SimulationRunner.run` **precalcula** todo y luego ordena el timeline
(`simulation_runner.py:60-182`); el `SimulationEngine` reactivo solo se usa en el replay
(`engine.py`, `replay.py:161`). Los handlers de pasajero/vuelo ya existen (cambian
estado al procesar cada evento).

**Propuesta**: que el engine sea quien **genere** (`add_event`) el siguiente evento según
el estado del mundo en cada dispatch (scheduling en cascada). Esto es la Fase 2 del
`docs/09_simulation_roadmap.md` y es **requisito** para demoras, cancelaciones,
conexiones y re-booking. Sin esto, A9 es imposible y el resto queda "precalculado bonito".

Orden sugerido: primero lo precalculado compatible (A1-A8), y con esas métricas ya
centradas, invertir el tiempo en el motor reactivo.

---

## 4. Polo B — Simulación más grande y densa (para mejor análisis)

### B1. Escala objetivo
- Hoy (default): 12 aeropuertos / 5 vuelos / 500 px; hub 5 vuelos / 1000 px.
- ✅ **Alcanzado (docs/14)**: red completa `--full-day` →
  `generate_world(12, 60, 3000)` desplegada en `web/dist` (3000 px, 60 vuelos,
  30180 eventos, 12 aeropuertos, 9+ aeropuertos de origen gracias a `home_airport`).
  Matemática de asientos: 60 vuelos × 200 asientos ≈ 12.000 ≥ 3000 de demanda.
- **Próximo objetivo**: llevar `--full-day` a ~10.000 px (mismo régimen, ver B3).
- Distribuir pasajeros por vuelo con factor de carga variable, no parejo.

### B2. Densidad: bancos de vuelos y turnos (lo que "revuelve" el agua)
- Hoy las salidas son parejas (hora aleatoria 5-22, `world_factory.py:49-50`).
- Propuesta: **ondas de vuelos** por la mañana (06-09) y tarde (17-20), como un hub real.
- Juntar con **staffing de seguridad variable por turno**: antes `capacity=20` y
  `service_points=4` eran constantes (`security_queue.py:53-54`) y nunca se rechazaba por
  capacidad. Hacer la capacidad dependiente de la hora → aparecen picos de cola reales,
  y `security_capacity` deja de estar `None` en los eventos (`passenger_journey.py:264-288`).
  - ✅ **Hecho**: el perfil por turno ya emite `security_capacity`/`occupancy` reales
    (`SecurityQueueResult.capacity`, `security_queue.py:22`); perfil actual en
    `simulation_runner.py:33` → `{"peak": (4, 18), "off": (3, 12), "night": (2, 6)}`
    con `base_service_time=130` (`queue_service_model.py:14`); la web y `hub_day_simulation`
    muestran la cola por hora (`in_queue` con forma de curva).

Esto convierte la métrica `in_queue` en una curva con forma (el santo grial visual).

### B3. Performance del build a 10k
- El builder ya es **una sola pasada**: `_MetricsTracker` alimenta eventos en orden y
  `replay.at()` avanza incrementalmente (`replay.py:175-189`; `seek` solo resetea si
  retrocede). Con ticks crecientes no hay O(n²). Verificado: no hay que rehacerlo.
- **Sí hay que blindar**: `snapshots.json` (~2.5 MB hoy) crece a ~30-80 MB estimado.
  Plan: (a) paso de snapshot **adaptativo** (1-2 min en picos, 10-15 de noche),
  (b) gzip de `meta.json`/`snapshots.json` en el CDN, (c) partir por horas y cargar el
  chunk contiguo en la web; (d) subir `MAX_POINTS_PER_ZONE` o muestrear inteligente.

### B4. Carga a SQL a escala
- Hoy el loader hace `INSERT` fila por fila desde un JSON **fijo**
  (`load_simulation.py:8-10,39-88`). A 10k px (~200-300k eventos) conviene:
  (a) `COPY`/`execute_values` en lotes, (b) export elegido como parámetro y no hardcode,
  (c) vistas materializadas de las 11 consultas de `timeline_analysis.sql`

### B5. Dterminismo para comparar
- ~~Hay `random` sin semilla global~~ → **Implementado**.
  `generate_world(..., seed=N)`, `build_hub_world(..., seed=N)` y los CLIs
  (`hub_day_simulation --seed`, `build_snapshots.py --seed`) siembran `random`,
  `numpy` y los `Faker` y resetean el estado global de aeropuertos, de modo que
  dos corridas con la misma semilla son idénticas (incluso en el mismo proceso).

---

## 5. Las métricas estrella (las que dan mejores visualizaciones)

| Métrica | Origen | Visualización posible en la web |
|---|---|---|
| Cola de seguridad con staffing por turno | B2 | curva en área con picos; heatmap aeropuerto×hora |
| On-time performance (DOORS_CLOSE) | A4 | strips de vuelos vs horario |
| % que llega estresado al embarque | A6 | panel SLA + correlación con espera |
| Care y carga por vuelo/motivo | A7 | barras duales, revenue por ruta |
| Cohortes por motivo | A5 | comparativa de distribuciones (margen, espera) |
| Demoras propagándose | A9 | árbol de demoras en el mapa aéreo |

### Métricas ya visibles en la pestaña "Métricas"
La pestaña "Métricas" ya pasa de 4 widgets a 8 paneles (acumula en una sola pasada,
`_MetricsTracker` en `web/build_snapshots.py`):
- **Cola de seguridad** y **Cola de check-in**: espera media + % congestión por
  aeropuerto (barra por momento) y pasajeros en cola por aeropuerto a lo largo del día
  (línea). La de check-in reutiliza `ARRIVE_CHECK_IN`/`CHECK_IN_COMPLETED` (A1).
- **Operativo** (doughnut): embarcados vs perdidos, completados, prom min en aeropuerto.
- **Experiencia / SLA**: estrés promedio al embarque, % estresados (>0.45) y % de esperas
  con presión de tiempo alta (`time_pressure`).
- **Puntualidad por vuelo**: embarcados vs perdidos por vuelo (`operational.flight`).
- **Cohortes por motivo**: missed-rate, espera media y estrés medio por Business /
  Leisure / Family / Visiting (desde `travel_purpose` de cada pasajero).

Estas son agregaciones de frontend/snapshot que reutilizan payloads ya emitidos por el
simulador; no requieren cambios del motor.

---

## 6. Orden de ejecución recomendado

1. **B1+B2+B4** — escala y densidad con las métricas actuales (riesgo bajo, sube ya el
   poder estadístico del análisis SQL y de la web).
   - ✅ **B1 (parcial, docs/14)**: red `--full-day` de 60 vuelos / 3000 px / 12
     aeropuertos con `home_airport` (pasajeros que "nacen" en su aeropuerto base) ya
     desplegada en `web/dist`. Queda densidad (B2) y llegar a ~10k px.
2. **A1, A3, A8 ✅, A2, A4** — check-in con cola, embarque por grupos y determinismo ya
   implementados; equipaje-real y DOORS_CLOSE quedan como próximas extensiones
   precalculadas, compatibles con la arquitectura actual.
3. **A5, A6, A7** — cohortes, SLA, economía, comparación de escenarios.
4. **A9 + motor reactivo** — el eslabón final, cuando las métricas ya tengan dónde
   clavar demoras/cancelaciones/conexiones.

Los pasos 1-3 no deberían romper el schema de `web/dist` actual; se extienden
`meta.json`/`snapshots.json` (añadir campos, no renombrar los existentes).

---

## 7. Riesgos y costos

- **Tamaño de artefactos web** (30-80 MB) → mitigado con §B3 (paso adaptativo + gzip + chunks).
- **Carga SQL lenta** a 10k px → §B4 (COPY/batches).
- **Determinismo**: sin semillas, A8 no es reproducible → sembrar `world_factory` y el builder.
- **Deuda previa**: `time_models.py` (lognormales legacy, descoordinado del camino vigente)
  debe **eliminarse o unificarse** para no duplicar modelos (mismo problema con el −15/−20
  min de DOORS_CLOSED).