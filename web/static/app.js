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
  let report = null;
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

  // ---- theme (light / dark) ----
  const THEME = {
    light: { tick: "#475569", title: "#94a3b8", grid: "rgba(148,163,184,0.25)", muted: "#64748b", muted2: "#94a3b8", fallback: "#64748b", arrow: "#64748b" },
    dark: { tick: "#cbd5e1", title: "#94a3b8", grid: "rgba(148,163,184,0.18)", muted: "#94a3b8", muted2: "#b8c2d4", fallback: "#94a3b8", arrow: "#94a3b8" },
  };
  let dark = (() => { try { return localStorage.getItem("airline-theme") === "dark"; } catch (_) { return false; } })();
  let T = dark ? THEME.dark : THEME.light;

  // Light dashboard defaults for all Chart.js instances (ticks, grid, font).
  if (typeof Chart !== "undefined") {
    Chart.defaults.color = T.tick;
    Chart.defaults.borderColor = T.grid;
    Chart.defaults.font.family =
      'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif';
  }

  const PALETTE = [
    "#2563eb", "#0d9488", "#f59e0b", "#7c3aed",
    "#e11d48", "#0891b2", "#db2777", "#65a30d",
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
    entrance: { label: "Entrada", color: "#16a34a" },
    check_in: { label: "Check-in", color: "#f59e0b" },
    security: { label: "Seguridad", color: "#dc2626" },
    gate: { label: "Puertas", color: "#3b82f6" },
    destination: { label: "Llegadas", color: "#7c3aed" },
    exited: { label: "Salida", color: "#0891b2" },
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

  async function loadDefault() {
    // Preferir el bundle único comprimido {meta, snapshots, report}.
    try {
      const bundle = await readBundleUrl(DATA + "simulation.json.gz");
      return {
        meta: bundle.meta,
        snapshots: bundle.snapshots,
        report: bundle.report || null,
      };
    } catch (_) {
      // Dist legacy sin bundle: cargar los ficheros separados.
      const [m, s] = await Promise.all([
        fetch(DATA + "meta.json").then((r) => r.json()),
        fetch(DATA + "snapshots.json").then((r) => r.json()),
      ]);
      let r = null;
      try {
        const res = await fetch(DATA + "report.json");
        if (res.ok) r = await res.json();
      } catch (_) { /* el informe es opcional */ }
      return { meta: m, snapshots: s, report: r };
    }
  }

  async function init() {
    const loaded = await loadDefault();
    meta = loaded.meta;
    snapshots = loaded.snapshots;
    report = loaded.report;

    $("sim-time").textContent = "00:00";
    $("frame-info").textContent = `1 / ${snapshots.length}`;

    $("axis").textContent =
      `${meta.start.slice(0, 16).replace("T", " ")}  →  ` +
      `${meta.end.slice(0, 16).replace("T", " ")}`;
    $("legend").textContent =
      `${meta.passengers} pasajeros · ${meta.flights} vuelos · ` +
      `${meta.total_events} eventos · 1 min sim. = 1 s real @1x`;

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

    $("btn-theme").addEventListener("click", toggleTheme);
    applyTheme();

    wireLoadBundle();

    setupTabs();
    setupAirportSelect();
    buildAirMap();

    const hashMatch = location.hash.match(/^#([a-z]+)?(?::(\d+))?$/);
    if (hashMatch) {
      if (["airport", "air", "metrics", "report"].includes(hashMatch[1])) selectTab(hashMatch[1]);
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
  // El paso entre snapshots es variable (adaptativo): cada frame debe durar
  // lo proporcional al paso real. 1x = 1 minuto simulado por segundo real.
  function frameMs() {
    let dtMin = FRAME_MS_1X / 1000;
    if (index < snapshots.length - 1) {
      const d = isoMin(snapshots[index + 1].t) - isoMin(snapshots[index].t);
      if (d > 0) dtMin = d;
    }
    return dtMin * 1000 / speedMult;
  }

  function togglePlay() {
    playing = !playing;
    $("btn-play").classList.toggle("is-playing", playing);
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
      $("btn-play").classList.remove("is-playing");
      clearInterval(timer);
      timer = null;
    }
  }

  // ---------- theme ----------
  function applyTheme() {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    T = dark ? THEME.dark : THEME.light;
    const btn = $("btn-theme");
    if (btn) {
      btn.textContent = dark ? "\u263C" : "\u263E";
      btn.title = dark ? "Cambiar a modo claro" : "Cambiar a modo oscuro";
    }
    if (typeof Chart !== "undefined") {
      Chart.defaults.color = T.tick;
      Chart.defaults.borderColor = T.grid;
    }
    if (snapshots) render();
  }

  function toggleTheme() {
    dark = !dark;
    try { localStorage.setItem("airline-theme", dark ? "dark" : "light"); } catch (_) {}
    applyTheme();
  }

  function render() {
    const snap = snapshots[index];
    $("slider").value = index;
    $("frame-info").textContent = `${index + 1} / ${snapshots.length}`;
    $("sim-time").textContent = hhmm(snap.t) + " · " + mmdd(snap.t);

    if (activeTab === "metrics") renderMetrics(snap);
    else if (activeTab === "airport") renderAirport(snap);
    else if (activeTab === "report") renderReport();
    else renderAir(snap);
  }

  // ==================================================================
  // TAB: Informe operativo (report.json del bundle o resumen local)
  // ==================================================================
  function renderReport() {
    const body = $("report-body");
    const r = report || buildClientReport();
    if (!r) { body.innerHTML = `<i>Informe no disponible.</i>`; return; }
    body.innerHTML = reportSections(r, !!report);
  }

  function buildClientReport() {
    if (!snapshots || !snapshots.length) return null;
    const last = snapshots[snapshots.length - 1];
    const m = last.metrics || {};
    const op = m.operational || {};
    const flights = Object.values(op.flight || {});
    const total = (op.boarded || 0) + (op.missed || 0);
    return {
      meta: {
        title: meta.title, start: meta.start && meta.start.slice(11, 16),
        end: meta.end && meta.end.slice(11, 16),
        passengers: meta.passengers, flights: meta.flights,
        airports: meta.airports, events: meta.total_events,
      },
      resumen: {
        boarded: op.boarded || 0, missed: op.missed || 0,
        missed_rate: total ? (op.missed || 0) / total : 0,
        completed: op.completed || 0, avg_origin_min: op.avg_origin_min || 0,
        on_time_rate: op.on_time_rate || 0, load_factor_avg: op.load_factor_avg || 0,
        boarding_avg_stress: (m.stress || {}).boarding_avg || 0,
        high_pressure_pct: (m.stress || {}).high_pressure_pct || 0,
      },
      colas: { security: queueRows(m.security), checkin: queueRows(m.checkin) },
      experiencia: Object.assign({}, (m.stress || {}), { avg_baggage_wait_s: 0 }),
      cohortes: Object.entries(m.cohorts || {}).map(([purpose, c]) =>
        Object.assign({ purpose }, c)),
      vuelos: flights.sort((a, b) => (a.dep || "").localeCompare(b.dep || "")).map((f) => ({
        flight: f.flight, origin: f.origin || "?", destination: f.destination || "?",
        dep: f.dep || "", sched_arr: f.arr || "", capacity: f.capacity || 0,
        load_factor: f.load_factor || 0, boarded: f.boarded || 0, missed: f.missed || 0,
        on_time: f.on_time !== false, delay_min: f.delay_min || 0,
      })),
      heatmap: { security: heatRows(m.security), checkin: heatRows(m.checkin) },
      _local: true,
    };
  }

  function queueRows(data) {
    const rows = [];
    Object.keys(data || {}).sort().forEach((code) => {
      const s = data[code];
      if (!s.processed) return;
      rows.push({
        airport: code, processed: s.processed, wait_avg_s: s.wait_avg_s || 0,
        wait_p90_s: s.wait_p90_s || 0, wait_max_s: s.wait_max_s || 0,
        congested_pct: s.congested_pct || 0,
        peak_hour: peakHour(s.hours),
      });
    });
    rows.sort((a, b) => (b.wait_p90_s || 0) - (a.wait_p90_s || 0));
    return rows;
  }

  function peakHour(hours) {
    if (!hours) return null;
    const keys = Object.keys(hours);
    if (!keys.length) return null;
    let best = keys[0];
    keys.forEach((k) => { if ((hours[k].wait_avg_s || 0) > (hours[best].wait_avg_s || 0)) best = k; });
    return best;
  }

  function heatRows(data) {
    const out = {};
    Object.keys(data || {}).forEach((code) => {
      const hours = (data[code].hours || {});
      const pairs = Object.keys(hours).map((h) => [Number(h), hours[h].wait_avg_s || 0]).sort((a, b) => a[0] - b[0]);
      if (pairs.length) out[code] = pairs;
    });
    return out;
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function reportSections(r, fromBundle) {
    const metaInfo = r.meta || {};
    const res = r.resumen || {};
    const exp = r.experiencia || {};
    const sec = (r.colas || {}).security || [];
    const ck = (r.colas || {}).checkin || [];

    const pct = (v) => (v == null ? "0" : Math.round(Number(v))) + "%";

    const queueTable = (rows) =>
      `<table class="report-table"><thead><tr><th>Aeropuerto</th><th>Procesados</th><th>Espera media</th><th>P90</th><th>Máx</th><th>Congestión</th><th>Hora pico</th></tr></thead><tbody>` +
      rows.map((q) =>
        `<tr><td>${esc(q.airport)}</td><td>${q.processed.toLocaleString()}</td><td>${Math.round(q.wait_avg_s)}s</td>` +
        `<td>${Math.round(q.wait_p90_s)}s</td><td>${Math.round(q.wait_max_s)}s</td>` +
        `<td>${pct(q.congested_pct)}</td><td>${q.peak_hour ? q.peak_hour + "h" : "—"}</td></tr>`).join("") +
      `</tbody></table>`;

    const heatmap = (hm) => {
      const hrs = [];
      Object.keys(hm || {}).forEach((code) => { hm[code].forEach(([h]) => { if (!hrs.includes(h)) hrs.push(h); }); });
      hrs.sort((a, b) => a - b);
      if (!hrs.length) return `<i>sin datos</i>`;
      const cell = (code, h) => {
        const pair = (hm[code] || []).find(([x]) => x === h);
        const v = pair ? pair[1] : 0;
        const alpha = Math.min(0.9, v / 600);
        return `<div class="hm-cell" style="--hm:${alpha}">${Math.round(v)}</div>`;
      };
      return `<div class="hm-grid hm-head"><div></div>` +
        hrs.map((h) => `<div class="hm-head">${h}h</div>`).join("") + `</div>` +
        Object.keys(hm).sort().map((code) =>
          `<div class="hm-grid"><div class="hm-apt">${esc(code)}</div>` +
          hrs.map((h) => cell(code, h)).join("") + `</div>`).join("");
    };

    const secCount = Math.max(sec.length, ck.length);

    let html = "";
    if (fromBundle) {
      html += `<div class="report-badge">Informe generado por el backend</div>`;
    } else {
      html += `<div class="report-badge alt">Resumen calculado en el navegador (cargá un bundle con report.json para el informe completo)</div>`;
    }
    html += `<div class="counters report-counters">
      <div class="counter"><div class="num">${res.boarded || 0}</div><div class="lbl">Embarcados</div></div>
      <div class="counter"><div class="num" style="color:#ef4444">${res.missed || 0}</div><div class="lbl">Perdieron vuelo</div></div>
      <div class="counter"><div class="num" style="color:#16a34a">${pct(res.on_time_rate)}</div><div class="lbl">Puntualidad</div></div>
      <div class="counter"><div class="num" style="color:#2563eb">${pct(res.load_factor_avg)}</div><div class="lbl">Load factor medio</div></div>
      <div class="counter"><div class="num">${res.avg_origin_min ?? 0}min</div><div class="lbl">Origen → puerta</div></div>
    </div>`;
    html += `<p class="report-sub">${esc(metaInfo.date || "")} · ${esc(metaInfo.start || "")}–${esc(metaInfo.end || "")} · ` +
      `${(metaInfo.passengers ?? 0).toLocaleString()} pasajeros · ${metaInfo.flights || 0} vuelos · ` +
      `${(metaInfo.events ?? 0).toLocaleString()} eventos</p>`;

    html += `<section class="report-block"><h3>Colas de seguridad (espera, segundos)</h3>${queueTable(sec)}</section>`;
    if (secCount > 0) html += `<section class="report-block"><h3>Colas de check-in (espera, segundos)</h3>${queueTable(ck)}</section>`;

    html += `<section class="report-block"><h3>Experiencia</h3><div class="report-kpis">` +
      `<div><b>${exp.boarding_avg ?? 0}</b><span>estrés medio embarque</span></div>` +
      `<div><b>${pct(exp.boarding_stressed_pct)}</b><span>estresados (&gt;60)</span></div>` +
      `<div><b>${pct(exp.high_pressure_pct)}</b><span>esperas con presión alta</span></div>` +
      `<div><b>${Math.round(exp.avg_baggage_wait_s || 0)}s</b><span>espera maletas media</span></div>` +
      `</div></section>`;

    if (r.cohortes && r.cohortes.length) {
      html += `<section class="report-block"><h3>Cohortes por motivo de viaje</h3><table class="report-table"><thead>
        <tr><th>Motivo</th><th>Embarcados</th><th>Perdidos</th><th>Miss rate</th><th>Espera media</th><th>Estrés</th></tr></thead><tbody>` +
        r.cohortes.map((c) =>
          `<tr><td>${esc(c.purpose)}</td><td>${c.boarded || 0}</td><td>${c.missed || 0}</td>` +
          `<td>${pct((c.missed_rate || 0) * 100)}</td><td>${Math.round(c.avg_wait || 0)}s</td>` +
          `<td>${Math.round(c.avg_stress || 0)}</td></tr>`).join("") + `</tbody></table></section>`;
    }

    if (r.vuelos && r.vuelos.length) {
      html += `<section class="report-block"><h3>Vuelos (${r.vuelos.length})</h3><div class="report-table-wrap"><table class="report-table"><thead>
        <tr><th>Vuelo</th><th>Ruta</th><th>Salida</th><th>Llegada</th><th>Capac.</th><th>Load</th><th>Embarcados</th><th>Perdidos</th><th>Puntual</th><th>Retraso</th></tr></thead><tbody>` +
        r.vuelos.map((v) =>
          `<tr><td class="mono">${esc(v.flight)}</td><td>${esc(v.origin)}→${esc(v.destination)}</td><td>${esc(v.dep)}</td>` +
          `<td>${esc(v.sched_arr)}</td><td>${v.capacity}</td><td>${pct(v.load_factor)}</td>` +
          `<td>${v.boarded || 0}</td><td>${v.missed || 0}</td>` +
          `<td><span class="pill ${v.on_time ? "ok" : "bad"}">${v.on_time ? "Sí" : "No"}</span></td>` +
          `<td>${v.delay_min || 0}m</td></tr>`).join("") + `</tbody></table></div></section>`;
    }

    html += `<section class="report-block"><h3>Heatmap de espera media por aeropuerto y hora (segundos)</h3><h4>Seguridad</h4>${heatmap((r.heatmap || {}).security)}` +
      `<h4>Check-in</h4>${heatmap((r.heatmap || {}).checkin)}</section>`;
    return html;
  }

  // ==================================================================
  // Cargar simulaciones (bundle {meta, snapshots, report} o .json.gz)
  // ==================================================================
  function tryJson(text) {
    try { return JSON.parse(text); } catch (_) { return null; }
  }

  async function readBundleUrl(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error("HTTP " + res.status + " para " + url);
    const bytes = new Uint8Array(await res.arrayBuffer());
    let parsed = tryJson(new TextDecoder().decode(bytes));
    if (parsed === null) {
      // No era JSON directo (p. ej. .gz) o el CDN lo sirvió ya sin
      // descomprimir: intentar gzip, tolerante a la extensión / encodings.
      const ds = new DecompressionStream("gzip");
      const stream = new Response(bytes).body.pipeThrough(ds);
      const text = await new Response(stream).text();
      parsed = tryJson(text);
    }
    if (parsed === null) throw new Error("Bundle no es JSON válido");
    return parsed;
  }

  function resetAll() {
    Object.keys(charts).forEach((k) => { try { charts[k].destroy(); } catch (_) {} });
    Object.keys(charts).forEach((k) => delete charts[k]);
    [opChart, stressChart, flightChart, cohortChart].forEach((c) => { if (c) { try { c.destroy(); } catch (_) {} } });
    opChart = stressChart = flightChart = cohortChart = null;
    Object.keys(_queueCodesCache).forEach((k) => delete _queueCodesCache[k]);
    playing = false; clearInterval(timer); timer = null;
    $("btn-play").classList.remove("is-playing");
  }

  function applyBundle(bundle) {
    if (bundle == null || !bundle.meta || !Array.isArray(bundle.snapshots) || !bundle.snapshots.length) {
      throw new Error("Bundle inválido: faltan meta o snapshots");
    }
    resetAll();
    meta = bundle.meta;
    snapshots = bundle.snapshots;
    report = bundle.report || null;
    index = 0;

    $("sim-time").textContent = "00:00";
    $("frame-info").textContent = `1 / ${snapshots.length}`;
    $("axis").textContent =
      `${meta.start.slice(0, 16).replace("T", " ")}  →  ` +
      `${meta.end.slice(0, 16).replace("T", " ")}`;
    $("legend").textContent =
      `${meta.passengers} pasajeros · ${meta.flights} vuelos · ` +
      `${meta.total_events} eventos · 1 min sim. = 1 s real @1x`;

    const slider = $("slider");
    slider.max = snapshots.length - 1;
    slider.value = 0;

    const sel = $("airport-select");
    sel.innerHTML = "";
    const codes = Object.keys(meta.layouts || {}).sort();
    codes.forEach((code) => {
      const opt = document.createElement("option");
      opt.value = code;
      opt.textContent = code;
      sel.appendChild(opt);
    });
    selectedAirport = codes.includes("JFK") ? "JFK" : (codes[0] || null);
    sel.value = selectedAirport || "";
    sel.style.display = codes.length ? "" : "none";

    const map = $("air-map");
    map.innerHTML = "";
    buildAirMap();

    render();
    if (activeTab === "report") renderReport();
  }

  async function loadBundleFromFile(file) {
    const bytes = new Uint8Array(await file.arrayBuffer());
    let parsed = tryJson(new TextDecoder().decode(bytes));
    if (parsed === null) {
      const ds = new DecompressionStream("gzip");
      const stream = new Response(bytes).body.pipeThrough(ds);
      const text = await new Response(stream).text();
      parsed = tryJson(text);
    }
    if (parsed === null) throw new Error("Bundle no es JSON válido");
    applyBundle(parsed);
  }

  function wireLoadBundle() {
    const fileInput = $("file-input");
    $("btn-load").addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", () => {
      if (fileInput.files && fileInput.files[0]) loadBundleFromFile(fileInput.files[0]).catch(showLoadError);
      fileInput.value = "";
    });

    let dragDepth = 0;
    document.addEventListener("dragenter", (e) => { e.preventDefault(); dragDepth += 1; document.body.classList.add("dropping"); });
    document.addEventListener("dragleave", (e) => { e.preventDefault(); dragDepth -= 1; if (dragDepth <= 0) { dragDepth = 0; document.body.classList.remove("dropping"); } });
    document.addEventListener("dragover", (e) => e.preventDefault());
    document.addEventListener("drop", (e) => {
      e.preventDefault(); dragDepth = 0; document.body.classList.remove("dropping");
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        loadBundleFromFile(e.dataTransfer.files[0]).catch(showLoadError);
      }
    });

    window.addEventListener("message", (e) => {
      const msg = e.data;
      if (msg && msg.type === "airline.bundle" && typeof msg.url === "string") {
        readBundleUrl(msg.url).then(applyBundle).catch(showLoadError);
      }
    });
  }

  function showLoadError(err) {
    console.error(err);
    alert("No se pudo cargar la simulación: " + (err && err.message ? err.message : err));
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
      ["En el aire", air, "#2563eb"],
      ["En aeropuerto de origen", origin, "#f59e0b"],
      ["En destino", dest, "#7c3aed"],
      ["Salieron", exited, "#16a34a"],
      ["Yendo al aeropuerto", toAirport, T.muted],
      ["En casa", home, T.muted2],
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
          { label: "Espera media (s)", data: wait, yAxisID: "y", backgroundColor: "#3b82f6" },
          { label: "% congestión", data: congest, yAxisID: "y1", backgroundColor: "#ef4444" },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: T.tick } } },
        scales: {
          x: { ticks: { color: T.tick } },
          y: { position: "left", title: { display: true, text: "segundos", color: T.title }, ticks: { color: T.tick }, beginAtZero: true },
          y1: { position: "right", min: 0, max: 100, title: { display: true, text: "%", color: T.title }, grid: { drawOnChartArea: false }, ticks: { color: T.tick } },
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
        plugins: { legend: { labels: { color: T.tick, boxWidth: 12 } } },
        scales: {
          x: { ticks: { color: T.title, maxRotation: 0, autoSkip: true, maxTicksLimit: 12 } },
          y: { beginAtZero: true, title: { display: true, text: yAxisText, color: T.title }, ticks: { color: T.tick } },
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
    const colors = ["#3b82f6", "#ef4444", "#f59e0b"];
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
            color: T.tick,
          },
        },
        scales: {
          y: { beginAtZero: true, title: { display: true, text: "promedio / %", color: T.title }, ticks: { color: T.tick } },
          x: { ticks: { color: T.tick, fontSize: 11 } },
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
          { label: "Embarcados", data: boarded, backgroundColor: "#16a34a" },
          { label: "Perdidos", data: missed, backgroundColor: "#ef4444" },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: T.tick } } },
        scales: {
          x: { ticks: { color: T.tick } },
          y: { beginAtZero: true, title: { display: true, text: "pasajeros", color: T.title }, ticks: { color: T.tick } },
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
          { label: "% perdieron vuelo", data: missedRate, yAxisID: "y", backgroundColor: "#ef4444" },
          { label: "Estrés medio", data: avgStress, yAxisID: "y1", backgroundColor: "#3b82f6" },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: T.tick } } },
        scales: {
          x: { ticks: { color: T.tick } },
          y: { position: "left", min: 0, max: 100, title: { display: true, text: "%", color: T.title }, ticks: { color: T.tick } },
          y1: { position: "right", min: 0, max: 100, title: { display: true, text: "estrés", color: T.title }, grid: { drawOnChartArea: false }, ticks: { color: T.tick } },
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
        datasets: [{ data: [boarded, missed], backgroundColor: ["#16a34a", "#ef4444"] }],
      },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: "55%",
        plugins: {
          legend: { labels: { color: T.tick } },
          title: {
            display: true,
            text: `Embarcados ${boarded} · Perdidos ${missed} · ${completed} en origen · prom ${avg} min en aeropuerto`,
            color: T.tick,
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
    path.setAttribute("fill", T.arrow);
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
      const color = (ZONE_STYLE[pt.zone] || {}).color || T.fallback;
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