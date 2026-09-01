# 14. Más datos: pasajeros que nacen en cualquier aeropuerto

> Informe de decisión (previo a implementar) + registro de lo decidido.

## 1. Objetivo

Construir una simulación con más datos y más rica:
- **Más vuelos y más pasajeros** (aprox. 3000 pasajeros / ~60 vuelos).
- Que los pasajeros **"nazcan" en cualquier aeropuerto** (su aeropuerto base), no solo
  en un único hub.

## 2. Estado actual (cómo nace un pasajero hoy)

- `Passenger` tiene `nationality` (país, usado para nombres/documentos) pero **no una
  aeropuerto base/origen** (`src/world/passenger.py`).
- `generate_bookings` asigna cada pasajero a un vuelo **solo por aerolínea preferida o
  aleatoriamente** (`booking_factory._select_flight`), sin considerar de dónde es.
- El viaje empieza en `booking.flight.origin_airport` (`prepare()` camina
  entrance → check-in del origen del vuelo). **El pasajero nace en el origen del vuelo
  que le toque.**
- Escenario actual de `web/dist` = **hub**: 5 vuelos todos desde JFK → todos nacen en
  JFK (`scenarios/hub_day_simulation.build_hub_world`).
- Ya existe `--full-day` (12 aeropuertos, 56 vuelos) que reparte orígenes por vuelo,
  pero es dirigido por vuelo, no por la casa del pasajero, y no correlaciona con la
  nacionalidad.

## 3. Hallazgo clave: desalineación nacionalidad ↔ aeropuerto

Las 11 nacionalidades de `config.json` incluyen China, Alemania, India y Japón, pero
los 12 aeropuertos disponibles están en Argentina (EZE), EE.UU. (MIA/JFK/LAX), España
(MAD/BCN), Francia (CDG), Reino Unido (LHR), Brasil (GRU), México (MEX), Colombia
(BOG) y Chile (SCL).

- **Países sin aeropuerto base**: China, Alemania, India, Japón.
- **Aeropuertos sin nacionalidad correspondiente**: EZE, SCL.

"Nacer en cualquier aeropuerto" exige alinear esto: mapear cada nacionalidad a un
aeropuerto base existente (o agregar aeropuertos para esos países).

## 4. Estrategia elegida: **B — `home_airport` real**

1. Agregar un campo `home_airport: str | None` a `Passenger`, coherente con la
   `nationality` del pasajero (mapeo país → aeropuerto base).
2. En `booking_factory`, enrutar la demanda por origen: `_select_flight` filtra por
   `flight.origin_airport == passenger.home_airport` (con overflow a otros orígenes si
   no hay ruta/cupo desde la base).
3. Así cada pasajero "nace" en su aeropuerto base real y la correlación
   nacionalidad → origen es realista.

### Decisión de escala

**~3000 pasajeros / ~60 vuelos** (12 aeropuertos, múltiples orígenes). Estimado:
~30.000 eventos y snapshots de ~8 MB (ver B3 en `docs/13`).

## 5. Cambios de diseño

- **Modelo**: `Passenger.home_airport` (nullable, IATA string).
- **Mapeo** nacionalidad → aeropuerto base (cada país → su hub natural; países sin
  aeropuerto propio se mapean a un hub regional vecino).

### Mapeo propuesto (país → base)

| Nacionalidad | Aeropuerto base |
|---|---|
| United States | JFK (hub; MIA/LAX como escalas) |
| United Kingdom | LHR |
| Spain | MAD |
| France | CDG |
| Brazil | GRU |
| Mexico | MEX |
| Colombia | BOG |
| Argentina | EZE |
| Chile | SCL |
| China | (sin base propia) → PEK/CDG/LHR regional |
| Germany | (sin base propia) → CDG/LHR regional |
| India | (sin base propia) → LHR regional |

Nota: como `ROUTES`/`AIRPORTS_DATA` tienen 12 aeropuertos, para los países sin base
propia se mapea a un aeropuerto existente. Alternativa futura: agregar aeropuertos
(PEK, FRA, DEL) y rutas.

- **Demanda por origen**: `_select_flight` prioriza vuelos desde `home_airport`;
  si no hay, cae a cualquier vuelo disponible **solo si la base no tiene rutas** (para
  no dejar demanda huérfana). A escala debe haber vuelos desde cada base.
- **Generación**: un nuevo build/CLI (o ampliar `generate_world`) que cree ~60 vuelos
  sobre rutas reales + sintéticas desde cada aeropuerto, y ~3000 pasajeros con
  `home_airport` asignado, luego bookings por origen.

## 6. Riesgos / costos

- **Capacidad**: demanda total ≤ plazas globales (60 vuelos × 200 = 12000 plazas ≫
  3000 demanda). Sin cuello.
- **Rutas por base**: cada base necesita al menos un vuelo saliente; si no, hay que
  garantizarlo generando rutas desde todos los orígenes.
- **Rendimiento/build**: ~30k eventos, snapshots ~8 MB; mirror de B3 en `docs/13`.
- **Tests**: preservar los tests/scenarios del hub existentes (`build_hub_world`,
  web tests) — el cambio debe ser aditivo.

## 7. Criterios de aceptación

- Todo pasajero tiene `home_airport` consistente con su `nationality`.
- Los bookings respetan (en su mayoría) `flight.origin == home_airport`; queda registro
  de overflow.
- Un build de ~3000 px / ~60 vuelos cubre varios aeropuertos de origen (no solo uno).
- La suite completa (143 tests) sigue en verde tras el cambio aditivo.
- `web/dist` regenerado muestra pasajeros en varios aeropuertos de origen.

## 8. Estado

- [x] Informe elaborado y decisiones tomadas (estrategia B, ~3000/60, este doc).
- [x] Implementado:
  - `Passenger.home_airport` (nullable, IATA).
  - Mapeo nacionalidad → aeropuerto base en `passenger_factory.HOME_AIRPORT_BY_NATIONALITY`
    (cubre US/UK/ES/FR/BR/MX/CO + AR/CH; China/Alemania/India/Japón → hub regional).
  - Se agregaron **Argentina** y **Chile** a `config.json` para que EZE y SCL tengan
    población base (pasa de 11 a 13 nacionalidades).
  - Routing por origen en `booking_factory._select_flight` (prioriza vuelos desde
    `home_airport`; si no hay, cae a cualquier vuelo para no dejar demanda huérfana).
  - `build_snapshots --full-day` ahora usa 60 vuelos; `build_meta` deriva el título
    ("red multi-aeropuerto" vs "hub").
  - Tests nuevos en `test_booking_factory.py` (home_airport, cobertura multi-origen,
    preferencia por origen). Suite completa **146 passed**.
- [x] `web/dist` regenerado con `--full-day --n-passengers 3000 --seed 20260713`
  (60 vuelos, 30180 eventos, 379 snapshots, 12 aeropuertos). A mitad de día 10
  aeropuertos operan en simultáneo. Snapshots ~19.6 MB (gzip). Assets sirven 200.
