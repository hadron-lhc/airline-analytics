/* Airline Timeline viewer — loads pre-generated snapshots and plays them.
 * 1x speed = 1 simulated hour per real minute.
 * Times are naive ISO strings (sim local time); never round-trip them through
 * `new Date().toISOString()` or the clock shifts on non-UTC browsers.
 */
(() => {
  "use strict";

  const DATA = "data/";
  const SNAPSHOT_MIN = 5; // each snapshot is 5 simulated minutes
  // 1 simulated hour (12 snapshots) must span 60 real seconds at 1x:
  const FRAME_MS_1X = 60000 / (60 / SNAPSHOT_MIN); // = 5000 ms

  let meta = null;
  let snapshots = null;
  let index = 0;
  let playing = false;
  let timer = null;
  let speedMult = 5;

  let opChart = null;
  let stressChart = null;
  let flightChart = null;
  let cohortChart = null;
  const charts = {};
  let activeTab = "metrics";
  let selectedAirport = null;

  const $ = (id) => document.getElementById(id);

  const PALETTE = [
    "#3aa0ff", "#37d67a", "#ffb347", "#c792ea",
    "#ff5d72", "#2be2c0", "#f06292", "#aed581",
  ];

  // ---- time helpers (naive ISOs, no Date/UTC munging) ----
  const hhmm = (iso) => iso.slice(11, 16);
  const mmdd = (iso) => iso.slice(5, 10);
  const isoMin = (iso) => parseInt(iso.slice(11, 13), 10) * 60 + parseInt(iso.slice(14, 16), 10);

  const STATE_LABELS = {
    "At Home": "At home",
    "Going to Airport": "To airport",
    "At Airport": "At airport",
    "Check In": "Check-in",
    "At Security": "Security",
    "Waiting Gate": "Gate",
    "Boarding": "Boarding",
    "On Flight": "In the air",
    "Arrived": "Arrived",
    "At Destination Airport": "Destination",
    "Exited Airport": "Exited",
  };

  const ZONE_STYLE = {
    entrance: { label: "Entrada", color: "#37d67a" },
    check_in: { label: "Check-in", color: "#ffb347" },
    security: { label: "Seguridad", color: "#ff5d72" },
    gate: { label: "Puertas", color: "#3aa0ff" },
    destination: { label: "Llegadas", color: "#c792ea" },
    exited: { label: "Salida", color: "#2bbf8a" },
  };

  // Approximate world positions (%) for the air map (all 12 airports in meta).
  // Spread apart so node circles (and their labels) don't overlap, especially
  // in the Europe (LHR/CDG/BCN/MAD) and South America (MEX/BOG/GRU/SCL/EZE)
  // clusters that share similar longitude bands.
  const AIRPORT_POS = {
    EZE: [21, 92], MIA: [14, 46], JFK: [20, 30], LAX: [5, 26],
    MAD: [44, 36], BCN: [52, 26], CDG: [48, 19], LHR: [43, 12],
    GRU: [29, 74], MEX: [15, 58], BOG: [14, 68], SCL: [26, 85],
  };

  async function init() {
    const [m, s] = await Promise.all([
      fetch(DATA + "meta.json").then((r) => r.json()),
      fetch(DATA + "snapshots.json").then((r) => r.json()),
    ]);
    meta = m;
    snapshots = s;

    $("sim-time").textContent = "00:00";
    $("frame-info").textContent = `1 / ${snapshots.length}`;

    $("axis").textContent =
      `${meta.start.slice(0, 16).replace("T", " ")}  →  ` +
      `${meta.end.slice(0, 16).replace("T", " ")}`;
    $("legend").textContent =
      `${meta.passengers} pasajeros · ${meta.flights} vuelos · ` +
      `${meta.total_events} eventos · 1 h sim. = 1 min real @1x`;

    const slider = $("slider");
    slider.max = snapshots.length - 1;
    slider.value = 0;
    slider.addEventListener("input", () => { index = Number(slider.value); render(); });

    $("btn-play").addEventListener("click", togglePlay);
    $("btn-prev").addEventListener("click", () => { index = Math.max(0, index - 1); render(); });
    $("btn-next").addEventListener("click", () => { index = Math.min(snapshots.length - 1, index + 1); render(); });
    $("speed").addEventListener("change", (e) => { speedMult = Number(e.target.value); if (playing) restart(); });

    document.addEventListener("keydown", (e) => {
      if (e.code === "Space") { e.preventDefault(); togglePlay(); }
      if (e.code === "ArrowLeft") { index = Math.max(0, index - 1); render(); }
      if (e.code === "ArrowRight") { index = Math.min(snapshots.length - 1, index + 1); render(); }
    });

    setupTabs();
    setupAirportSelect();
    buildAirMap();

    const hashMatch = location.hash.match(/^#([a-z]+)?(?::(\d+))?$/);
    if (hashMatch) {
      if (hashMatch[1] === "airport" || hashMatch[1] === "air" || hashMatch[1] === "metrics") selectTab(hashMatch[1]);
      if (hashMatch[2]) index = Math.min(snapshots.length - 1, Math.max(0, Number(hashMatch[2])));
    }

    render();
  }

  // ---------- tab switching ----------
  function selectTab(name) {
    activeTab = name;
    document.querySelectorAll(".tab").forEach((b) => {
      b.classList.toggle("active", b.dataset.tab === name);
    });
    document.querySelectorAll(".tab-content").forEach((el) => { el.hidden = el.id !== "tab-" + name; });
  }

  function setupTabs() {
    document.querySelectorAll(".tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        selectTab(btn.dataset.tab);
        render();
      });
    });
  }

  // ---------- playback ----------
  function frameMs() { return FRAME_MS_1X / speedMult; }

  function togglePlay() {
    playing = !playing;
    $("btn-play").innerHTML = playing ? "&#10074;&#10074; Pause" : "&#9654; Play";
    if (playing) {
      if (index >= snapshots.length - 1) index = 0;
      timer = setInterval(step, frameMs());
    } else { clearInterval(timer); timer = null; }
  }

  function restart() { clearInterval(timer); timer = setInterval(step, frameMs()); }

  function step() {
    index = Math.min(snapshots.length - 1, index + 1);
    render();
    if (index >= snapshots.length - 1) {
      playing = false;
      $("btn-play").innerHTML = "&#9654; Play";
      clearInterval(timer);
      timer = null;
    }
  }

  function render() {
    const snap = snapshots[index];
    $("slider").value = index;
    $("frame-info").textContent = `${index + 1} / ${snapshots.length}`;
    $("sim-time").textContent = hhmm(snap.t) + " · " + mmdd(snap.t);

    if (activeTab === "metrics") renderMetrics(snap);
    else if (activeTab === "airport") renderAirport(snap);
    else renderAir(snap);
  }

  // ==================================================================
  // TAB: Metrics
  // ==================================================================
  function renderMetrics(snap) {
    renderCounters(snap);
    renderQueueMoment(snap, "security", "security-chart");
    renderQueueMoment(snap, "checkin", "checkin-chart");
    renderOperational(snap);
    renderStress(snap);
    renderFlight(snap);
    renderCohorts(snap);
    renderQueueOverDay(snap, "security", "security-queue-chart", "Pasajeros en cola");
    renderQueueOverDay(snap, "checkin", "checkin-queue-chart", "Pasajeros en cola de check-in");
  }

  function renderCounters(snap) {
    const g = snap.global;
    const air = g.air_total || 0;
    const state = g.by_state || {};
    const origin =
      (state["At Airport"] || 0) + (state["Check In"] || 0) +
      (state["At Security"] || 0) + (state["Waiting Gate"] || 0) +
      (state["Boarding"] || 0);
    const dest = (state["Arrived"] || 0) + (state["At Destination Airport"] || 0);
    const exited = state["Exited Airport"] || 0;
    const toAirport = state["Going to Airport"] || 0;
    const home = state["At Home"] || 0;

    const counters = [
      ["En el aire", air, "#3aa0ff"],
      ["En aeropuerto de origen", origin, "#ffb347"],
      ["En destino", dest, "#c792ea"],
      ["Salieron", exited, "#37d67a"],
      ["Yendo al aeropuerto", toAirport, "#8ca0c0"],
      ["En casa", home, "#888"],
    ];
    $("counters").innerHTML = counters.map(
      ([lbl, num, color]) =>
        `<div class="counter"><div class="num" style="color:${color}">${num}</div><div class="lbl">${lbl}</div></div>`
    ).join("");
  }

  // Render a per-moment bar chart (espera media + % congestión) for a queue
  // metric ("security" or "checkin").
  function renderQueueMoment(snap, metric, canvasId) {
    const data = (snap.metrics && snap.metrics[metric]) || {};
    const codes = Object.keys(data).sort();
    if (!codes.length) {
      if (charts[canvasId]) { charts[canvasId].destroy(); }
      delete charts[canvasId];
      return;
    }
    const labels = codes;
    const wait = codes.map((c) => data[c].wait_avg_s);
    const congest = codes.map((c) => data[c].congested_pct);
    if (charts[canvasId]) charts[canvasId].destroy();
    const ctx = $(canvasId).getContext("2d");
    charts[canvasId] = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          { label: "Espera media (s)", data: wait, yAxisID: "y", backgroundColor: "#3aa0ff" },
          { label: "% congestión", data: congest, yAxisID: "y1", backgroundColor: "#ff5d72" },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: "#cfd8ea" } } },
        scales: {
          x: { ticks: { color: "#cfd8ea" } },
          y: { position: "left", title: { display: true, text: "segundos", color: "#8ca0c0" }, ticks: { color: "#cfd8ea" }, beginAtZero: true },
          y1: { position: "right", min: 0, max: 100, title: { display: true, text: "%", color: "#8ca0c0" }, grid: { drawOnChartArea: false }, ticks: { color: "#cfd8ea" } },
        },
      },
    });
  }

  // Cumulative "in queue over the day" line chart for a queue metric.
  function renderQueueOverDay(snap, metric, canvasId, yAxisText) {
    const codes = queueCodes(metric);
    const rows = snapshots.slice(0, index + 1).map((s) => {
      const data = (s.metrics && s.metrics[metric]) || {};
      const row = { t: hhmm(s.t) };
      codes.forEach((c) => { row[c] = (data[c] && data[c].in_queue) || 0; });
      return row;
    });
    const datasets = codes.map((c, ci) => ({
      label: c,
      data: rows.map((r) => r[c]),
      borderColor: PALETTE[ci % PALETTE.length],
      backgroundColor: PALETTE[ci % PALETTE.length] + "22",
      fill: true,
      tension: 0.3,
      pointRadius: 0,
      borderWidth: 2,
    }));
    if (charts[canvasId]) charts[canvasId].destroy();
    const ctx = $(canvasId).getContext("2d");
    charts[canvasId] = new Chart(ctx, {
      type: "line",
      data: { labels: rows.map((r) => r.t), datasets },
      options: {
        responsive: true, maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: { legend: { labels: { color: "#cfd8ea", boxWidth: 12 } } },
        scales: {
          x: { ticks: { color: "#8ca0c0", maxRotation: 0, autoSkip: true, maxTicksLimit: 12 } },
          y: { beginAtZero: true, title: { display: true, text: yAxisText, color: "#8ca0c0" }, ticks: { color: "#cfd8ea" } },
        },
      },
    });
  }

  const _queueCodesCache = {};
  function queueCodes(metric) {
    if (_queueCodesCache[metric]) return _queueCodesCache[metric];
    const seen = new Set();
    for (const s of snapshots) {
      const data = (s.metrics && s.metrics[metric]) || {};
      Object.keys(data).forEach((c) => seen.add(c));
    }
    _queueCodesCache[metric] = [...seen].sort();
    return _queueCodesCache[metric];
  }

  // SLA / experiencia (acumulado): estrés al embarque + presión de tiempo.
  function renderStress(snap) {
    const st = (snap.metrics && snap.metrics.stress) || {};
    const labels = ["Estrés prom.\nembarque", "…estresados\n(>60)", "Esperas con\npresión alta"];
    const data = [
      st.boarding_avg || 0,
      st.boarding_stressed_pct || 0,
      st.high_pressure_pct || 0,
    ];
    const colors = ["#3aa0ff", "#ff5d72", "#ffb347"];
    if (stressChart) stressChart.destroy();
    const ctx = $("stress-chart").getContext("2d");
    stressChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [{ label: "% o valor", data, backgroundColor: colors }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          title: {
            display: true,
            text: `${(st.waited || 0)} esperas → ${st.high_pressure_pct || 0}% con presión alta`,
            color: "#cfd8ea",
          },
        },
        scales: {
          y: { beginAtZero: true, title: { display: true, text: "promedio / %", color: "#8ca0c0" }, ticks: { color: "#cfd8ea" } },
          x: { ticks: { color: "#cfd8ea", fontSize: 11 } },
        },
      },
    });
  }

  // Puntualidad por vuelo (acumulado): embarcados vs perdidos.
  function renderFlight(snap) {
    const op = (snap.metrics && snap.metrics.operational) || {};
    const flights = op.flight || {};
    const labels = Object.keys(flights);
    if (!labels.length) {
      if (flightChart) { flightChart.destroy(); flightChart = null; }
      return;
    }
    const boarded = labels.map((f) => flights[f].boarded);
    const missed = labels.map((f) => flights[f].missed);
    if (flightChart) flightChart.destroy();
    const ctx = $("flight-chart").getContext("2d");
    flightChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          { label: "Embarcados", data: boarded, backgroundColor: "#37d67a" },
          { label: "Perdidos", data: missed, backgroundColor: "#ff5d72" },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: "#cfd8ea" } } },
        scales: {
          x: { ticks: { color: "#cfd8ea" } },
          y: { beginAtZero: true, title: { display: true, text: "pasajeros", color: "#8ca0c0" }, ticks: { color: "#cfd8ea" } },
        },
      },
    });
  }

  // Cohortes por motivo de viaje (acumulado): missed-rate + estrés medio.
  function renderCohorts(snap) {
    const cohorts = (snap.metrics && snap.metrics.cohorts) || {};
    const labels = Object.keys(cohorts);
    if (!labels.length) {
      if (cohortChart) { cohortChart.destroy(); cohortChart = null; }
      return;
    }
    const missedRate = labels.map((c) => (cohorts[c].missed_rate || 0) * 100);
    const avgStress = labels.map((c) => cohorts[c].avg_stress || 0);
    if (cohortChart) cohortChart.destroy();
    const ctx = $("cohort-chart").getContext("2d");
    cohortChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          { label: "% perdieron vuelo", data: missedRate, yAxisID: "y", backgroundColor: "#ff5d72" },
          { label: "Estrés medio", data: avgStress, yAxisID: "y1", backgroundColor: "#3aa0ff" },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: "#cfd8ea" } } },
        scales: {
          x: { ticks: { color: "#cfd8ea" } },
          y: { position: "left", min: 0, max: 100, title: { display: true, text: "%", color: "#8ca0c0" }, ticks: { color: "#cfd8ea" } },
          y1: { position: "right", min: 0, max: 100, title: { display: true, text: "estrés", color: "#8ca0c0" }, grid: { drawOnChartArea: false }, ticks: { color: "#cfd8ea" } },
        },
      },
    });
  }

  function renderOperational(snap) {
    const op = (snap.metrics && snap.metrics.operational) || {};
    const boarded = op.boarded || 0;
    const missed = op.missed || 0;
    const completed = op.completed || 0;
    const avg = op.avg_origin_min || 0;
    if (opChart) opChart.destroy();
    const ctx = $("op-chart").getContext("2d");
    opChart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: ["Embarcados", "Perdidos"],
        datasets: [{ data: [boarded, missed], backgroundColor: ["#37d67a", "#ff5d72"] }],
      },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: "55%",
        plugins: {
          legend: { labels: { color: "#cfd8ea" } },
          title: {
            display: true,
            text: `Embarcados ${boarded} · Perdidos ${missed} · ${completed} en origen · prom ${avg} min en aeropuerto`,
            color: "#cfd8ea",
          },
        },
      },
    });
  }

  // ==================================================================
  // TAB: Airport floor-plan (real layouts from meta.layouts)
  // ==================================================================
  function setupAirportSelect() {
    const sel = $("airport-select");
    const codes = Object.keys(meta.layouts || {}).sort();
    codes.forEach((code) => {
      const opt = document.createElement("option");
      opt.value = code;
      opt.textContent = code;
      sel.appendChild(opt);
    });
    selectedAirport = codes.includes("JFK") ? "JFK" : (codes[0] || null);
    sel.value = selectedAirport || "";
    sel.addEventListener("change", (e) => { selectedAirport = e.target.value; render(); });
    if (!codes.length) $("airport-select").style.display = "none";
  }

  function svgEl() {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "flow-svg");
    svg.setAttribute("viewBox", "0 0 100 100");
    svg.setAttribute("preserveAspectRatio", "none");
    return svg;
  }

  function flowArrows(svg, geo) {
    const flow = geo && geo.flow && geo.flow.length ? geo.flow : null;
    if (!flow) return;
    const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    const marker = document.createElementNS("http://www.w3.org/2000/svg", "marker");
    marker.setAttribute("id", "flow-arrow");
    marker.setAttribute("viewBox", "0 0 10 10");
    marker.setAttribute("refX", "8");
    marker.setAttribute("refY", "5");
    marker.setAttribute("markerWidth", "5");
    marker.setAttribute("markerHeight", "5");
    marker.setAttribute("orient", "auto");
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", "M 0 0 L 10 5 L 0 10 z");
    path.setAttribute("fill", "#566e9c");
    marker.appendChild(path);
    defs.appendChild(marker);
    svg.appendChild(defs);

    for (let i = 0; i < flow.length - 1; i++) {
      const a = geo.zones[flow[i]].c;
      const b = geo.zones[flow[i + 1]].c;
      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", a[0]); line.setAttribute("y1", a[1]);
      line.setAttribute("x2", b[0]); line.setAttribute("y2", b[1]);
      line.setAttribute("class", "flow-line");
      if (i === flow.length - 2) line.setAttribute("marker-end", "url(#flow-arrow)");
      svg.appendChild(line);
    }
  }

  function renderAirport(snap) {
    if (!selectedAirport) return;
    const geo = meta.layouts[selectedAirport] || { zones: {} };
    const apt = snap.by_airport[selectedAirport] || {};
    const floor = snap.airports[selectedAirport] || null;
    const floorZones = (floor && floor.zones) || {};
    const points = (floor && floor.points) || [];

    const map = $("airport-map");
    const oldDots = [...map.children].filter((c) => c.classList.contains("person-dot"));
    map.innerHTML = "";

    // flow arrows (SVG overlay) + zone rooms
    if (Object.keys(geo.zones).length) {
      const svg = svgEl();
      flowArrows(svg, geo);
      map.appendChild(svg);
    }

    Object.keys(geo.zones).forEach((zone) => {
      const info = ZONE_STYLE[zone];
      if (!info) return;
      const c = geo.zones[zone].c;
      const r = geo.zones[zone].r;
      const total = floorZones[zone] != null ? floorZones[zone] : (apt[zone] || 0);
      const el = document.createElement("div");
      el.className = "zone-area";
      el.style.left = (c[0] - r[0]) + "%";
      el.style.top = (c[1] - r[1]) + "%";
      el.style.width = (r[0] * 2) + "%";
      el.style.height = (r[1] * 2) + "%";
      el.style.borderColor = info.color;
      el.innerHTML =
        `<span class="zone-name" style="color:${info.color}">${info.label}</span>` +
        `<span class="zone-count" style="background:${info.color}">${total}</span>`;
      map.appendChild(el);
    });

    // persons (sampled) with real movement via CSS transitions (dots reused)
    const pool = new Map(oldDots.map((d) => [d.dataset.id, d]));
    points.forEach((pt) => {
      let d = pool.get(pt.id);
      if (!d) {
        d = document.createElement("div");
        d.className = "person-dot";
        d.dataset.id = pt.id;
      }
      const color = (ZONE_STYLE[pt.zone] || {}).color || "#ffd866";
      d.style.left = pt.x + "%";
      d.style.top = pt.y + "%";
      d.style.background = color;
      d.style.boxShadow = `0 0 4px ${color}`;
      d.title = (pt.g ? "Gate " + pt.g : "") || ((ZONE_STYLE[pt.zone] || {}).label || pt.zone);
      map.appendChild(d);
    });

    const shown = points.length;
    const totalPeople = apt.total || 0;
    $("airport-note").textContent = totalPeople
      ? `Ahora hay ${totalPeople} personas en ${selectedAirport}. ` +
        `Se muestran ${shown} puntos de muestra; los indicadores de cada zona muestran el total real. Los puntos se agrupan por puerta/zona según el layout real.`
      : `No hay pasajeros en ${selectedAirport} en este momento.`;

    const gates = apt.gates || {};
    $("airport-gates").innerHTML =
      `<h3 style="margin:0 0 8px;font-size:13px;color:var(--muted);width:100%">Ocupación por puerta</h3>` +
      (Object.keys(gates).length
        ? Object.entries(gates).map(([g, v]) =>
            `<div class="gate-chip">Gate ${g}<b>${v}</b></div>`).join("")
        : `<span class="zone-tag" style="text-align:left">(sin pasajeros en puertas)</span>`);

    const pax = meta.airports[selectedAirport] || selectedAirport;
    $("airport-title").textContent = pax;
    $("airport-side").textContent =
      (geo.zones.gate ? "Salidas — " : "Llegadas — ") + Object.keys(geo.gates || {}).length + " puertas";
  }

  // ==================================================================
  // TAB: Air map (curved flows over the network)
  // ==================================================================
  let airMapBuilt = false;

  function nodeEl(code) {
    const pos = AIRPORT_POS[code];
    if (!pos) return null;
    const hub = code === "JFK";
    const el = document.createElement("div");
    el.className = "airport-node" + (hub ? " hub" : "");
    el.style.left = pos[0] + "%";
    el.style.top = pos[1] + "%";
    el.innerHTML = `<div class="dot">${code}</div><div class="name">${code}</div>`;
    return el;
  }

  function buildAirMap() {
    const map = $("air-map");
    Object.keys(AIRPORT_POS).forEach((code) => {
      const node = nodeEl(code);
      if (node) map.appendChild(node);
    });
    airMapBuilt = true;
  }

  function quadPath(x1, y1, x2, y2) {
    // quadratic bezier curved sideways; side depends on route hash (deterministic)
    const dx = x2 - x1, dy = y2 - y1;
    const len = Math.hypot(dx, dy) || 1;
    const h1 = Math.abs(dx * 9999 + dy * 101) % 2; // 0 or 1
    const side = h1 ? 1 : -1;
    const k = 0.16; // bow magnitude
    const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
    const nx = -dy / len, ny = dx / len;
    const cx = mx + side * k * len * nx;
    const cy = my + side * k * len * ny;
    return { d: `M ${x1.toFixed(2)} ${y1.toFixed(2)} Q ${cx.toFixed(2)} ${cy.toFixed(2)} ${x2.toFixed(2)} ${y2.toFixed(2)}`, cx, cy };
  }

  function pointOnQuad(c, t) {
    const [x1, y1] = c.p0;
    const [cx, cy] = c.c;
    const [x2, y2] = c.p2;
    const u = 1 - t;
    return {
      x: u * u * x1 + 2 * u * t * cx + t * t * x2,
      y: u * u * y1 + 2 * u * t * cy + t * t * y2,
      a: Math.atan2(2 * u * (cy - y1) + 2 * t * (y2 - cy),
                    2 * u * (cx - x1) + 2 * t * (x2 - cx)),
    };
  }

  function toMinutes(hhmmStr) {
    const [h, m] = hhmmStr.split(":").map(Number);
    return h * 60 + m;
  }

  function renderAir(snap) {
    const map = $("air-map");
    map.querySelectorAll("svg.air-svg, .air-plane").forEach((el) => el.remove());

    const svg = svgEl();
    svg.setAttribute("class", "air-svg");
    map.insertBefore(svg, map.firstChild);

    const flights = snap.flights || {};
    const air = snap.global.air_by_flight || {};
    const tMin = isoMin(snap.t);

    const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    svg.appendChild(defs);

    const byRoute = new Map(); // route key -> {from, to, flights:[{code, frac, active}]}
    Object.keys(flights).forEach((code) => {
      const f = flights[code];
      const from = AIRPORT_POS[f.from];
      const to = AIRPORT_POS[f.to];
      if (!from || !to) return;
      const dep = toMinutes(f.dep), arr = toMinutes(f.arr);
      let frac = 0;
      if (arr > dep) frac = Math.min(1, Math.max(0, (tMin - dep) / (arr - dep)));
      const active = f.status === "Departed";
      if (f.status === "Scheduled" || f.status === "Boarding") frac = 0;
      const key = f.from + "|" + f.to;
      const group = byRoute.get(key) || { from, to, flights: [] };
      group.flights.push({ code, frac, active });
      byRoute.set(key, group);
    });

    byRoute.forEach((g) => {
      const [x1, y1] = g.from, [x2, y2] = g.to;
      const curve = quadPath(x1, y1, x2, y2);
      const active = g.flights.some((fl) => fl.active);
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", curve.d);
      path.setAttribute("class", active ? "air-path" : "air-path faint");
      svg.appendChild(path);

      if (active) {
        g.flights.forEach((fl) => {
          if (!fl.active) return;
          const q = pointOnQuad({ p0: [x1, y1], c: [curve.cx, curve.cy], p2: [x2, y2] }, fl.frac);
          const plane = document.createElement("div");
          plane.className = "air-plane";
          plane.style.left = q.x.toFixed(2) + "%";
          plane.style.top = q.y.toFixed(2) + "%";
          plane.style.transform = `translate(-50%, -50%) rotate(${((q.a * 180) / Math.PI + 90).toFixed(1)}deg)`;
          plane.textContent = `${fl.code} · ${air[fl.code] ?? 0}`;
          map.appendChild(plane);
        });
      }
    });

    const rows = Object.entries(air).map(([code, n]) => {
      const f = flights[code] || {};
      return `<div class="air-row"><span><b>${f.from || "?"} → ${f.to || "?"}</b> ${code} · salida ${f.dep}</span><span>${n} pasajeros</span></div>`;
    });
    $("air-list").innerHTML = rows.length
      ? rows.join("")
      : `<i>No hay vuelos en el aire en este momento</i>`;
  }

  init().catch((e) => {
    document.body.innerHTML =
      `<pre style="padding:30px;white-space:pre-wrap">No se pudo cargar la data.\n\nEsta vista debe servirse por HTTP (no file://).\nProbá:\n  python -m http.server --directory web/dist 8080\n  y abrí http://localhost:8080\n\n${e}</pre>`;
  });
})();