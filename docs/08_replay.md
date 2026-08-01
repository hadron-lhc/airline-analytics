# SimulationReplay

El replay es un **reproductor** de la simulación. Permite recorrer una línea de
tiempo y, en cada instante, ver el estado del mundo tal como quedó en ese
momento. Es el complemento natural de `SimulationAnalyzer`: el replay te da el
mundo en un instante, el analyzer lo analiza.

## Idea

```
SimulationWorld
        │
        ▼
generate_events()
        │
        ▼
SimulationEngine
        │
        ▼
SimulationResult
       ├───────────────┐
       │               │
       ▼               ▼
SimulationAnalyzer   SimulationReplay
                           │
                           ▼
                     current_world
                           │
                           ▼
                  futura animación
```

El engine muta el mundo **en vivo** y los handlers son deterministas (no usan
azar al procesar). Por eso el replay puede reconstruir cualquier estado
intermedio simplemente re-ejecutando los eventos sobre una copia del mundo
inicial.

## Requisito

`SimulationResult` debe conocer el estado inicial del mundo:

```python
# runner.run_simulation() ya lo captura automáticamente:
result = run_simulation(world)

# o manualmente, antes de engine.run():
initial_world = deepcopy(world)
engine.run()
result = SimulationResult(world=world, events=..., initial_world=initial_world)
```

Si el result no tiene `initial_world`, `SimulationReplay` lanza un `ValueError`.

## API

```python
from src.simulation.replay import SimulationReplay

replay = SimulationReplay(result)
```

### Navegación (estilo video player, devuelven `None`)

| Método | Descripción |
|---|---|
| `reset()` | Vuelve al inicio (mundo inicial). |
| `has_next() -> bool` | `True` mientras queden eventos por reproducir. |
| `step()` | Avanza un evento; deja el reloj en la hora de ese evento. |
| `seek(index: int)` | Salta al frame `index`; deja el reloj en la hora del evento de ese índice (`index == 0` → inicio). Hacia atrás re-ejecuta desde el inicio. |
| `at(time: datetime)` | Procesa todos los eventos con tiempo `<= time` (bisect_right) y fija el reloj exactamente en `time`. |

### Estado (properties)

| Propiedad | Descripción |
|---|---|
| `current_index -> int` | Cantidad de eventos procesados (= índice del próximo a reproducir). |
| `current_world -> SimulationWorld` | El mundo tal como quedó en el instante actual. |
| `current_event -> SimulationEvent \| None` | El último evento reproducido (`None` al inicio). |
| `current_events -> list[SimulationEvent]` | Los eventos del estado actual (`events[:index]`). |
| `current_result -> SimulationResult` | Envuelve `current_world` + `current_events` listo para el analyzer. |
| `current_time -> datetime` | El reloj del replay en el instante actual. |
| `frame_count -> int` | Cantidad total de eventos en la línea de tiempo. |
| `start_time / end_time -> datetime` | Límites de la línea de tiempo. |
| `timeline -> list[ReplayFrame]` | La línea de tiempo completa (cacheada). |
| `progress -> float` | Progreso de **eventos**: `current_index / frame_count` (0.0 a 1.0). |
| `time_progress -> float` | Progreso de **tiempo**: `(current_time - start) / (end - start)`. Puede superar 1.0 si `at()` pide una hora posterior al último evento. |

### Consultas de estado

El replay **solo navega** y responde "¿cómo está el mundo ahora?". Las métricas y
reglas de negocio viven en `SimulationAnalyzer`.

| Método | Descripción |
|---|---|
| `world_statistics() -> dict` | Estado crudo del mundo: `time`, `passengers_by_state`, `flights_by_status`. No imprime. |
| `summary() -> dict` | Resumen estructurado (datos puros): `current_time`, `current_event` (enum crudo) y `event_time`, `next_event` (enum crudo) y `next_event_time`, `idle` (`current_time - event_time`), `processed_events`, `total_events`, `event_progress`, `time_progress`, `passengers_by_state`. |
| `print_summary(summary: dict \| None = None) -> None` | Solo formatea y muestra un resumen (`summary()` si no se pasa). Presentación; los datos nunca se transforman acá. |

Progreso de **eventos** y progreso de **tiempo** son distintos: puede haber un
80% del tiempo transcurrido con solo un 35% de los eventos procesados (largos
períodos sin actividad). `print_summary()` los muestra por separado.

Filosofía: **los datos permanecen puros; la presentación los embellece**. La GUI
puede hacer `stats = replay.summary()` y actualizar su ventana sin parsear texto.

`ReplayFrame` es un dataclass inmutable con `index`, `time`, `event_type`,
`entity_kind` y `entity_id` (UUID del pasajero o `flight_number`).

## Uso

```python
from src.simulation.replay import SimulationReplay
from src.analysis.simulation_analyzer import SimulationAnalyzer

replay = SimulationReplay(result)

# 1. Recorrer toda la línea
while replay.has_next():
    replay.step()
    world = replay.current_world

# 2. Saltar a un frame y analizar ese instante
replay.seek(replay.frame_count // 2)
print(replay.current_event)          # Passenger_Boarded @ 09:14
print(f"Progreso: {replay.progress:.0%}")

analyzer = SimulationAnalyzer(replay.current_result)
analyzer.total_revenue()             # revenue acumulado hasta ese instante

# 3. Pararse en un momento del día
replay.at(datetime(2026, 7, 13, 10, 0))
world = replay.current_world         # estado del mundo a las 10:00

# 4. La línea de tiempo para animaciones
for frame in replay.timeline:
    print(frame.time, frame.event_type.value)

# 5. Renderizar un aeropuerto en el instante actual (presentación aparte)
from src.render.console_renderer import ConsoleRenderer

renderer = ConsoleRenderer()
print(renderer.render_airport(replay.current_world, "EZE", replay.current_time))
```

`ConsoleRenderer` es la capa de presentación: recibe un `SimulationWorld`
(p.ej. `replay.current_world`) y devuelve texto. No imprime, no analiza;
solo embellece los datos puros.

## Demo

```bash
python -m src.scenarios.replay_demo
```

## Notas

- **Estado vivo**: `current_world` es el mismo objeto que se muta en cada
  `step()`. Si necesitás conservar un instante exacto, copialo con
  `deepcopy(replay.current_world)` o usá los frames de `timeline`.
- `result.events` siempre se conserva completo; `current_events` es solo una
  vista del segmento ya reproducido.
- Los eventos del replay se re-vinculan a las copias del mundo de trabajo para
  que los handlers muten el mundo del replay y no los objetos originales.
