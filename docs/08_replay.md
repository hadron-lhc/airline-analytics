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
| `step()` | Avanza un evento; actualiza el estado interno. |
| `seek(index: int)` | Salta al frame `index`. Hacia atrás re-ejecuta desde el inicio. |
| `at(time: datetime)` | Se posiciona en el último evento `<= time`. |

### Estado (properties)

| Propiedad | Descripción |
|---|---|
| `current_index -> int` | Índice del siguiente evento a reproducir. |
| `current_world -> SimulationWorld` | El mundo tal como quedó en el instante actual. |
| `current_event -> SimulationEvent \| None` | El último evento reproducido (`None` al inicio). |
| `current_events -> list[SimulationEvent]` | Los eventos del estado actual (`events[:index]`). |
| `current_result -> SimulationResult` | Envuelve `current_world` + `current_events` listo para el analyzer. |
| `frame_count -> int` | Cantidad total de eventos en la línea de tiempo. |
| `start_time / end_time -> datetime` | Límites de la línea de tiempo. |
| `timeline -> list[ReplayFrame]` | La línea de tiempo completa (cacheada). |
| `progress -> float` | `current_index / frame_count` (0.0 a 1.0). |

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
```

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
