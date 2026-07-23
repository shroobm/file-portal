// S34 — the Room surface: the Control Room's operations dashboard, graduated from the
// Claude-Design merge (prototypes/control-panel/control-room/). Framework-free, same idiom
// as main.js. PROJECTION ONLY: every value here is read from an existing invoke() command
// (or the new read-only room_metrics/gpu_vram); the Room owns no state and writes nothing
// except through the same intent-writing commands the Dock already uses.
//
// The source object's `renderVals()` computed a view-model from a simulation; this rebuilds
// the same view-model shape from real commands. The markup below is the lifted Room markup.

const { invoke } = window.__TAURI__.core;

// Verdict → token color, shared with the Dock's assay language (docs/13: terracotta = fail only).
const VCOL = { pass: "var(--ok)", flag: "var(--warn)", fail: "var(--clay)" };
const VBG = { pass: "var(--ok-bg)", flag: "var(--warn-bg)", fail: "var(--clay-bg)" };
const VSYM = { pass: "✓", flag: "⚠", fail: "✕" };
const TAGCOL = {
  intake: "var(--flow)", convert: "var(--text)", gate: "var(--warn)",
  analyst: "var(--flow)", audit: "var(--clay)", ship: "var(--ok)", vault: "var(--ok)",
};
const MODE_LABELS = { ask: "ask", local: "auto-🔒", gemini: "auto-☁", off: "off" };

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const words = (s, n) => String(s ?? "").split(/\s+/).filter(Boolean).slice(0, n).join(" ");
const etaText = (s) => (s == null ? "—" : s < 90 ? `${s}s` : `${Math.round(s / 60)}m`);
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

let roomEl = null;
let active = false;
let pollT = 0;
let deps = {}; // { setStatus, dbg, getWindow, LogicalSize }
// cross-surface bits the Dock owns; the Room mirrors them so a click here matches a click there
let gateMode = "off";
let surface = "room"; // "room" | "wall" — the density this module is rendering

// the canvas transit belt (S35): an AMBIENT activity projection. Chip count/tint reflect real
// in-flight work (drop_waiting / converting / gate / held); empty when the watcher is down. It
// invents no traffic — it visualises the line's real state. Reduced-motion → static.
const belt = { canvas: null, chips: [], raf: 0, running: false, W: 0, H: 0, DPR: 1, pal: {}, reduce: false, targetN: 0, tints: [] };

// S38: GPU telemetry rolling window (docs/16 §8 #4). The poll IS the sampler — each gatherVM()
// does one nvidia-smi read (via gpu_vram) and we accumulate the VRAM %used here into a bounded
// ring for the Room's sparkline. No always-on backend thread: sampling happens only while the
// Room/Wall is being viewed (you can't see the sparkline with the Room closed anyway).
const VRAM_HIST_MAX = 48;
const vramHist = []; // recent VRAM %used samples (0..100), oldest → newest
function sampleVram(v) {
  if (!v || !v.total) return; // no probe → no fake sample (keeps the trend honest)
  vramHist.push((v.used / v.total) * 100);
  if (vramHist.length > VRAM_HIST_MAX) vramHist.shift();
}

// System verdict (shared by the Room header + the Wall): terracotta only when your hand is
// required (a pending gate decision or an audit fail); green when viable; grey when paused.
function systemVerdict(d) {
  const gateN = (d.pf || []).length;
  const av = d.assay?.verdict;
  const w = d.watcher?.state === "running";
  if (!w) return { word: "paused", color: "var(--text-3)" };
  if (av === "fail" || gateN > 0) return { word: "attention", color: "var(--clay)" };
  return { word: "viable", color: "var(--ok)" };
}

// ---- data gathering: assemble the view-model from real commands --------------------------
async function gatherVM() {
  const call = async (name, args) => {
    try { return await invoke(name, args); }
    catch (e) { deps.dbg?.(`room ${name}: ${e}`); return null; }
  };
  const [ls, assay, shift, pf, watcher, vault, metrics, vram] = await Promise.all([
    call("line_state"), call("assay_status"), call("shift_summary"),
    call("preflight_list"), call("watcher_status"), call("vault_check"),
    call("room_metrics"), call("gpu_vram"),
  ]);
  try { gateMode = (await invoke("analyst_mode_get")) || gateMode; } catch { /* keep */ }
  sampleVram(vram); // append this poll's VRAM reading to the rolling window (S38)
  return { ls, assay, shift, pf: pf || [], watcher, vault, metrics, vram };
}

// ---- render -------------------------------------------------------------------------------
function stationRail(d) {
  const ls = d.ls || {}, assay = d.assay || {}, m = d.metrics || {};
  const converting = !!ls.converting;
  const gateN = d.pf.length;
  const av = assay.verdict || null;
  const defs = [
    { seg: "intake", glyph: "▚", name: "Intake", count: String(ls.drop_waiting ?? 0),
      sub: d.watcher?.state === "running" ? "watching" : "paused", st: (ls.drop_waiting > 0) ? "active" : "" },
    { seg: "convert", glyph: "⚙", name: "Convert", count: converting ? "1" : "0",
      sub: converting ? (ls.converting_eta_s != null ? etaText(ls.converting_eta_s) + " left" : "running") : "idle",
      st: converting ? "active" : "" },
    { seg: "gate", glyph: "✳", name: "Gate", count: gateN > 0 ? String(gateN) : "0",
      sub: gateN > 0 ? "waiting" : (MODE_LABELS[gateMode] || gateMode), st: gateN > 0 ? "attn" : "" },
    { seg: "assay", glyph: "◎", name: "Assay",
      count: av === "pass" ? Number(assay.doc_survival ?? 0).toFixed(2) : (av || "—"),
      sub: "survival", st: av },
    { seg: "ship", glyph: "⇈", name: "Ship", count: "—",
      sub: ls.last_shipped?.bundle ? shortName(ls.last_shipped.bundle) : "—", st: "" },
    { seg: "vault", glyph: "▤", name: "Vault", count: String(m.vault_count ?? "—"),
      sub: "Library", st: "done" },
  ];
  return `<div class="room-line">${defs.map((x, i) => {
    const active = x.st === "active", done = x.st === "done", attn = x.st === "attn";
    const verd = ["pass", "flag", "fail"].includes(x.st) ? x.st : null;
    const accent = (attn || active) ? "var(--clay)" : done ? "var(--ok)" : verd ? VCOL[verd] : "var(--text-2)";
    const glyphBg = (active || attn || verd === "fail") ? "var(--clay-bg)" : verd === "pass" ? "var(--ok-bg)" : "var(--surface-2)";
    const border = (active || attn) ? "var(--clay)" : done ? "rgba(111,191,115,.4)" : verd ? VCOL[verd] : "var(--border)";
    const pulse = verd === "fail" ? "assay-pulse 1.7s ease-in-out infinite" : "none";
    const countCol = attn ? "var(--clay)" : "var(--text)";
    const subCol = attn ? "var(--clay)" : active ? "var(--ok)" : verd ? VCOL[verd] : "var(--text-3)";
    return (i ? `<span class="rl-sep">·</span>` : "") +
      `<button class="rl-st" data-seg="${x.seg}" title="${x.name}">` +
      `<span class="rl-glyph" style="color:${accent};background:${glyphBg};border-color:${border};animation:${pulse}">${x.glyph}</span>` +
      `<span class="rl-name">${x.name}</span>` +
      `<span class="rl-count" style="color:${countCol}">${x.count}</span>` +
      `<span class="rl-sub" style="color:${subCol}">${esc(x.sub)}</span></button>`;
  }).join("")}</div>`;
}

function shortName(s) {
  return String(s || "").replace(/\.pdf$/i, "").replace(/--[0-9a-f]{6,}$/, "").replace(/_/g, " ").slice(0, 22);
}

// domain?: { min, max } draws on a FIXED scale (S38: VRAM uses 0..100 so height means true
// fullness — idle sits low, a convert spikes). Omit it to autoscale min..max (throughput/median).
function sparkSvg(series, col, domain) {
  if (!series || series.length < 2) return "";
  const w = 66, h = 22;
  const mn = domain ? domain.min : Math.min(...series);
  const mx = domain ? domain.max : Math.max(...series);
  const r = (mx - mn) || 1;
  const pts = series.map((v, i) => `${((i / (series.length - 1)) * w).toFixed(1)},${(h - 2 - clamp((v - mn) / r, 0, 1) * (h - 4)).toFixed(1)}`).join(" ");
  const [lx, ly] = pts.split(" ").pop().split(",");
  return `<svg class="rk-spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">` +
    `<polyline points="${pts}" fill="none" stroke="${col}" stroke-width="1.5"/>` +
    `<circle cx="${lx}" cy="${ly}" r="1.8" fill="${col}"/></svg>`;
}

function gauge(pct, col) {
  return `<div class="rk-gauge"><i style="width:${clamp(pct, 0, 100)}%;background:${col}"></i></div>`;
}

function kpiTiles(d) {
  const ls = d.ls || {}, m = d.metrics || {}, sh = d.shift?.today || {}, v = d.vram;
  const gateN = d.pf.length;
  const queue = (ls.drop_waiting ?? 0) + gateN;
  const vramUsed = v && v.total ? v.used : null;
  const vramPct = v && v.total ? (v.used / v.total) * 100 : 0;
  const surv = m.survival_avg;
  const survPct = surv != null ? Math.round(surv * 100) : 0;
  const survCol = surv == null ? "var(--text-3)" : surv >= 0.9 ? "var(--ok)" : surv >= 0.75 ? "var(--warn)" : "var(--clay)";
  const tiles = [
    { label: "Throughput", val: m.throughput_pp_s != null ? Number(m.throughput_pp_s).toFixed(1) : "—", unit: "pp/s",
      extra: sparkSvg(m.spp_series && m.spp_series.map((x) => 1 / x), "var(--ok)") },
    { label: "Median s/page", val: m.median_spp != null ? Number(m.median_spp).toFixed(1) : "—", unit: "",
      extra: sparkSvg(m.spp_series, "var(--flow)") },
    { label: "GPU VRAM", val: vramUsed != null ? Number(vramUsed).toFixed(1) : "—", unit: v?.total ? `/${v.total} GB` : "GB",
      // S38: rolling sparkline (fixed 0..100% scale) once ≥2 samples; gauge is the first-poll
      // fallback; clay stroke when the card is under pressure (>92%), else flow.
      extra: v?.total
        ? (sparkSvg(vramHist, vramPct > 92 ? "var(--clay)" : "var(--flow)", { min: 0, max: 100 }) || gauge(vramPct, vramPct > 92 ? "var(--clay)" : "var(--flow)"))
        : `<span class="rk-note">no GPU probe</span>` },
    { label: "Queue depth", val: String(queue), unit: "", extra: `<span class="rk-note">${queue ? queue + " waiting" : "clear"}</span>` },
    { label: "Survival avg", val: surv != null ? Number(surv).toFixed(2) : "—", unit: "", extra: gauge(survPct, survCol) },
    { label: "Shipped today", val: String(sh.shipped ?? 0), unit: "", extra: `<span class="rk-note">${sh.converted ?? 0} converted · ${sh.failed ?? 0} held</span>` },
  ];
  return `<div class="room-kpis">${tiles.map((t) =>
    `<div class="rk"><div class="rk-label">${t.label}</div>` +
    `<div class="rk-val">${t.val}<span class="rk-unit">${t.unit}</span></div>` +
    `<div class="rk-extra">${t.extra || ""}</div></div>`).join("")}</div>`;
}

function convertPanel(d) {
  const ls = d.ls || {}, v = d.vram;
  const converting = !!ls.converting;
  const name = converting ? ls.converting : (ls.last_shipped?.bundle || "line idle");
  const eta = converting ? (ls.converting_eta_s != null ? etaText(ls.converting_eta_s) + " left" : "running") : "idle";
  const vram = v && v.total ? `${Number(v.used).toFixed(1)} GB` : "—";
  const state = converting ? "RUNNING" : "IDLE";
  const stateCol = converting ? "var(--ok)" : "var(--text-3)";
  // Live progress from measured data (S37): elapsed / (elapsed + estimated-remaining). Capped at
  // 95% until the 'converted' event actually fires — it's an ETA-based estimate, kept honest.
  const el = ls.convert_elapsed_s, rem = ls.converting_eta_s;
  let pct = converting ? 6 : 100;
  if (converting && el != null && rem != null && el + rem > 0) pct = Math.min(95, Math.round(el / (el + rem) * 100));
  const elapsedTxt = converting && el != null ? etaText(el) + " elapsed" : "";
  return `<div class="rp"><div class="rp-head"><span class="rp-title">⚙ Convert station</span>` +
    `<span class="rp-state" style="color:${stateCol}">${state}${converting ? " · " + pct + "%" : ""}</span></div>` +
    `<div class="rp-body"><div class="rp-name">${esc(shortName(name) || name)}</div>` +
    `<div class="rp-bar${converting ? " live" : ""}"><i style="width:${pct}%;background:${converting ? "var(--clay)" : "var(--border-strong)"}"></i></div>` +
    `<div class="rp-grid">` +
    `<span>eta</span><b>${eta}</b>` +
    `<span>elapsed</span><b>${elapsedTxt || "—"}</b>` +
    `<span>engine</span><b>marker · batch 32</b>` +
    `<span>VRAM</span><b>${vram}</b>` +
    `</div><div class="rp-note">progress = elapsed ÷ measured ETA (per-page %: converter installment)</div></div></div>`;
}

function assayPanel(d) {
  const a = d.assay;
  if (!a || !a.available) return `<div class="rp"><div class="rp-head"><span class="rp-title">◎ Survival Audit</span></div><div class="rp-body"><div class="rp-note">no audit yet</div></div></div>`;
  const av = a.verdict, col = VCOL[av] || "var(--text-3)";
  const held = a.held || [];
  const pct = a.doc_survival != null ? Math.round(Number(a.doc_survival) * 100) : 100;
  const mode = a.mode || "report";
  const zones = a.zones || [], runs = a.runs || [], mdLines = a.md_lines || 0;
  let map = "";
  if (a.degeneration && zones.length && mdLines) {
    const bands = zones.map((z) => {
      const left = clamp((z.line / mdLines) * 100, 0, 94);
      const w = clamp(((z.chars || 0) / (mdLines * 45)) * 100, 2, 8);
      return `<span class="z degen" style="left:${left.toFixed(1)}%;width:${w.toFixed(1)}%"></span>`;
    }).join("");
    map = `<div class="ac-caption"><b>degeneration</b> — ${zones.length} loop zone(s) · ${esc(a.kind)} lane</div><div class="ac-map">${bands}</div>`;
  } else if (runs.length && a.pages_scored) {
    const bands = runs.slice(0, 40).map((r) =>
      `<span class="z run" style="left:${clamp((r.page || 0) / a.pages_scored * 100, 0, 98).toFixed(1)}%;width:1.5%"></span>`).join("");
    map = `<div class="ac-caption">${runs.length} omission run(s) · ${esc(a.kind)} lane</div><div class="ac-map">${bands}</div>`;
  }
  let list = "";
  if (a.degeneration && zones.length) {
    list = "<ul class=\"ac-runs\">" + zones.slice(0, 3).map((z) =>
      `<li><span class="k">${Number(z.chars || 0).toLocaleString()} ch</span> · tri×${z.max_trigram} · <q>"${esc(words(z.excerpt, 6))}…"</q></li>`).join("") + "</ul>";
  } else if (runs.length) {
    list = "<ul class=\"ac-runs\">" + runs.slice(0, 3).map((r) =>
      `<li><span class="k">p${r.page}</span> · ${r.words} words · <q>"${esc(words(r.excerpt, 6))}…"</q></li>`).join("") + "</ul>";
  }
  const foot = (av === "fail" || held.length)
    ? `<div class="ac-foot"><button class="ac-remedy" data-src="${esc(a.bundle)}">⟳ re-convert</button><span class="ac-swapnote">swap: <b>manual</b> — supersede pending</span></div>` : "";
  const heldHtml = held.length
    ? `<div class="ac-held">held: <b>${held.length}</b> awaiting remedy — ${held.slice(0, 2).map((h) => esc(h.bundle)).join(", ")}</div>` : "";
  const toggle = `<button class="rp-lever" id="room-audit-toggle" title="enforce parks a fail in held/">` +
    `<span class="${mode === "report" ? "on" : "off"}">report</span> ⇄ <span class="${mode === "enforce" ? "on" : "off"}">enforce</span></button>`;
  return `<div class="rp ${av === "fail" ? "fail" : ""}"><div class="rp-head"><span class="rp-title">◎ Survival Audit</span><span class="rp-grow"></span>${toggle}</div>` +
    `<div class="rp-body"><div class="ac-verdict"><span class="nm">${esc(shortName(a.bundle) || "last convert")}</span>` +
    `<span class="meter"><i style="width:${pct}%;background:${col}"></i></span>` +
    `<span class="badge" style="color:${col}">${av} ${VSYM[av] || ""}</span></div>` +
    `<div class="ac-caption">survival <b>${a.doc_survival != null ? Number(a.doc_survival).toFixed(3) : "—"}</b></div>` +
    map + list + foot + `</div>${heldHtml}</div>`;
}

function eventsPanel(d) {
  const tail = (d.shift?.tail || []).slice().reverse();
  const rows = tail.slice(0, 12).map((e) => {
    const ts = String(e.ts || "").slice(11, 19);
    const tag = e.stage || e.tag || "";
    const msg = e.msg || eventMsg(e);
    return `<div class="rev"><span class="rev-ts">${ts}</span><span class="rev-tag" style="color:${TAGCOL[tag] || "var(--text-2)"}">${esc(tag)}</span><span class="rev-msg">${esc(msg)}</span></div>`;
  }).join("");
  return `<div class="rp rp-events"><div class="rp-head"><span class="rp-title">Event stream</span><span class="rp-grow"></span><span class="rp-file">events.jsonl</span></div>` +
    `<div class="rp-body">${rows || `<div class="rp-note">no events yet</div>`}</div></div>`;
}

// turn a raw event line into a human phrase (mirrors main.js tickerPhrase, compacted)
function eventMsg(e) {
  const s = (v) => String(v ?? "").slice(0, 34);
  const k = `${e.stage}/${e.event}`;
  const map = {
    "intake/detected": `${s(e.source)} — on the belt`,
    "convert/probe": `probing ${s(e.source)} — ${e.pages}pp ${e.lane}`,
    "convert/converted": `converted ${s(e.source)} in ${Math.round(e.wall_s || 0)}s`,
    "audit/scored": `scored ${s(e.source)} · survival ${e.doc_survival != null ? Number(e.doc_survival).toFixed(3) : "?"}`,
    "audit/flagged": `${s(e.source)} — verdict ${e.verdict}`,
    "audit/held": `${s(e.bundle)} — held · enforce`,
    "gate/pending": `${s(e.bundle)} — awaiting routing`,
    "analyst/done": `analysis done · ${e.chunks_passed ?? "?"}✓`,
    "ship/shipped": `${s(e.bundle)} — shipped ✓`,
  };
  return map[k] || `${e.stage || ""} ${e.event || ""}`.trim();
}

function header(d) {
  const w = d.watcher?.state === "running";
  const v = d.vram;
  let gpu = v && v.total ? `${Number(v.used).toFixed(1)}/${v.total} GB` : "GPU —";
  if (v && v.total) { // S38: append utilization + temperature when the probe reports them
    const bits = [];
    if (v.util != null) bits.push(`${Math.round(v.util)}%`);
    if (v.temp != null) bits.push(`${Math.round(v.temp)}°`);
    if (bits.length) gpu += ` · ${bits.join(" · ")}`;
  }
  const clock = new Date().toISOString().slice(11, 19);
  const sv = systemVerdict(d);
  return `<div class="room-head">` +
    `<div class="rh-brand"><span class="rh-logo">◆</span><div><div class="rh-title">File Portal</div><div class="rh-sub">OPERATIONS ROOM</div></div></div>` +
    `<div class="rh-stat"><span class="dot" style="background:${sv.color}"></span> System <b style="color:${sv.color}">${sv.word}</b></div>` +
    `<div class="rh-stat"><span class="dot ${w ? "ok" : "off"}"></span> Watcher <b>${w ? "up" : "off"}</b></div>` +
    `<div class="rh-stat mono">${gpu}</div>` +
    `<div class="rh-stat mono">${clock} UTC</div>` +
    `<button class="rh-theme" id="room-theme" title="Toggle theme">◐</button></div>`;
}

function render(vm) {
  if (!roomEl) return;
  if (surface === "wall") { renderWall(vm); return; }
  roomEl.className = "room-mode";
  roomEl.innerHTML =
    header(vm) + stationRail(vm) +
    `<canvas id="room-belt" class="room-belt"></canvas>` +
    kpiTiles(vm) +
    `<div class="room-panels">${convertPanel(vm)}${assayPanel(vm)}${eventsPanel(vm)}</div>` +
    `<div class="room-foot"><span>${esc(shiftLine(vm))}</span><span class="rf-lin">Control Room · projection of the live pipeline · docs/16</span></div>`;
  wire();
  attachBelt(vm); // persistent chips (module state) survive the innerHTML replace
}

function shiftLine(d) {
  const t = d.shift?.today;
  if (!t) return "line idle";
  const p = [];
  if (t.converted) p.push(`${t.converted} converted`);
  if (t.shipped) p.push(`${t.shipped} shipped`);
  if (t.failed) p.push(`${t.failed} held`);
  return p.length ? "shift: " + p.join(" · ") : "line idle";
}

// ---- interaction (through the SAME intent commands the Dock uses) --------------------------
function wire() {
  roomEl.querySelector("#room-theme")?.addEventListener("click", toggleTheme);
  roomEl.querySelector("#room-audit-toggle")?.addEventListener("click", async () => {
    try {
      const cur = (d0.assay?.mode) || "report";
      const next = cur === "report" ? "enforce" : "report";
      await invoke("audit_mode_set", { mode: next });
      deps.setStatus?.(`Assay: ${next}`);
      refresh();
    } catch (e) { deps.setStatus?.(`Assay mode: ${e}`); }
  });
  roomEl.querySelectorAll(".ac-remedy").forEach((b) => b.addEventListener("click", async () => {
    b.disabled = true;
    try { await invoke("assay_reconvert", { source: b.dataset.src }); deps.setStatus?.(`Re-queued ${b.dataset.src}`); }
    catch (e) { b.disabled = false; deps.setStatus?.(`Re-convert: ${e}`); }
  }));
  // S36: click a station to OPEN ITS DRILL-DOWN — the accurate observation of its real on-disk
  // tree. (Controls — gate mode, audit lever, re-convert — live in the Dock + the assay panel.)
  roomEl.querySelectorAll(".rl-st").forEach((el) =>
    el.addEventListener("click", (ev) => openDrill(el.dataset.seg, ev)));
}

// ---- the drill-down observation system (S36): station → live, real on-disk file tree --------
let drill = null;           // { seg, tree }
let drillCollapsed = new Set();
let drillT = 0;
let drillOrigin = "50% 40%";
const STATION_LABEL = { intake: "Intake", convert: "Convert", gate: "Gate", assay: "Assay", ship: "Ship", vault: "Vault" };
const STATION_GLYPH = { intake: "▚", convert: "⚙", gate: "✳", assay: "◎", ship: "⇈", vault: "▤" };

function openDrill(seg, ev) {
  drill = { seg, tree: null };
  drillCollapsed = new Set();
  const vw = window.innerWidth || 1, vh = window.innerHeight || 1;
  drillOrigin = (ev && ev.clientX != null) ? `${(ev.clientX / vw * 100).toFixed(1)}% ${(ev.clientY / vh * 100).toFixed(1)}%` : "50% 40%";
  clearTimeout(pollT); // pause the Room's own poll while inspecting
  buildDrillShell();
  drillLoop();
}
function killDrill() {
  drill = null;
  clearTimeout(drillT);
  document.getElementById("drill-overlay")?.remove();
  document.removeEventListener("keydown", drillEsc);
}
function closeDrill() {
  if (!drill) return;
  killDrill();
  if (active && surface === "room") roomLoop(); // resume the Room poll
}
function drillEsc(e) { if (e.key === "Escape") closeDrill(); }
function buildDrillShell() {
  document.getElementById("drill-overlay")?.remove();
  const o = document.createElement("div");
  o.id = "drill-overlay";
  o.innerHTML =
    `<div class="drill-backdrop"></div>` +
    `<div class="drill-panel" style="--drill-origin:${drillOrigin}">` +
    `<div class="drill-head"><span class="dh-glyph">${STATION_GLYPH[drill.seg] || "▤"}</span>` +
    `<span class="dh-title">${STATION_LABEL[drill.seg] || drill.seg} · live tree</span>` +
    `<span class="dh-root"></span>` +
    `<button class="dh-close" title="Close (Esc)">✕</button></div>` +
    `<div class="drill-body"><div class="rp-note" style="padding:10px 14px">reading disk…</div></div></div>`;
  document.body.appendChild(o);
  o.querySelector(".drill-backdrop").addEventListener("click", closeDrill);
  o.querySelector(".dh-close").addEventListener("click", closeDrill);
  document.addEventListener("keydown", drillEsc);
}
async function drillLoop() {
  if (!drill) return;
  try {
    drill.tree = await invoke("station_tree", { seg: drill.seg });
    renderDrillBody();
  } catch (e) { deps.dbg?.(`station_tree ${drill?.seg}: ${e}`); }
  drillT = setTimeout(drillLoop, 4000); // live observation — re-read disk every 4s
}
function flattenTree(nodes, depth, out) {
  for (const n of nodes) {
    const isDir = n.kind === "dir";
    const collapsed = drillCollapsed.has(n.id);
    out.push({ ...n, depth, isDir, collapsed });
    if (isDir && !collapsed && n.children) flattenTree(n.children, depth + 1, out);
  }
  return out;
}
function renderDrillBody() {
  const o = document.getElementById("drill-overlay");
  if (!o || !drill?.tree) return;
  const rootEl = o.querySelector(".dh-root");
  rootEl.textContent = drill.tree.root || "";
  rootEl.title = drill.tree.root || "";
  const rows = flattenTree(drill.tree.children || [], 0, []);
  const body = o.querySelector(".drill-body");
  body.innerHTML = rows.map((r) => {
    const nameCol = r.kind === "note" ? "var(--text-3)" : r.kind === "zone" ? "var(--clay)" : r.isDir ? "var(--text)" : "var(--text-2)";
    const caret = r.isDir ? (r.collapsed ? "▸" : "▾") : "";
    const right = (r.verdict && r.verdict !== null)
      ? `<span class="dverd" style="color:${VCOL[r.verdict] || "var(--text-3)"}">${r.survival != null ? Number(r.survival).toFixed(3) + " " : ""}${esc(r.verdict)}</span>`
      : (r.size ? `<span class="dsize">${esc(r.size)}</span>` : "");
    return `<div class="drow" data-id="${esc(r.id)}" data-dir="${r.isDir}" style="padding-left:${12 + r.depth * 18}px">` +
      `<span class="dcaret">${caret}</span>` +
      `<span class="dglyph">${r.glyph || ""}</span>` +
      `<span class="dname" style="color:${nameCol}">${esc(r.name)}</span>` +
      (r.meta ? `<span class="dmeta">${esc(r.meta)}</span>` : "") +
      right + `</div>`;
  }).join("");
  body.querySelectorAll('.drow[data-dir="true"]').forEach((el) => el.addEventListener("click", () => {
    const id = el.dataset.id;
    if (drillCollapsed.has(id)) drillCollapsed.delete(id); else drillCollapsed.add(id);
    renderDrillBody();
  }));
}

function toggleTheme() {
  const root = document.documentElement;
  const next = root.getAttribute("data-theme") === "light" ? "dark" : "light";
  root.setAttribute("data-theme", next);
}

let d0 = {}; // last view-model (for handlers that need current mode)
async function refresh() {
  if (!active) return;
  d0 = await gatherVM();
  render(d0);
}

async function roomLoop() {
  if (!active) return;
  await refresh();
  const fast = !!(d0.ls && d0.ls.converting);
  pollT = setTimeout(roomLoop, fast ? 4000 : 9000);
}

// ---- the canvas transit belt (S35) --------------------------------------------------------
// Ambient projection of the line's real activity. Runs only while the Room is showing.
function beltTargets(d) {
  const w = d.watcher?.state === "running";
  if (!w) return { n: 0, tints: [] };
  const dw = d.ls?.drop_waiting || 0;
  const conv = d.ls?.converting ? 1 : 0;
  const gateN = (d.pf || []).length;
  const heldN = d.assay?.held?.length || 0;
  const n = Math.max(2, Math.min(12, 2 + dw + conv + gateN + heldN));
  const tints = [];
  for (let i = 0; i < dw; i++) tints.push("flow");
  if (conv) tints.push("clay");
  for (let i = 0; i < gateN; i++) tints.push("warn");
  for (let i = 0; i < heldN; i++) tints.push("clay");
  while (tints.length < n) tints.push("flow");
  return { n, tints };
}
function newChip(tint) {
  return { x: Math.random(), y: 0.28 + Math.random() * 0.44, speed: (0.018 + Math.random() * 0.014) / 60, tint: tint || "flow" };
}
function refreshBeltPalette() {
  const cs = getComputedStyle(document.documentElement);
  belt.pal = {};
  for (const k of ["--flow", "--warn", "--clay", "--ok", "--border", "--border-strong", "--surface-2", "--text-3"]) {
    belt.pal[k] = cs.getPropertyValue(k).trim() || "#888";
  }
  belt.reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
}
function sizeBelt() {
  const c = belt.canvas; if (!c) return;
  const r = c.getBoundingClientRect();
  if (!r.width) return;
  belt.DPR = Math.min(2, window.devicePixelRatio || 1);
  belt.W = r.width; belt.H = r.height;
  c.width = belt.W * belt.DPR; c.height = belt.H * belt.DPR;
  c.getContext("2d").setTransform(belt.DPR, 0, 0, belt.DPR, 0, 0);
}
function rr(ctx, x, y, w, h, rad) {
  ctx.beginPath(); ctx.moveTo(x + rad, y);
  ctx.arcTo(x + w, y, x + w, y + h, rad); ctx.arcTo(x + w, y + h, x, y + h, rad);
  ctx.arcTo(x, y + h, x, y, rad); ctx.arcTo(x, y, x + w, y, rad); ctx.closePath();
}
function tintColor(t) { return belt.pal[{ flow: "--flow", warn: "--warn", clay: "--clay", ok: "--ok" }[t]] || belt.pal["--flow"]; }
function attachBelt(vm) {
  belt.canvas = document.getElementById("room-belt");
  if (!belt.canvas) return;
  refreshBeltPalette();
  const t = beltTargets(vm); belt.targetN = t.n; belt.tints = t.tints;
  requestAnimationFrame(() => sizeBelt());
  if (!belt.running) { belt.running = true; belt.raf = requestAnimationFrame(drawBelt); }
}
function stopBelt() {
  belt.running = false;
  if (belt.raf) cancelAnimationFrame(belt.raf);
  belt.raf = 0;
}
function drawBelt() {
  if (!belt.running) return;
  const c = belt.canvas;
  if (c && belt.W) {
    // sync chip population to the real target
    while (belt.chips.length < belt.targetN) belt.chips.push(newChip(belt.tints[belt.chips.length % (belt.tints.length || 1)]));
    while (belt.chips.length > belt.targetN) belt.chips.pop();
    const ctx = c.getContext("2d"), W = belt.W, H = belt.H, yMid = H * 0.5;
    ctx.clearRect(0, 0, W, H);
    ctx.strokeStyle = belt.pal["--border-strong"]; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(0, yMid); ctx.lineTo(W, yMid); ctx.stroke();
    for (let i = 0; i < 6; i++) {
      const x = (i + 0.5) / 6 * W;
      ctx.strokeStyle = belt.pal["--border"]; ctx.beginPath(); ctx.moveTo(x, 8); ctx.lineTo(x, H - 8); ctx.stroke();
      ctx.fillStyle = belt.pal["--text-3"]; ctx.beginPath(); ctx.arc(x, yMid, 2.2, 0, 7); ctx.fill();
    }
    for (const d of belt.chips) {
      const x = d.x * W, y = H * d.y, col = tintColor(d.tint);
      ctx.fillStyle = col; ctx.globalAlpha = 0.14; rr(ctx, x - 11, y - 7, 22, 14, 4); ctx.fill(); ctx.globalAlpha = 1;
      ctx.strokeStyle = col; ctx.lineWidth = 1.3; ctx.fillStyle = belt.pal["--surface-2"]; rr(ctx, x - 8, y - 5, 16, 10, 3); ctx.fill(); ctx.stroke();
      ctx.fillStyle = col; ctx.fillRect(x - 3.5, y - 2, 7, 1); ctx.fillRect(x - 3.5, y + 0.5, 4.5, 1);
      if (!belt.reduce) { d.x += d.speed; if (d.x > 1.05) { d.x = -0.05; d.tint = belt.tints[Math.floor(Math.random() * (belt.tints.length || 1))] || "flow"; d.y = 0.28 + Math.random() * 0.44; } }
    }
  }
  belt.raf = requestAnimationFrame(drawBelt);
}
addEventListener("resize", () => { if (belt.running) sizeBelt(); });

// ---- the Wall surface (S35): a glanceable projection for a screen across the room (docs/14) --
function renderWall(vm) {
  const sv = systemVerdict(vm);
  const m = vm.metrics || {}, ls = vm.ls || {}, assay = vm.assay || {};
  const surv = m.survival_avg, survStr = surv != null ? Number(surv).toFixed(2) : "—";
  const survCol = surv == null ? "var(--text-3)" : surv >= 0.9 ? "var(--ok)" : surv >= 0.75 ? "var(--warn)" : "var(--clay)";
  const thru = m.throughput_pp_s != null ? Number(m.throughput_pp_s).toFixed(1) : "—";
  const vault = m.vault_count != null ? String(m.vault_count) : "—";
  const conv = ls.converting ? shortName(ls.converting) : "line idle";
  const gateN = (vm.pf || []).length;
  // the six stations as big dots
  const defs = [
    { g: "▚", n: "Intake", on: (ls.drop_waiting || 0) > 0, col: "var(--flow)" },
    { g: "⚙", n: "Convert", on: !!ls.converting, col: "var(--clay)" },
    { g: "✳", n: "Gate", on: gateN > 0, col: "var(--clay)" },
    { g: "◎", n: "Assay", on: assay.verdict === "fail", col: assay.verdict === "fail" ? "var(--clay)" : assay.verdict === "flag" ? "var(--warn)" : "var(--ok)", always: true },
    { g: "⇈", n: "Ship", on: false, col: "var(--ok)" },
    { g: "▤", n: "Vault", on: true, col: "var(--ok)", always: true },
  ];
  const dots = defs.map((s) => {
    const lit = s.on || s.always;
    const col = lit ? s.col : "var(--text-3)";
    const pulse = (s.n === "Assay" && assay.verdict === "fail") ? "assay-pulse 1.7s ease-in-out infinite" : "none";
    return `<div class="wl-st"><div class="wl-dot" style="color:${col};border-color:${col};animation:${pulse};opacity:${lit ? 1 : 0.4}">${s.g}</div><div class="wl-nm">${s.n}</div></div>`;
  }).join("<span class='wl-link'></span>");
  const latest = (vm.shift?.tail || []).slice(-1)[0];
  const evtLine = latest ? eventMsg(latest) : "";
  roomEl.className = "wall-mode";
  roomEl.innerHTML =
    `<div class="wall">` +
    `<div class="wall-top"><span class="wl-brand">◆ File Portal</span><button class="rh-theme" id="room-theme">◐</button></div>` +
    `<div class="wall-verdict" style="color:${sv.color}">${sv.word.toUpperCase()}</div>` +
    `<div class="wall-line">${dots}</div>` +
    `<div class="wall-heroes">` +
    `<div class="wl-hero"><div class="wl-hv" style="color:${survCol}">${survStr}</div><div class="wl-hl">survival avg</div></div>` +
    `<div class="wl-hero"><div class="wl-hv">${thru}<span>pp/s</span></div><div class="wl-hl">throughput</div></div>` +
    `<div class="wl-hero"><div class="wl-hv">${vault}</div><div class="wl-hl">in the vault</div></div>` +
    `</div>` +
    `<div class="wall-foot"><span class="wl-conv">${esc(conv)}</span><span class="wl-evt">${esc(evtLine)}</span></div>` +
    `</div>`;
  roomEl.querySelector("#room-theme")?.addEventListener("click", toggleTheme);
}

// ---- public API ---------------------------------------------------------------------------
export function initRoom(dependencies) {
  deps = dependencies || {};
  roomEl = document.getElementById("room");
}

// name: "off" | "room" | "wall"
export function setActiveSurface(name) {
  clearTimeout(pollT);
  killDrill(); // any open inspector closes when the surface changes
  if (name === "off") { active = false; stopBelt(); roomEl.hidden = true; return; }
  surface = name;
  active = true;
  if (name !== "room") stopBelt();
  roomEl.hidden = false;
  roomLoop();
}
