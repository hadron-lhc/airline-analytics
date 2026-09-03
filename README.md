# Airline Day — simulador de un día de operación aérea

Simulador de *evento discreto* de un día de operación de una red de aeropuertos:
cada pasajero viaja de su origen a su destino atravesando check-in, seguridad,
puerta de embarque y vuelo. El proyecto genera las métricas de la jornada
(colas, puntualidad, load factor, estrés), un **informe operativo** y una
**vista web estática animada** con la evolución del día, todo reproducible
gracias a semillas fijas.

## Estructura

```
├── .env.example            # Plantilla de configuración (crear .env a partir de ella)
├── docs/                   # Diseño del sistema (mundo, motor, web, escala…)
├── sql/
│   ├── schema.sql          # Esquema de la tabla simulation_events (PostgreSQL)
│   └── timeline_analysis.sql  # Consultas de análisis de la timeline
├── src/
│   ├── analysis/           # Informe operativo (report_builder.py) + análisis SQL
│   ├── database/           # Capa SQL: carga de eventos a PostgreSQL
│   ├── data/               # Datos de referencia (países, aeropuertos…)
│   ├── enums/              # Enumerados del dominio
│   ├── scenarios/          # Escenarios: hub, full-day, export/refresh timeline
│   ├── simulation/         # Motor: world, runner, replay, generators, queues
│   └── world/              # Entidades del dominio
├── web/
│   ├── static/             # Plantilla de la web (index.html, app.js, style.css)
│   ├── tests/              # Tests del build web
│   └── build_snapshots.py  # Construcción del dist + bundle (línea de comando)
└── web/dist/               # Web estática servible (generada, no se commitea)
```

## Requisitos

- **Python 3.10+**
- **PostgreSQL** — solo para la capa de persistencia/análisis SQL (opcional si
  solo quieres la web).
- **Node.js** — solo opcional, para el chequeo de sintaxis del JS
  (`node --check`).

Instala las dependencias de Python:

```bash
pip install -r requirements.txt
```

> Para la web (build + `http.server`) no hace falta instalar nada más: todo lo
> que usa el build es stdlib.

## Ver la web (fast path)

```bash
python -m http.server 8080 --directory web/dist
```

Abrir `http://localhost:8080`. La web es **100% estática**: no hace falta
nada más. Nota: abrir `index.html` con doble clic no funciona (los datos se
cargan por `fetch`); siempre hay que servir el directorio.

### Cómo se maneja

- **Timeline** fijo arriba: ▶/⏸ (o `espacio`), flechas ← →, slider y
  velocidad 1×–50× *(1 min simulado = 1 s real a 1×)*. Los enlaces con
  `#tab:n` abren pestaña y fotograma (`#report:42`).
- **Métricas**: contadores globales, colas de seguridad/check-in (en el
  momento y a lo largo del día por aeropuerto), operativo acumulado
  (embarcados, puntualidad, load factor, retraso medio), experiencia,
  puntualidad por vuelo y cohortes por motivo de viaje.
- **Aeropuerto**: plano con zonas y viajeros por zona (+ lista de puertas).
- **Mapa aéreo**: vuelos en el aire y lista.
- **Informe**: resumen operativo del día (informe completo del build o
  resumen local si se carga un bundle sin `report`).

## Generar una simulación desde terminal

El build escribe en `web/dist` (lo regenera por completo) y produce, además,
el **bundle único** de toda la simulación.

```bash
# Escenario hub (un aeropuerto central): rápido, 6.000 pasajeros por defecto
python web/build_snapshots.py --n-passengers 1000 --seed 7

# Red completa (12 aeropuertos / 60 vuelos), paso de snapshot adaptativo
python web/build_snapshots.py --full-day --seed 20260713

# Hub saturado: todos los vuelos a la vez → pico de seguridad
python web/build_snapshots.py --saturate --seed 7

# Forzar margen de llegada (min): márgenes cortos → llegadas tardías/retrasos
python web/build_snapshots.py --full-day --margin 45 --seed 7
```

### Opciones

| Flag | Descripción |
|---|---|
| `--full-day` | Red completa (12 aeropuertos, 60 vuelos). Activa el paso adaptativo por defecto. |
| `--n-passengers N` | Pasajeros (default `6000`). |
| `--seed N` | Semilla para reproducir el mundo (los datos en `web/dist` usan `20260713`). |
| `--adaptive` | Paso de snapshot variable: fino en las ondas de salida (~2–3 min), 15 min de noche. |
| `--step-min N` | Paso fijo entre snapshots (min). |
| `--saturate` | Hub con todos los vuelos saliendo a la vez (demostración de congestión). |
| `--margin MIN` | Fuerza el margen de llegada de todos los pasajeros. |
| `--out-file PATH` | Escribe además el bundle `{meta, snapshots, report}` en `PATH` (`*.json` o `*.json.gz`) para cargarlo en la web. |
| `--no-report` | Omite la generación del informe (sin `report.md`). |

### Qué genera `web/dist`

```
index.html · js/ · vendor/               → la web lista
report.md                                → informe operativo en Markdown
data/simulation.json.gz                  → bundle único {meta, snapshots, report}
```

Solo se publica lo que la web necesita (el bundle único comprimido más los
assets), así `web/dist` pesa ~5 MB y es apto para commitear y desplegar. Con
`--full-day` y 6.000 pasajeros el build tarda ~1 min y produce ~4,5 MB; el paso
adaptativo deja ~430 fotogramas.

## Cargar un JSON propio en la web

Genera un bundle standalone y cárgalo en la vista:

```bash
python web/build_snapshots.py --full-day --seed 7 --out-file /tmp/mi-sim.json.gz
```

En la web, con el botón **↯** (arriba a la derecha):

1. Abrir el selector de archivos y elegir `mi-sim.json.gz`, **o**
2. arrastrar/soltar el archivo sobre la ventana.

Acepta `.json` y `.json.gz` (la descompresión ocurre en el navegador). El
formato del bundle es un único JSON: `{"meta": …, "snapshots": […], "report": …}`.
La vista también acepta simulaciones por `postMessage`:

```js
window.postMessage({ type: "airline.bundle", url: "/data/simulation.json.gz" }, "*");
```

## Persistir y analizar en PostgreSQL (SQL)

El proyecto puede volcar los eventos de una simulación a PostgreSQL y
ejecutar consultas de análisis (`sql/timeline_analysis.sql`). La conexión se
lee de un archivo `.env`.

### 1. Configurar la conexión

Copia `.env.example` a `.env` y rellena con tus credenciales:

```bash
cp .env.example .env
# edita DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
```

> `.env` está en `.gitignore` y **no** se commitea. `.env.example` sí.

### 2. Pipeline completo (recomendado)

El script `refresh_timeline` orquesta los 4 pasos (exportar → crear schema →
cargar → analizar):

```bash
python -m src.scenarios.refresh_timeline
```

### 3. Pasos sueltos

Si prefieres ejecutarlos uno a uno:

```bash
# 1) Genera y exporta los eventos a data/exports/simulation_2026_07_13.json
python -m src.scenarios.export_timeline

# 2) Crea la tabla simulation_events (sql/schema.sql)
python -m src.database.load_simulation   # (aplica schema solo si no existe)

# 3) Carga los eventos en la tabla
python -m src.database.load_simulation

# 4) Ejecuta las consultas de análisis (sql/timeline_analysis.sql)
python -m src.analysis.run_timeline_analysis
```

> Nota: `load_simulation.main()` aplica el schema **y** carga los eventos en una
> sola llamada. Para aplicarlo por separado usa `apply_schema()`/`insert_events()`
> desde el módulo.

### Esquema

La tabla `simulation_events` (definida en `sql/schema.sql`) guarda por evento:
`event_time`, `event_type`, `entity_*`, `flight_number`, `airport_code`, `zone`,
`state`, y métricas (`stress`, `wait_seconds`, `queue_length`,
`security_congested`, `walking_speed`, …). Incluye índices por tiempo, vuelo y
zona.

## Informe operativo

El informe (`web/dist/report.md` o la pestaña **Informe**) resume la jornada:

- **Resumen**: embarcados/perdidos, % que completaron el ciclo, puntualidad
  (retraso ≤ 15 min, estándar de aviación), retraso medio, load factor medio.
- **Colas**: seguridad y check-in por aeropuerto (espera media / P90 / máx,
  congestión, hora pico).
- **Heatmap** de espera media por aeropuerto y hora.
- **Vuelos** operados con sus retrasos y **cohortes** por motivo de viaje.

En un día tranquilo (márgenes amplios) casi todo sale puntual; para ver
retrasos y pérdidas de vuelo usa `--margin 45` o `--saturate`.

## Tests y chequeos

```bash
python -m pytest -q          # suite completa (motor, informe, build web)
node --check web/static/app.js
```

## Deploy: Cloudflare Pages / Netlify

`web/dist` es estática de principio a fin y **se commitea** (ya no está en
`.gitignore`), así que el despliegue no necesita build ni variables de entorno
en el host.

### Flujo (ambos hosts)

1. **Regenera** localmente el dist con la simulación que quieras publicar:
   ```bash
   python web/build_snapshots.py --full-day --seed 20260713
   ```
2. **Commit + push** el dist actualizado:
   ```bash
   git add web/dist
   git commit -m "web: publicar simulación"
   git push
   ```
3. El host publica `web/dist`.

### Cloudflare Pages

1. Crea un *proyecto Pages* conectado al repo.
2. *Build command*: **vacío**. *Build output directory*: **`web/dist`**.
3. Cada push con `web/dist` actualizado se publica automáticamente.

### Netlify

1. Conecta el repo. *Build command*: vacío (o `true`). *Build directory*:
   **`web/dist`**.
2. El push con el dist actualizado publica el sitio.

### La web publicada

- Carga por defecto el bundle `data/simulation.json.gz` del build.
- Con el botón **↯** (o arrastrando un archivo) puedes cargar **cualquier**
  otra simulación generada en consola (`--out-file mi-sim.json.gz`) sin tocar
  el servidor; todo se procesa en el navegador.

**Notas de rendimiento y gotchas**

- La web carga `data/simulation.json.gz` (bundle único comprimido), un único
  request de ~4,5 MB. Cloudflare **no comprime JSON** por defecto, por eso se
  publica el bundle ya en gzip.
- La detección "JSON directo o gzip" intenta primero `JSON.parse` y solo
  descomprime si falla, con lo que funciona aunque el CDN sirva el `.gz` ya
  descomprimido.
- Las rutas son relativas (`data/`, `js/`, `vendor/`), así que el sitio
  funciona también bajo un subpath. No hace falta SPA fallback: los deep
  links usan `#hash`.
- `DecompressionStream` requiere un navegador moderno (Chrome/Edge 80+,
  Firefox 113+, Safari 16.4+).
- El bundle subido por el usuario (botón ↯ / drag&drop) se procesa en el
  navegador sin tocar el servidor.

## Limitaciones conocidas

- El flag `--sql` de `build_snapshots.py` no está cableado al build: la carga a
  PostgreSQL es un pipeline separado (ver **Persistir y analizar en PostgreSQL**),
  orquestado por `src/scenarios/refresh_timeline.py`.
- El margen de llegada mínimo por pasajero es de 45 min; en días
  descongestionados los retrasos son de pocos minutos y la puntualidad queda
  cerca del 100%.