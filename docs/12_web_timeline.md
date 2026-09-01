# 12. Web de timeline estática (desplegable en Netlify + Cloudflare)

## Separación del proyecto

| Ámbito | Dónde | Qué hace |
|---|---|---|
| Simulación + análisis SQL | `src/` + `sql/` (Python, terminal) | Genera la simulación, vuelca a Postgres, analiza |
| Build de datos para la web | `web/build_snapshots.py` | Pre-genera los JSON de snapshots + métricas en `web/dist/` |
| Web (visualización) | `web/static/`, desplegable `web/dist/` | **Solo consume los JSON ya generados**; no simula ni usa la DB en runtime |

La web es **estática**: se despliega idéntica en Netlify y Cloudflare Pages, sin
servidores, sin functions y sin base de datos en producción. Si se re-generan
los snapshots y se re-despliega, se actualiza.

## Generación (terminal)

```bash
python web/build_snapshots.py                # hub JFK por defecto (5 vuelos) → web/dist/
python web/build_snapshots.py --step-min 1   # resolución por minuto (más JSON)
python web/build_snapshots.py --full-day     # día completo: 12 aeropuertos, 60 vuelos
python web/build_snapshots.py --saturate     # hacinamiento: todos llegan al margen mínimo
python web/build_snapshots.py --margin 45    # margen de llegada personalizado (min)
python web/build_snapshots.py --n-passengers 3000   # controla la población
python web/build_snapshots.py --full-day --n-passengers 3000 --seed 20260713
                                              # build multi-aeropuerto (estado actual de web/dist)
```

- Por defecto (sin `--full-day`) se genera el **hub JFK** con
  `build_hub_world(n_passengers=...)`.
- `--full-day` genera la **red completa** con
  `world_factory.generate_world(12, 60, n)` (60 vuelos repartidos entre los 12
  aeropuertos; cada pasajero "nace" en su aeropuerto base vía `home_airport`, ver
  `docs/14_mas_datos.md`).
- `--saturate/--margin/--n-passengers/--seed` ajustan el escenario.

Los tiempos de `meta.json` y snapshots se escriben
como ISO **sin zona horaria** (naive): la web los muestra siempre con
`slice()` sobre la cadena, nunca convirtiendo con `Date.toISOString()`.

Salida en `web/dist/`:

```
dist/
  index.html
  js/{app.js,style.css}
  vendor/chart.umd.js        # Chart.js local (sin CDN)
  data/meta.json             # título, franja de tiempos, layouts de aeropuertos
  data/snapshots.json        # 1 entrada por bucket de ~5 min
```

Cada snapshot contiene, en ese instante:
- **`global`**: pasajeros por estado y cuántos **en el aire** (por vuelo). El
  conteo "en el aire" es **geográficamente correcto**: un pasajero solo cuenta
  como tal si su vuelo está **despegado** (`DEPARTED`, aún no aterrizado); los
  que están a bordo pero en pista antes del despegue se cuentan en el aeropuerto
  de origen (puerta).
- **`by_airport`**: por aeropuerto + zona (entrada / check-in / seguridad /
  puertas / destino / salida), con desglose por puerta.
- **`airports`**: solo los aeropuertos **con gente dentro** (`{code: {zones,
  points}}`) — los puntos llevan zonas en % para pintarlos sobre el layout.
- **`metrics`**:
  - `security`: por aeropuerto, `wait_avg`/`wait_max` (min), `congestion` (%),
    `in_queue` (cola instantánea).
  - `operational`: `boarded`, `missed`, `completed`, `avg_origin_min` — tiempo
    medio en el aeropuerto de **origen** hasta embarcar (recompensa/penaliza por
    factor de seguridad; antes medía origen→destino, renombrado a
    `avg_origin_min` para ser honesto).
- **`flights`**: estado y ocupación de cada vuelo.

`meta.layouts` contiene, por aeropuerto, la geometría **real** en % tomada de
`src/data/airports/*.json`: zonas con rectángulo `c/r`. Para aeropuertos sin
layout propio se usa una rejilla genérica por defecto.

El build es **una sola pasada** sobre los eventos
(`_MetricsTracker`, O(events+snapshots)), no un re-cálculo por bucket.

## Vista previa local

```bash
python -m http.server 8080 --directory web/dist
# abre http://localhost:8080
```

> Debe servirse por HTTP (no `file://`): el navegador no permite `fetch()` de
> JSON local bajo `file://`. Se puede encadenar la pestaña/frame inicial con
> hashes de desarrollo: `#airport:110`, `#air:60`, `#metrics`.

## Deploy

### Netlify
- Build command: `python web/build_snapshots.py`
- Publish directory: `web/dist`

### Cloudflare Pages
- `npx wrangler pages deploy web/dist`
- o dashboard → *Create a project* → *Direct Upload* de `web/dist`.

## Controles de la timeline
- **Play / Pause** (o `Espacio`), **anterior/siguiente** (o flechas), **slider**
  para saltar a cualquier instante, y selector de **velocidad** (1x/5x/10x/25x/50x).
- **1x = 1 hora simulada por minuto real** (los snapshots son cada 5 min
  simulados → 5 s por frame a 1x). Las velocidades superiores multiplican eso.
- **Pestañas** (la timeline queda fija arriba, independiente de la pestaña):
  - **Métricas**: contadores globales + chart de seguridad (eje x tiempo, filas
    de cola con entrar/salir sobre doble eje) y de operativo (embarcados /
    perdidos / tiempo medio de origen), más la evolución de cola por aeropuerto.
  - **Aeropuerto**: selector con los **12 aeropuertos**; maqueta con el **layout
    real** (zonas en %, puertas, flujo entrada → check-in → seguridad →
    puertas), gente animada por zona y chips de conteo. El check-in y el
    embarque ahora muestran gente real (la simulación emite los estados
    `Check In` / `Boarding`, no solo llegadas a seguridad).
  - **Mapa aéreo**: red de aeropuertos, **rutas como Béziers cuadráticas**
    (sin superposición entre las paralelas de rutas opuestas), vuelos en el
    aire animados sobre su curva con orientación según la tangente, y pasajeros
    a bordo; las rutas inactivas se atenúan.

## Tests
```bash
python -m pytest web/tests/test_snapshot_builder.py -q   # 8 tests del builder
python -m pytest -q                                      # suite completa (146)
```

## Escalado futuro (Hito 2+)
- Día completo real (`--full-day`): 12 aeropuertos, 60 vuelos, ~10k px.
  Si se sube la resolución (por minuto / por vuelo) y hace falta comprimir los
  JSON (gzip/Parquet en el CDN), el régimen de snapshots se ajusta desde el
  builder sin tocar la web.