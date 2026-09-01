# Airline Day — simulador de un día de operación aérea

Simulador de *evento discreto* de un día de operación de una red de aeropuertos:
cada pasajero viaja de su origen a su destino atravesando check-in, seguridad,
puerta de embarque y vuelo. El proyecto genera las métricas de la jornada
(colas, puntualidad, load factor, estrés), un **informe operativo** y una
**vista web estática animada** con la evolución del día, todo reproducible
gracias a semillas fijas.

## Estructura

```
├── docs/                   # Diseño del sistema (mundo, motor, web, escala…)
├── src/
│   ├── analysis/           # Informe operativo (report_builder.py)
│   ├── database/           # Capa SQL (pendiente de cablear)
│   ├── data/               # Datos de referencia (países, aeropuertos…)
│   ├── enums/              # Enumerados del dominio
│   ├── scenarios/          # Demos y escenarios (hub, full-day…)
│   ├── simulation/         # Motor: world, runner, replay, generators, queues
│   └── world/              # Entidades del dominio
├── web/
│   ├── static/             # Plantilla de la web (index.html, app.js, style.css)
│   ├── tests/              # Tests del build web
│   └── build_snapshots.py  # Construcción del dist + bundle (línea de comando)
└── web/dist/               # Web estática servible (generada)
```

## Requisitos

- **Python 3.10+** — única dependencia del proyecto (el `requirements.txt`
  está vacío; todo es stdlib).
- **pytest** — para ejecutar la suite de tests.
- **Node.js** — solo opcional, para el chequeo de sintaxis del JS
  (`node --check`).

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
| `--out-file PATH` | Escribe además el bundle `{meta, snapshots, report}` en `PATH` (`*.json` o `*.json.gz`). |
| `--no-report` | Omite la generación del informe (sin `report.json`/`report.md`). |

### Qué genera `web/dist`

```
index.html · js/ · vendor/               → la web lista
report.md                                → informe operativo en Markdown
data/meta.json(.gz)                      → metadatos del día
data/snapshots.json(.gz)                 → fotogramas de la animación
data/report.json                         → informe (JSON, lo usa la web)
data/simulation.json.gz                  → bundle único {meta, snapshots, report}
```

Con `--full-day` y 6.000 pasajeros el build tarda ~1 min y produce ~5,7 MB
comprimidos (≈34 MB sin comprimir). El paso adaptativo deja ~430 fotogramas.

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

## Deploy: Netlify / Cloudflare Pages

La carpeta `web/dist` es estática de principio a fin, así que el despliegue es
trivial y no necesita servidor, build ni variables de entorno.

**Netlify**

1. Conecta el repo. Netlify suele pedir un *build command*: déjalo vacío
   (o `true`). Build option: `Directory` → **`web/dist`** (**sin** command).
2. Tras regenerar `web/dist` localmente
   (`python web/build_snapshots.py --full-day --seed <semilla>`), haz commit y
   push; Netlify publica el directorio.

**Cloudflare Pages**

1. Crea un *proyecto Pages* conectado al repo.
2. *Build command*: vacío. *Build output directory*: **`web/dist`**.
3. Sube el dist actualizado con git (mismo flujo que Netlify).

**Notas de rendimiento y gotchas**

- La web carga `data/simulation.json.gz` (bundle único comprimido) en vez de
  los 34 MB de `snapshots.json`: menos requests y ~5,7 MB por el ancho de
  banda. Cloudflare **no comprime JSON** por defecto, por eso se prefiere el
  bundle gzip.
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

- La integración `--sql` (PostgreSQL) está declarada como *no implementada*
  en la CLI; la capa vive en `src/database/load_simulation.py` (paso
  separado, no cableado al build).
- El margen de llegada mínimo por pasajero es de 45 min; en días
  descongestionados los retrasos son de pocos minutos y la puntualidad queda
  cerca del 100%.