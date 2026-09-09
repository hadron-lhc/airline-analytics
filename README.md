# Airline Day — a day of airline operations simulator

Discrete-event simulator of a day of operations of an airport network: each
passenger travels from origin to destination through check-in, security,
boarding gate and flight. The project produces the day's metrics (queues,
punctuality, load factor, stress), an **operational report** and an **animated
static web view** with the evolution of the day, all reproducible thanks to
fixed seeds.

## Live demo

**https://airline-analytics.valentingonzalezdaumes.workers.dev/**

## Demo videos

Short screen recordings of the web view, one per tab:

| | |
|---|---|
| **Metrics** — counters, security/check-in queues, experience, punctuality and cohorts | **Airport** — floor plan with zones and travelers per zone |
| <video src="images/video_metrics.webm" controls width="380"></video> | <video src="images/video_airport.webm" controls width="380"></video> |
| **Air map** — flights in the air and list | **Report** — day's operational summary |
| <video src="images/video_air_map.webm" controls width="380"></video> | <video src="images/video_report.webm" controls width="380"></video> |

## Structure

```
├── .env.example            # Configuration template (create .env from it)
├── docs/                   # System design (world, engine, web, scale…)
├── sql/
│   ├── schema.sql          # simulation_events table schema (PostgreSQL)
│   └── timeline_analysis.sql  # Timeline analysis queries
├── src/
│   ├── analysis/           # Operational report (report_builder.py) + SQL analysis
│   ├── database/           # SQL layer: loads events into PostgreSQL
│   ├── data/               # Reference data (countries, airports…)
│   ├── enums/              # Domain enums
│   ├── scenarios/          # Scenarios: hub, full-day, export/refresh timeline
│   ├── simulation/         # Engine: world, runner, replay, generators, queues
│   └── world/              # Domain entities
├── web/
│   ├── static/             # Web templates (index.html, app.js, style.css)
│   ├── tests/              # Web build tests
│   └── build_snapshots.py  # dist + bundle build (command line)
└── web/dist/               # Servable static web (generated, committed)
```

## Requirements

- **Python 3.10+**
- **PostgreSQL** — only for the persistence/SQL analysis layer (optional if
  you just want the web).
- **Node.js** — optional, only for the JS syntax check
  (`node --check`).

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

> For the web (build + `http.server`) nothing else needs installing: the build
> only uses the standard library.

## View the web (fast path)

```bash
python -m http.server 8080 --directory web/dist
```

Open `http://localhost:8080`. The web is **100% static**: nothing else is
needed. Note: opening `index.html` with a double click does not work (the data
is loaded via `fetch`); always serve the directory.

### How it works

- **Fixed timeline** at the top: ▶/⏸ (or `space`), ← → arrows, slider and
  speed 1×–50× *(1 simulated min = 1 real s at 1×)*. Links with
  `#tab:n` open a tab and frame (`#report:42`).
- **Metrics**: global counters, security/check-in queues (at the moment and
  over the day per airport), cumulative operations (boarded, punctuality,
  load factor, average delay), experience, punctuality per flight and cohorts
  by travel purpose.
- **Airport**: floor plan with zones and travelers per zone (+ gate list).
- **Air map**: flights in the air and list.
- **Report**: day's operational summary (full build report or local summary
  when loading a bundle without `report`).

## Generating a simulation from the terminal

The build writes into `web/dist` (regenerated completely) and also produces a
**single bundle** with the whole simulation.

```bash
# Hub scenario (a central airport): fast, 6,000 passengers by default
python web/build_snapshots.py --n-passengers 1000 --seed 7

# Full network (12 airports / 60 flights), adaptive snapshot step
python web/build_snapshots.py --full-day --seed 20260713

# Saturated hub: all flights at once → security peak
python web/build_snapshots.py --saturate --seed 7

# Force arrival margin (min): short margins → late arrivals/delays
python web/build_snapshots.py --full-day --margin 45 --seed 7
```

### Options

| Flag | Description |
|---|---|
| `--full-day` | Full network (12 airports, 60 flights). Enables the adaptive step by default. |
| `--n-passengers N` | Passengers (default `6000`). |
| `--seed N` | Seed to reproduce the world (the data in `web/dist` uses `20260713`). |
| `--adaptive` | Variable snapshot step: fine during departure waves (~2–3 min), 15 min at night. |
| `--step-min N` | Fixed step between snapshots (min). |
| `--saturate` | Hub with all flights departing at once (congestion demo). |
| `--margin MIN` | Forces the arrival margin of every passenger. |
| `--out-file PATH` | Also writes the bundle `{meta, snapshots, report}` to `PATH` (`*.json` or `*.json.gz`) to load it in the web. |
| `--no-report` | Skips report generation (no `report.md`). |

### What `web/dist` generates

```
index.html · js/ · vendor/               → the ready web
report.md                                → operational report in Markdown
data/simulation.json.gz                  → single bundle {meta, snapshots, report}
```

Only what the web needs is published (the single compressed bundle plus the
assets), so `web/dist` weighs ~5 MB and is suitable for committing and
deploying. With `--full-day` and 6,000 passengers the build takes ~1 min and
produces ~4.5 MB; the adaptive step leaves ~430 frames.

## Loading your own JSON in the web

Generate a standalone bundle and load it in the view:

```bash
python web/build_snapshots.py --full-day --seed 7 --out-file /tmp/mi-sim.json.gz
```

In the web, with the **Load simulation** button (top center):

1. Open the file picker and choose `mi-sim.json.gz`, **or**
2. drag & drop the file over the window.

Accepts `.json` and `.json.gz` (decompression happens in the browser). The
bundle format is a single JSON: `{"meta": …, "snapshots": […], "report": …}`.
The view also accepts simulations via `postMessage`:

```js
window.postMessage({ type: "airline.bundle", url: "/data/simulation.json.gz" }, "*");
```

## Persisting and analyzing in PostgreSQL (SQL)

The project can dump a simulation's events to PostgreSQL and run analysis
queries (`sql/timeline_analysis.sql`). The connection is read from a `.env`
file.

### 1. Configure the connection

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
# edit DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
```

> `.env` is in `.gitignore` and is **not** committed. `.env.example` is.

### 2. Full pipeline (recommended)

The `refresh_timeline` script orchestrates the 4 steps (export → create schema →
load → analyze):

```bash
python -m src.scenarios.refresh_timeline
```

### 3. Individual steps

If you prefer to run them one by one:

```bash
# 1) Generates and exports the events to data/exports/simulation_2026_07_13.json
python -m src.scenarios.export_timeline

# 2) Creates the simulation_events table (sql/schema.sql)
python -m src.database.load_simulation   # (applies the schema only if it doesn't exist)

# 3) Loads the events into the table
python -m src.database.load_simulation

# 4) Runs the analysis queries (sql/timeline_analysis.sql)
python -m src.analysis.run_timeline_analysis
```

> Note: `load_simulation.main()` applies the schema **and** loads the events in
> a single call. To apply them separately use `apply_schema()`/`insert_events()`
> from the module.

### Schema

The `simulation_events` table (defined in `sql/schema.sql`) stores per event:
`event_time`, `event_type`, `entity_*`, `flight_number`, `airport_code`, `zone`,
`state`, and metrics (`stress`, `wait_seconds`, `queue_length`,
`security_congested`, `walking_speed`, …). Includes indexes by time, flight and
zone.

## Operational report

The report (`web/dist/report.md` or the **Report** tab) summarizes the day:

- **Summary**: boarded/missed, % that completed the cycle, punctuality (delay ≤
  15 min, aviation standard), average delay, average load factor.
- **Queues**: security and check-in per airport (avg wait / P90 / max,
  congestion, peak hour).
- **Heatmap** of average wait per airport and hour.
- **Flights** operated with their delays and **cohorts** by travel purpose.

On a calm day (wide margins) almost everything is on time; to see delays and
missed flights use `--margin 45` or `--saturate`.

## Tests and checks

```bash
python -m pytest -q          # full suite (engine, report, web build)
node --check web/static/app.js
```

## Deploy: Cloudflare Pages / Netlify

`web/dist` is static end to end and **is committed** (no longer in
`.gitignore`), so the deploy needs no build or environment variables on the
host.

### Flow (both hosts)

1. **Regenerate** the dist locally with the simulation you want to publish:
   ```bash
   python web/build_snapshots.py --full-day --seed 20260713
   ```
2. **Commit + push** the updated dist:
   ```bash
   git add web/dist
   git commit -m "web: publish simulation"
   git push
   ```
3. The host publishes `web/dist`.

### Cloudflare Pages

1. Create a *Pages project* connected to the repo.
2. *Build command*: **empty**. *Build output directory*: **`web/dist`**.
3. Every push with an updated `web/dist` publishes automatically.

### Netlify

1. Connect the repo. *Build command*: empty (or `true`). *Build directory*:
   **`web/dist`**.
2. The push with the updated dist publishes the site.

### The published web

- Loads the default bundle `data/simulation.json.gz` from the build.
- With the **Load simulation** button (or drag & drop) you can load **any**
  other simulation generated on the command line (`--out-file mi-sim.json.gz`)
  without touching the server; everything is processed in the browser.

**Performance notes and gotchas**

- The web loads `data/simulation.json.gz` (a single compressed bundle), a single
  request of ~4.5 MB. Cloudflare does **not compress JSON** by default, so the
  bundle is published already gzipped.
- The "plain JSON or gzip" detection first tries `JSON.parse` and only
  decompresses if it fails, so it works even if the CDN serves the `.gz` already
  decompressed.
- The paths are relative (`data/`, `js/`, `vendor/`), so the site also works
  under a subpath. No SPA fallback needed: deep links use `#hash`.
- `DecompressionStream` requires a modern browser (Chrome/Edge 80+, Firefox
  113+, Safari 16.4+).
- The bundle uploaded by the user (Load simulation button / drag & drop) is
  processed in the browser without touching the server.

## Known limitations

- The `--sql` flag of `build_snapshots.py` is not wired into the build: the
  PostgreSQL load is a separate pipeline (see **Persisting and analyzing in
  PostgreSQL**), orchestrated by `src/scenarios/refresh_timeline.py`.
- The minimum arrival margin per passenger is 45 min (business travelers cut it
  close; leisure/family keep 110-130 min). Congestion at peak waves can now form
  real security queues, which is what drives stress, pressure and delays.