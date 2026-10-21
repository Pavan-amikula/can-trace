"use strict";
const $ = (id) => document.getElementById(id);
let summary,
  source,
  events = [],
  position = 0,
  selected = null,
  alerts = 0,
  running = false;
const titles = {
  overview: [
    "Live forensics",
    "From anomaly to evidence.",
    "Inspect the signal. Trace the decision. Preserve the evidence.",
  ],
  evaluation: [
    "Evaluation",
    "Performance you can verify.",
    "Full captures. Frozen thresholds. Context for every number.",
  ],
  model: [
    "Tensor model",
    "Inside the learned structure.",
    "Compact tensor cores. Explicit contractions. Reproducible scores.",
  ],
  research: [
    "Research & scope",
    "A foundation, with boundaries.",
    "Primary research, public evidence and clear next steps.",
  ],
};
document.querySelectorAll(".nav").forEach((button) =>
  button.addEventListener("click", () => {
    document
      .querySelectorAll(".nav")
      .forEach((b) => b.classList.toggle("active", b === button));
    document
      .querySelectorAll(".view")
      .forEach((v) =>
        v.classList.toggle("hidden", v.id !== button.dataset.view),
      );
    const t = titles[button.dataset.view];
    $("breadcrumb").textContent = t[0];
    $("title").textContent = t[1];
    $("subtitle").textContent = t[2];
    if (button.dataset.view === "model") drawBonds();
  }),
);
function canvas(id) {
  const el = $(id),
    dpr = window.devicePixelRatio || 1,
    rect = el.getBoundingClientRect();
  el.width = rect.width * dpr;
  el.height = rect.height * dpr;
  const c = el.getContext("2d");
  c.scale(dpr, dpr);
  return [c, rect.width, rect.height];
}
function timeline() {
  const [c, w, h] = canvas("timeline");
  if (!summary) return;
  const left = 37,
    top = 15,
    right = w - 15,
    bottom = h - 22;
  const max =
    Math.max(summary.threshold * 1.5, ...events.map((e) => e.score), 0.1) *
    1.15;
  const y = (s) => bottom - (s / max) * (bottom - top),
    x = (i) => left + (i / Math.max(summary.events - 1, 1)) * (right - left);
  c.font = "9px Segoe UI";
  c.lineWidth = 1;
  for (let i = 0; i < 4; i++) {
    const val = (max * i) / 3,
      yy = y(val);
    c.strokeStyle = "#edf2ef";
    c.beginPath();
    c.moveTo(left, yy);
    c.lineTo(right, yy);
    c.stroke();
    c.fillStyle = "#90a29c";
    c.fillText(val.toFixed(2), 2, yy + 3);
  }
  c.setLineDash([4, 4]);
  c.strokeStyle = "#d39054";
  c.beginPath();
  c.moveTo(left, y(summary.threshold));
  c.lineTo(right, y(summary.threshold));
  c.stroke();
  c.setLineDash([]);
  for (let i = 0; i < 5; i++) {
    c.fillStyle = "#91a29d";
    c.fillText(
      Math.round((summary.events * i) / 4).toString(),
      x((summary.events * i) / 4) - 4,
      h - 5,
    );
  }
  if (!events.length) {
    c.fillStyle = "#9aaba5";
    c.font = "11px Segoe UI";
    c.fillText(
      "Awaiting replay · start to score captured traffic",
      left + 35,
      h / 2,
    );
    return;
  }
  c.beginPath();
  events.forEach((e, i) =>
    i ? c.lineTo(x(i), y(e.score)) : c.moveTo(x(i), y(e.score)),
  );
  c.lineTo(x(events.length - 1), bottom);
  c.lineTo(left, bottom);
  c.closePath();
  c.fillStyle = "#0a8b7c0d";
  c.fill();
  c.beginPath();
  events.forEach((e, i) =>
    i ? c.lineTo(x(i), y(e.score)) : c.moveTo(x(i), y(e.score)),
  );
  c.strokeStyle = "#168b7e";
  c.lineWidth = 1.6;
  c.stroke();
  events.forEach((e, i) => {
    if (e.alert) {
      c.fillStyle = "#cf853c";
      c.beginPath();
      c.arc(x(i), y(e.score), 2, 0, Math.PI * 2);
      c.fill();
    }
  });
  if (selected !== null && events[selected]) {
    const e = events[selected];
    c.strokeStyle = "#647f73";
    c.setLineDash([2, 3]);
    c.beginPath();
    c.moveTo(x(selected), top);
    c.lineTo(x(selected), bottom);
    c.stroke();
    c.setLineDash([]);
    c.fillStyle = "#0b6f65";
    c.beginPath();
    c.arc(x(selected), y(e.score), 4, 0, Math.PI * 2);
    c.fill();
  }
}
function stop() {
  if (source) source.close();
  running = false;
  $("play").textContent = "▶ Resume replay";
  $("streamStatus").textContent = "PAUSED";
  $("streamStatus").classList.remove("running");
}
function start() {
  if (!summary) return;
  if (position >= summary.events) reset();
  source = new EventSource(
    `/api/stream?start=${position}&speed=${$("speed").value}`,
  );
  running = true;
  $("play").textContent = "Ⅱ Pause replay";
  $("streamStatus").textContent = "REPLAYING";
  $("streamStatus").classList.add("running");
  source.onmessage = (e) => {
    const item = JSON.parse(e.data);
    if (item.position !== position) return;
    events.push(item);
    position++;
    if (item.alert) alerts++;
    $("windowCount").replaceChildren(
      document.createTextNode(position + " "),
      Object.assign(document.createElement("small"), {
        textContent: `/ ${summary.events}`,
      }),
    );
    $("alertCount").textContent = alerts;
    $("liveCount").textContent = `${position} windows`;
    renderRows();
    timeline();
    if (
      selected === null ||
      (item.ground_truth === 1 && item.alert && selected < position - 10)
    )
      inspect(item.position);
  };
  source.addEventListener("complete", () => {
    stop();
    $("streamStatus").textContent = "COMPLETE";
    $("play").textContent = "↺ Replay again";
  });
  source.onerror = () => {
    stop();
    $("streamStatus").textContent = "CONNECTION PAUSED";
  };
}
function reset() {
  stop();
  events = [];
  position = 0;
  selected = null;
  alerts = 0;
  $("windowCount").textContent = "0";
  $("alertCount").textContent = "0";
  $("liveCount").textContent = "0 windows";
  $("caseContent").classList.add("hidden");
  $("inspectorEmpty").classList.remove("hidden");
  $("caseTitle").textContent = "Inspect a window";
  $("play").textContent = "▶ Start replay";
  $("streamStatus").textContent = "READY";
  renderRows();
  timeline();
}
$("play").addEventListener("click", () => (running ? stop() : start()));
$("reset").addEventListener("click", reset);
$("speed").addEventListener("change", () => {
  if (running) {
    stop();
    start();
  }
});
function cell(row, text, className) {
  const td = document.createElement("td");
  td.textContent = text;
  if (className) td.className = className;
  row.appendChild(td);
  return td;
}
function renderRows() {
  const body = $("trafficRows");
  body.replaceChildren();
  if (!events.length) {
    const tr = document.createElement("tr");
    const td = cell(
      tr,
      "Start replay to receive and score captured CAN traffic.",
      "empty",
    );
    td.colSpan = 6;
    body.appendChild(tr);
    return;
  }
  events
    .slice(-60)
    .reverse()
    .forEach((e) => {
      const tr = document.createElement("tr");
      tr.dataset.position = e.position;
      if (selected === e.position) tr.className = "selected";
      const f = e.frames[e.frames.length - 1];
      cell(tr, "#" + e.index);
      cell(tr, f.can_id);
      cell(tr, f.payload, "hex");
      cell(tr, e.score.toFixed(4));
      const td = cell(tr, "");
      const badge = document.createElement("span");
      badge.className = "decision" + (e.alert ? " alert" : "");
      badge.textContent = e.alert ? "Alert" : "Within threshold";
      td.appendChild(badge);
      cell(
        tr,
        e.ground_truth ? "Attack present" : "Normal",
        "ground" + (e.ground_truth ? " attack" : ""),
      );
      tr.tabIndex = 0;
      tr.setAttribute("aria-label", `Inspect window ${e.index}`);
      tr.addEventListener("click", () => inspect(e.position));
      tr.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter") inspect(e.position);
      });
      body.appendChild(tr);
    });
}
async function inspect(p) {
  selected = p;
  renderRows();
  timeline();
  const response = await fetch(`/api/case/${p}`);
  if (!response.ok) return;
  const bundle = await response.json();
  if (selected !== p) return;
  const e = bundle.case.chain[0].event,
    ex = e.explanation;
  $("inspectorEmpty").classList.add("hidden");
  $("caseContent").classList.remove("hidden");
  $("caseTitle").textContent = "Window #" + e.index;
  $("caseScore").textContent = ex.score.toFixed(4);
  $("caseDecision").textContent = e.alert ? "Alert" : "Within threshold";
  $("caseDecision").className = "decision" + (e.alert ? " alert" : "");
  $("contributions").replaceChildren();
  const top = ex.features.slice(0, 5),
    max = Math.max(...top.map((f) => Math.abs(f.delta)), 1e-6);
  top.forEach((f) => {
    const row = document.createElement("div");
    row.className = "contribution";
    const name = document.createElement("code");
    name.textContent = `t${f.offset < 0 ? f.offset : ""} · ${f.feature}`;
    const bar = document.createElement("meter");
    bar.min = 0;
    bar.max = max;
    bar.value = Math.abs(f.delta);
    bar.title = "Absolute signed score change";
    const v = document.createElement("b");
    v.textContent = (f.delta >= 0 ? "+" : "") + f.delta.toFixed(3);
    row.append(name, bar, v);
    $("contributions").appendChild(row);
  });
  $("frames").replaceChildren();
  e.frames.forEach((f) => {
    const row = document.createElement("div");
    row.className = "frame-row" + (f.label ? " attacked" : "");
    const id = document.createElement("strong");
    id.textContent = f.can_id;
    const hex = document.createElement("code");
    hex.textContent = f.payload;
    const line = document.createElement("span");
    line.textContent = "L" + f.line;
    row.append(id, hex, line);
    $("frames").appendChild(row);
  });
  $("caseHash").textContent = bundle.case_sha256;
  $("export").href = `/api/case/${p}/export`;
  drawHeat(ex.matrix);
}
function drawHeat(matrix) {
  const [c, w, h] = canvas("heatmap");
  const cols = matrix[0].length,
    gap = 2,
    cw = (w - 23) / cols,
    ch = (h - 15) / 4;
  const max = Math.max(...matrix.flat().map(Math.abs), 1e-8);
  c.font = "8px Segoe UI";
  matrix.forEach((row, r) => {
    c.fillStyle = "#81998e";
    c.fillText(r === 3 ? "t" : `−${3 - r}`, 0, r * ch + ch * 0.7);
    row.forEach((v, col) => {
      const alpha = 0.08 + (Math.abs(v) / max) * 0.86;
      c.fillStyle =
        v >= 0 ? `rgba(202,128,63,${alpha})` : `rgba(23,139,122,${alpha})`;
      c.fillRect(22 + col * cw, r * ch + 3, cw - gap, ch - gap);
    });
  });
}
function evaluation() {
  const m = summary.metrics;
  $("protocol").textContent = m.protocol;
  const names = {
    held_out_benign: "Held-out benign",
    physical_injection: "Physical injection",
    derived_masquerade: "Derived masquerade",
  };
  $("evaluationTables").replaceChildren();
  Object.entries(m.results).forEach(([capture, methods]) => {
    const wrap = document.createElement("div");
    const h = document.createElement("h4");
    const first = Object.values(methods)[0];
    h.textContent = `${names[capture]} · ${first.windows.toLocaleString()} windows · ${(first.prevalence * 100).toFixed(3)}% positive`;
    const table = document.createElement("table");
    const head = document.createElement("thead"),
      hr = document.createElement("tr");
    ["MODEL", "AUROC", "AP", "PRECISION", "RECALL", "F1", "FP / 1K"].forEach(
      (t) => {
        const th = document.createElement("th");
        th.textContent = t;
        hr.appendChild(th);
      },
    );
    head.appendChild(hr);
    table.appendChild(head);
    const body = document.createElement("tbody");
    Object.entries(methods).forEach(([name, result]) => {
      const tr = document.createElement("tr");
      cell(tr, name);
      [
        "auroc",
        "average_precision",
        "precision",
        "recall",
        "f1",
        "false_positives_per_1000_normal",
      ].forEach((k) =>
        cell(tr, result[k] === null ? "—" : result[k].toFixed(4)),
      );
      body.appendChild(tr);
    });
    table.appendChild(body);
    wrap.append(h, table);
    $("evaluationTables").appendChild(wrap);
  });
  $("reproducibility").textContent =
    `Independent identical-environment refit: maximum score difference ${m.reproducibility.independent_refit_max_abs_score_difference.toExponential(2)} across ${m.reproducibility.probe_windows} windows. Cross-platform bit identity is not guaranteed.`;
  $("latencyDetail").textContent =
    `Single-window scoring: median ${m.latency.single_window_p50_ms.toFixed(2)} ms, p95 ${m.latency.single_window_p95_ms.toFixed(2)} ms. Excludes parsing, encoding, explanation and network. Software replay is a functional demonstration, not an ECU real-time benchmark.`;
}
function drawBonds() {
  if (!summary) return;
  const [c, w, h] = canvas("bonds"),
    data = summary.metrics.mps.bond_entropies_bits[0];
  c.strokeStyle = "#edf2ef";
  c.font = "9px Segoe UI";
  for (let i = 0; i <= 3; i++) {
    const y = h - 25 - (i * (h - 40)) / 3;
    c.beginPath();
    c.moveTo(25, y);
    c.lineTo(w - 10, y);
    c.stroke();
    c.fillStyle = "#82968c";
    c.fillText(String(i), 4, y + 3);
  }
  c.beginPath();
  data.forEach((v, i) => {
    const x = 25 + (i / (data.length - 1)) * (w - 40),
      y = h - 25 - (v / 3) * (h - 40);
    i ? c.lineTo(x, y) : c.moveTo(x, y);
  });
  c.strokeStyle = "#138f7b";
  c.lineWidth = 2;
  c.stroke();
}
window.addEventListener("resize", () => {
  timeline();
  if (!$("model").classList.contains("hidden")) drawBonds();
  if (selected !== null) inspect(selected);
});
(async () => {
  try {
    const response = await fetch("/api/summary");
    if (!response.ok)
      throw new Error(
        "Setup required: download the pinned samples and run the evaluation. See README for commands.",
      );
    summary = await response.json();
    $("threshold").textContent = summary.threshold.toFixed(4);
    $("latency").textContent =
      summary.metrics.latency.single_window_p95_ms.toFixed(1) + " ms";
    $("bondSpec").textContent =
      summary.metrics.mps.rank +
      " · " +
      summary.metrics.mps.prototypes +
      " IDs";
    $("parameters").textContent =
      summary.metrics.mps.parameters.toLocaleString() + " core parameters";
    $("modelDetails").textContent =
      `${summary.metrics.mps.parameters.toLocaleString()} float64 core parameters · ${(summary.metrics.mps.model_bytes / 1024).toFixed(1)} KiB compressed artifact · same-environment deterministic training order.`;
    evaluation();
    timeline();
  } catch (error) {
    $("setup").textContent = error.message;
    $("setup").classList.remove("hidden");
    $("play").disabled = true;
  }
})();
