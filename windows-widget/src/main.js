// Renders one drop-target tile per configured portal and sends dropped files to the Rust
// backend's `send_to_portal` command. Kept framework-free on purpose — see docs/07-development-guide.md.

// No bundler in this project (see docs/07-development-guide.md), so we can't resolve bare
// module specifiers like "@tauri-apps/api/core" -- use the global API Tauri injects instead
// (enabled via app.withGlobalTauri in tauri.conf.json).
const { invoke } = window.__TAURI__.core;
const { getCurrentWebview } = window.__TAURI__.webview;
const { getCurrentWindow } = window.__TAURI__.window;

// S34 — the Room surface (docs/16). Kept in its own ES module so the proven Dock code below
// is untouched. Relative import resolves natively in the webview (no bundler needed — only
// BARE specifiers can't resolve here).
import { initRoom, setActiveSurface } from "./room.js";

// Boot diagnostics (S22 debug): any uncaught error or rejection lands in the status
// line instead of a console nobody can open in release builds.
function dbg(msg) {
  try { invoke("debug_log", { msg: String(msg) }); } catch { /* pre-IPC */ }
}
window.addEventListener("error", (e) => {
  const m = `JS error: ${e.message} @ ${(e.filename || "").split("/").pop()}:${e.lineno}`;
  document.getElementById("status").textContent = m;
  dbg(m);
});
window.addEventListener("unhandledrejection", (e) => {
  document.getElementById("status").textContent = `Unhandled: ${e.reason}`;
  dbg(`unhandled rejection: ${e.reason}`);
});
dbg("boot: module evaluating");

const portalsEl = document.getElementById("portals");
const statusEl = document.getElementById("status");

// Wire the titlebar minimize button. Dragging is handled by Tauri via the data-tauri-drag-region
// attributes on #titlebar (needs core:window:allow-start-dragging); minimize needs this JS call
// (needs core:window:allow-minimize). Wired at top level so it works even if list_portals stalls.
const minBtn = document.getElementById("min-btn");
minBtn?.addEventListener("click", () => {
  getCurrentWindow().minimize();
});

function setStatus(message) {
  statusEl.textContent = message;
}

function renderPortals(portals) {
  portalsEl.innerHTML = "";
  for (const portal of portals) {
    const tile = document.createElement("div");
    tile.className = "portal";
    tile.dataset.category = portal.category;
    tile.innerHTML = `<span class="icon">${portal.icon}</span><span>${portal.label}</span>`;
    portalsEl.appendChild(tile);
  }
}

function tileForPosition(physicalX, physicalY) {
  // event.payload.position is in PHYSICAL pixels; getBoundingClientRect() is in CSS/logical
  // pixels. On any display scaling other than 100% these don't match, so convert first.
  const x = physicalX / window.devicePixelRatio;
  const y = physicalY / window.devicePixelRatio;
  return [...document.querySelectorAll(".portal")].find((el) => {
    const r = el.getBoundingClientRect();
    return x >= r.left && x <= r.right && y >= r.top && y <= r.bottom;
  });
}

async function init() {
  const portals = await invoke("list_portals");
  renderPortals(portals);

  let activeTile = null;

  const webview = getCurrentWebview();

  await webview.onDragDropEvent(async (event) => {
    const { type, position, paths } = event.payload;
    console.log("dragDropEvent", type, position, paths);

    if (type === "enter" || type === "over") {
      const tile = tileForPosition(position.x, position.y);
      if (tile !== activeTile) {
        activeTile?.classList.remove("drag-over");
        activeTile = tile ?? null;
        activeTile?.classList.add("drag-over");
      }
      setStatus(activeTile ? `Hovering over ${activeTile.dataset.category}` : "");
      return;
    }

    if (type === "leave") {
      activeTile?.classList.remove("drag-over");
      activeTile = null;
      setStatus("");
      return;
    }

    if (type === "drop") {
      activeTile?.classList.remove("drag-over");
      const tile = activeTile ?? tileForPosition(position.x, position.y);
      activeTile = null;

      if (!tile) {
        setStatus("Dropped outside any portal — try again over a tile.");
        return;
      }

      const category = tile.dataset.category;
      tile.classList.add("sending");
      setStatus(`Sending ${paths.length} file(s) to ${category}...`);

      try {
        const report = await invoke("send_to_portal", { category, paths });
        const failedCount = report.failed.length;
        if (failedCount === 0) {
          if (category === "convert-gpu") {
            // Local conveyor: the line strip is this category's status — no ThinkPad
            // allocator events to poll for.
            setStatus(`Queued ${report.sent.length} file(s) for GPU convert — watch the line.`);
          } else {
            setStatus(`Sent ${report.sent.length} file(s) to ${category}.`);
            if (report.sent.length > 0) pollStatuses(report.sent, category);
          }
        } else {
          console.error("transfer failures", report.failed);
          const firstError = report.failed[0]?.error ?? "unknown error";
          setStatus(`Sent ${report.sent.length}, failed ${failedCount}: ${firstError}`);
        }
      } catch (err) {
        console.error("send_to_portal failed", err);
        setStatus(`Error: ${err}`);
      } finally {
        tile.classList.remove("sending");
      }
    }
  });
}


async function pollStatuses(sentPaths, category) {
  const pending = new Set(sentPaths.map((p) => p.replace(/\\/g, "/").split("/").pop()));
  for (let i = 0; i < 10 && pending.size > 0; i++) {
    await new Promise((r) => setTimeout(r, 3000));
    for (const filename of [...pending]) {
      try {
        const ev = await invoke("fetch_file_status", { category, filename });
        if (ev) { pending.delete(filename); applyStatusEvent(category, ev); }
      } catch (err) { console.warn("poll error", err); }
    }
  }
  if (pending.size > 0) setStatus("Sent -- allocator pending for " + pending.size + " file(s).");
}

function applyStatusEvent(category, ev) {
  const tile = document.querySelector(".portal[data-category=\"" + category + "\"]");
  if (ev.action === "allocated") {
    setStatus("✓ " + ev.file + " → " + (ev.dest ?? category));
    tile?.classList.add("success");
    setTimeout(() => tile?.classList.remove("success"), 3000);
    // A vault-bound file just left: the converter takes ~a minute, so watch the vault
    // closely for a while instead of waiting for the slow poll to notice.
    if ((ev.dest ?? "").startsWith("pipeline/convert")) vaultFastPoll();
  } else if (ev.action === "rejected") {
    setStatus("✗ " + ev.file + " rejected: " + (ev.reason ?? "unknown"));
    tile?.classList.add("error");
    setTimeout(() => tile?.classList.remove("error"), 5000);
  } else if (ev.action === "skipped") {
    setStatus("⚠ " + ev.file + " skipped: " + (ev.reason ?? "collision"));
  }
}


// ---- S18: pre-flight analyst cards ---------------------------------------------------
// The Desktop converter parks bundles in pending/ when analyst-mode is "ask"; each gets a
// card here: measured ETAs, privacy labels, the estimator's recommendation, and three
// routes. A click spawns the detached resume (Rust preflight_decide) and the card lives
// until the resume ships the bundle (json deleted) or fails (state: "failed").

const cardsEl = document.getElementById("preflight-cards");
let rulesAutoLocal = false;
invoke("rules_get").then((r) => { rulesAutoLocal = r.auto_local_over_chunks != null; })
  .catch(() => {});
const PF_POLL_MS = 15000;
const PF_FAST_POLL_MS = 4000;
let pfFastUntil = 0;
let pfWorking = new Set(); // ids clicked this session, until their card disappears

const BASE_HEIGHT = 224;
const CARD_HEIGHT = 76;
const LINE_HEIGHT = 30;
let lineVisible = false;

function pfEtaOne(s) {
  return s < 90 ? `${s}s` : `${Math.round(s / 60)}m`;
}
function pfEta(backendInfo) {
  const r = backendInfo?.eta_range_s;
  if (r && r.length === 2 && r[0] !== r[1]) return `~${pfEtaOne(r[0])}–${pfEtaOne(r[1])}`;
  const s = backendInfo?.eta_s;
  return s == null ? "?" : `~${pfEtaOne(s)}`;
}

// ---- window sizing (S39): respect a manual resize -----------------------------------------
// The window is resizable; the widget only auto-sizes to avoid clipping content. Once the user
// drags a surface to their own size we remember it (per surface) and stop forcing — reflow then
// only GROWS the Dock to prevent a clip, never shrinks and never touches width. (`surface` is
// module-scoped below; these run after boot so it's initialised by call time.)
const DEFAULT_DOCK_W = 480;
const userSize = {};        // { dock?:{w,h}, room?:{w,h}, wall?:{w,h} } — set when the user drags
let lastApplied = null;     // the last size WE set programmatically (to tell our resize from theirs)
let suppressResizeUntil = 0;
let winScale = 1;           // cached device scale factor (physical → logical)

async function applySize(w, h) {
  w = Math.round(w); h = Math.round(h);
  lastApplied = { w, h };
  suppressResizeUntil = Date.now() + 350; // ignore the resize echo of our own setSize
  try {
    const { LogicalSize } = window.__TAURI__.dpi;
    await getCurrentWindow().setSize(new LogicalSize(w, h));
  } catch (e) { dbg(`resize: ${e}`); }
  suppressResizeUntil = Date.now() + 350; // re-arm past the event settle
}

// Watch for a MANUAL resize (a size we didn't set) and remember it for the current surface.
async function initSizing() {
  const win = getCurrentWindow();
  try { winScale = await win.scaleFactor(); } catch { winScale = 1; }
  try {
    await win.onResized(({ payload }) => {
      if (Date.now() < suppressResizeUntil) return;      // our own programmatic resize settling
      const lw = Math.round(payload.width / winScale);
      const lh = Math.round(payload.height / winScale);
      if (!lastApplied || Math.abs(lw - lastApplied.w) > 2 || Math.abs(lh - lastApplied.h) > 2) {
        userSize[surface] = { w: lw, h: lh };            // the user dragged this surface — keep it
        dbg(`user-sized ${surface} → ${lw}×${lh}`);
      }
    });
    await win.onScaleChanged(({ payload }) => { winScale = payload.scaleFactor || winScale; });
  } catch (e) { dbg(`onResized unavailable: ${e}`); }
}

let pfCardCount = 0;
function reflow() {
  // Auto-fit the DOCK's height to content (S22: the DOM knows its height; the old arithmetic
  // model clipped the titlebar). S39: never fight a manual resize — off the Dock we don't touch
  // the window, and once the user has sized the Dock we only grow to prevent a clip.
  if (surface !== "dock") return;
  requestAnimationFrame(() => {
    const need = Math.ceil(document.body.scrollHeight) + 2;
    const u = userSize.dock;
    if (u) {
      if (need > u.h) { u.h = need; applySize(u.w, need); } // grow just enough; keep their width
      return;                                               // otherwise leave their size alone
    }
    applySize(DEFAULT_DOCK_W, need);                        // default auto-fit until they take over
  });
}
function pfResize(count) {
  pfCardCount = count;
  reflow();
}

function pfRender(cards) {
  cardsEl.innerHTML = "";
  for (const card of cards) {
    const pf = card.preflight ?? {};
    const local = pf.backends?.local ?? {};
    const gemini = pf.backends?.gemini ?? {};
    const rec = pf.recommendation;
    const working = card.state === "running" || pfWorking.has(card.id);
    const failed = card.state === "failed";

    const el = document.createElement("div");
    el.className = "pf-card" + (working ? " working" : "");
    el.dataset.id = card.id;

    const meta = [
      `${pf.est_chunks ?? "?"} chunks`,
      `~${((pf.est_tokens ?? 0) / 1000).toFixed(1)}k tok`,
      pf.gpu_busy ? "⚠ GPU busy" : "GPU free",
    ].join(" · ");

    const warn = failed
      ? `<div class="pf-warn pf-error">✗ ${card.error ?? "failed"} — pick a route to retry</div>`
      : gemini.warning
        ? `<div class="pf-warn">⚠ ${gemini.warning}</div>`
        : "";

    el.innerHTML =
      `<div class="pf-title"><span class="spark">✳</span>` +
      `<span class="name">${card.bundle_name}</span></div>` +
      `<div class="pf-meta">${working ? "analyst working…" : meta}</div>` +
      warn +
      `<div class="pf-actions">` +
      `<button class="pf-btn${rec === "local" ? " recommended" : ""}" data-backend="local" ${working ? "disabled" : ""}>🔒 Local ${pfEta(local)}</button>` +
      `<button class="pf-btn${rec === "gemini" ? " recommended" : ""}" data-backend="gemini" ${working ? "disabled" : ""}>☁ Flash ${pfEta(gemini)}</button>` +
      `<button class="pf-btn" data-backend="none" ${working ? "disabled" : ""}>Ship as-is</button>` +
      `</div>` +
      // S22 remember-my-choice: only offered where it applies (big docs), per docs/13.
      ((pf.est_chunks ?? 0) > 18 && !working
        ? `<label class="pf-rule"><input type="checkbox" id="rule-${card.id}"${rulesAutoLocal ? " checked" : ""}> always route big docs 🔒 local</label>`
        : "");

    el.querySelectorAll(".pf-btn").forEach((btn) =>
      btn.addEventListener("click", () => pfDecide(card.id, btn.dataset.backend))
    );
    el.querySelector(`#rule-${CSS.escape(card.id)}`)?.addEventListener("change", async (e) => {
      try {
        const rules = await invoke("rules_set",
          { autoLocalOverChunks: e.target.checked ? 18 : null });
        rulesAutoLocal = rules.auto_local_over_chunks != null;
        setStatus(rulesAutoLocal ? "Rule set: big docs auto-route local" : "Rule cleared");
      } catch (err) {
        setStatus(`Rule: ${err}`);
      }
    });
    cardsEl.appendChild(el);
  }
  pfResize(cards.length);
}

async function pfDecide(id, backend) {
  try {
    pfWorking.add(id);
    setStatus(backend === "none" ? "Shipping as-is…" : `Analyst (${backend}) started…`);
    await invoke("preflight_decide", { id, backend });
    pfFastUntil = Date.now() + 20 * 60 * 1000; // watch the queue closely until it clears
    await pfCheck();
  } catch (err) {
    pfWorking.delete(id);
    console.error("preflight_decide failed", err);
    setStatus(`Route failed: ${err}`);
  }
}

async function pfCheck() {
  try {
    const cards = await invoke("preflight_list");
    gateCount = cards.length;
    for (const id of [...pfWorking]) {
      if (!cards.some((c) => c.id === id)) {
        pfWorking.delete(id); // shipped and cleared — the vault will glow shortly
        setStatus("✓ analyst done — bundle shipped");
        vaultFastPoll();
      }
    }
    pfRender(cards);
  } catch (err) {
    console.warn("preflight_list failed", err);
  }
}

async function pfLoop() {
  await pfCheck();
  const wait = Date.now() < pfFastUntil ? PF_FAST_POLL_MS : PF_POLL_MS;
  setTimeout(pfLoop, wait);
}

// ---- S21: the line (docs/13 grammar) + gate selector + reader launchers --------------

const lineEl = document.getElementById("line");
const stDrop = document.getElementById("st-drop");
const stConvert = document.getElementById("st-convert");
const stGate = document.getElementById("st-gate");
const stShip = document.getElementById("st-ship");
const stLib = document.getElementById("st-lib");
const MODE_LABELS = { ask: "ask", local: "auto-🔒", gemini: "auto-☁", off: "off" };
const MODE_ORDER = ["ask", "local", "gemini", "off"];
let gateMode = "ask";
let gateCount = 0;

function stSet(el, value, cls = "") {
  el.querySelector(".st-v").textContent = value;
  el.className = "st " + cls;
}

// S26: the stage ticker — the pipeline's newest event as a human sentence, shown in
// the shift line while work is fresh (the user's READY→CONVERTING→…→COMPLETE narration).
function tickerPhrase(ev) {
  if (!ev) return null;
  const s = (v) => String(v ?? "").slice(0, 40);
  const key = `${ev.stage}/${ev.event}`;
  const map = {
    "intake/detected": `📥 ${s(ev.source)} — on the belt`,
    "convert/probe": `⚙ probing ${s(ev.source)} — ${ev.pages}pp, ${ev.lane} lane`,
    "convert/converted": `⚙ converted ${s(ev.source)} in ${Math.round(ev.wall_s)}s — bundling`,
    "gate/pending": `✳ ${s(ev.bundle)} — awaiting YOUR routing decision`,
    "gate/auto_routed": `✳ ${s(ev.bundle)} — rule auto-routed 🔒 local`,
    "analyst/start": `🧠 analyzing ${s(ev.bundle)} (${ev.backend})…`,
    "analyst/done": `🧠 analysis done: ${ev.chunks_passed}✓ ${ev.chunks_rejected || 0}🛡 in ${Math.round(ev.duration_s)}s`,
    "ship/shipped": `⇈ ${s(ev.bundle)} — shipped to vault ✓`,
    "gate/resolved": `✓ task complete — check the Library button`,
    "intake/failed": `✗ ${s(ev.source)} failed — see the drop tray`,
    "gate/failed": `✗ routing failed: ${s(ev.error)} — pick a route to retry`,
    "ship/failed": `✗ ship failed: ${s(ev.error)}`,
  };
  return map[key] ?? null;
}

async function lineLoop() {
  try {
    const ls = await invoke("line_state");
    if (ls.available) {
      if (!lineVisible) { lineVisible = true; lineEl.hidden = false; reflow(); }
      const failed = ls.failed_count ?? 0;
      stSet(stDrop, failed ? `${ls.drop_waiting} (+${failed}✗)` : String(ls.drop_waiting),
        failed ? "has-failed" : "");
      stDrop.classList.toggle("has-failed", failed > 0);
      if (ls.converting) {
        const eta = ls.converting_eta_s != null ? ` ~${pfEtaOne(ls.converting_eta_s)} left` : "";
        stSet(stConvert, `${ls.converting}${eta}`, "active");
      } else {
        stSet(stConvert, "idle", "");
      }
      stSet(stGate, gateCount > 0 ? `${gateCount} waiting` : MODE_LABELS[gateMode],
        gateCount > 0 ? "attn" : "");
      if (ls.last_shipped?.bundle) {
        stSet(stShip, ls.last_shipped.bundle, "");
      }
      // Ticker owns the shift line while the machine is mid-story.
      const phrase = tickerPhrase(ls.latest);
      const busy = ls.converting || gateCount > 0 ||
        (ls.latest && ["analyst", "ship"].includes(ls.latest.stage));
      if (phrase && busy) shiftEl.textContent = phrase;
    }
  } catch (err) {
    console.warn("line_state failed", err);
  }
  setTimeout(lineLoop, ls_fast() ? 5000 : 10000);
}
function ls_fast() {
  return document.getElementById("st-convert").classList.contains("active");
}

stGate.addEventListener("click", async () => {
  if (gateCount > 0) return; // cards waiting — the gate isn't a toggle right now
  try {
    const next = MODE_ORDER[(MODE_ORDER.indexOf(gateMode) + 1) % MODE_ORDER.length];
    gateMode = await invoke("analyst_mode_set", { mode: next });
    stSet(stGate, MODE_LABELS[gateMode], "");
    setStatus(`Analyst gate: ${gateMode}`);
  } catch (err) {
    setStatus(`Gate: ${err}`);
  }
});

stDrop.addEventListener("click", () => {
  if (stDrop.classList.contains("has-failed")) invoke("open_failed_tray").catch(() => {});
});

// S22: the ship station's receipt — last bundle's chain, shown in the status line.
stShip.addEventListener("click", async () => {
  try {
    const r = await invoke("last_receipt");
    const bits = [r.bundle];
    if (r.convert) bits.push(`${r.convert.pages}pp @ ${r.convert.s_per_page}s/p`);
    if (r.analyst) bits.push(
      `${r.analyst.backend}: ${r.analyst.passed}✓` +
      (r.analyst.protected ? ` ${r.analyst.protected}🛡` : "") +
      ` in ${Math.round(r.analyst.duration_s)}s`);
    if (lastAssay?.verdict) bits.push(`audit ${lastAssay.verdict}`);
    setStatus("receipt: " + bits.join(" · "));
  } catch (err) {
    setStatus(`Receipt: ${err}`);
  }
});
stShip.style.cursor = "pointer";

async function lineInit() {
  try {
    gateMode = await invoke("analyst_mode_get");
  } catch { /* stays default */ }
  try {
    const rc = await invoke("reader_config");
    dbg(`reader_config: ${JSON.stringify(rc)}`);
    for (const [name, id] of [["obsidian", "reader-obsidian"], ["zennotes", "reader-zennotes"]]) {
      const btn = document.getElementById(id);
      if (rc[name]) {
        btn.hidden = false;
        btn.addEventListener("click", () =>
          invoke("open_reader", { reader: name }).catch((e) => setStatus(`Reader: ${e}`)));
      }
    }
  } catch (err) {
    setStatus(`readers: ${err}`);
  }
  lineLoop();
}

// ---- S20: watcher lifecycle + shift report -------------------------------------------
// The widget owns the conveyor watcher (docs/13): autostarts it when configured, the
// titlebar dot shows/toggles it, and it dies with the window (Rust on_window_event).
// The shift line is today's factory totals, derived from events.jsonl — pure projection.

const watcherBtn = document.getElementById("watcher-btn");
const shiftEl = document.getElementById("shift");

function watcherRender(st) {
  if (st.state === "unconfigured") {
    watcherBtn.hidden = true;
    return;
  }
  watcherBtn.hidden = false;
  watcherBtn.className = st.state === "running" ? "running" : "";
  watcherBtn.title = st.state === "running"
    ? `Conveyor running (pid ${st.pid}) — click to pause intake`
    : "Conveyor stopped — click to start";
}

watcherBtn.addEventListener("click", async () => {
  try {
    const st = await invoke("watcher_status");
    watcherRender(await invoke(st.state === "running" ? "watcher_stop" : "watcher_start"));
  } catch (err) {
    console.error("watcher toggle failed", err);
    setStatus(`Watcher: ${err}`);
  }
});

async function watcherAutostart() {
  try {
    const st = await invoke("watcher_status");
    dbg(`watcher_status: ${JSON.stringify(st)}`);
    if (st.state === "stopped") {
      const started = await invoke("watcher_start");
      dbg(`watcher_start: ${JSON.stringify(started)}`);
      watcherRender(started);
    } else {
      watcherRender(st);
    }
  } catch (err) {
    console.warn("watcher autostart failed", err);
    setStatus(`watcher autostart: ${err}`);
    dbg(`watcher autostart FAILED: ${err}`);
  }
}

async function shiftLoop() {
  try {
    const s = await invoke("shift_summary");
    if (s.available) {
      const t = s.today;
      const parts = [];
      if (t.converted) parts.push(`${t.converted} converted`);
      if (t.analyzed) parts.push(`${t.analyzed} analyzed` +
        (t.chunks_protected ? ` (${t.chunks_protected} protected)` : ""));
      if (t.shipped) parts.push(`${t.shipped} shipped`);
      if (t.failed) parts.push(`${t.failed} failed`);
      shiftEl.textContent = parts.length ? "shift: " + parts.join(" · ") : "line idle";
    }
  } catch (err) {
    console.warn("shift_summary failed", err);
  }
  setTimeout(shiftLoop, 30000);
}

// ---- W8: Add-to-Library button -------------------------------------------------------
// The vault clone lives on this machine; new bundles only appear locally after a git pull.
// This bar polls `vault_check` (git fetch + behind-count in Rust), glows when the ThinkPad
// has pushed notes we don't have yet, and `vault_pull`s on click.

const vaultBar = document.getElementById("vault-bar");
const vaultBtn = document.getElementById("vault-btn");
const vaultBtnLabel = document.getElementById("vault-btn-label");
const vaultNote = document.getElementById("vault-note");

const VAULT_POLL_MS = 45000;
const VAULT_FAST_POLL_MS = 10000;
let vaultFastUntil = 0;
let vaultBusy = false;
let vaultDisabled = false;

function vaultRender(state, { label, note = "", enabled = true } = {}) {
  vaultBar.className = state;
  vaultBtnLabel.textContent = label;
  vaultNote.textContent = note;
  vaultNote.title = note;
  vaultBtn.disabled = !enabled;
}

function describeBundles(st) {
  const names = (st.bundles ?? []).map((s) => s.replace(/--[0-9a-f]{8}$/, ""));
  if (names.length === 0) return st.behind + " update(s)";
  const shown = names.slice(0, 2).join(", ");
  return names.length > 2 ? `${shown} +${names.length - 2} more` : shown;
}

function vaultApply(st) {
  if (st.state === "disabled") {
    vaultDisabled = true;
    vaultBar.hidden = true;
    return;
  }
  vaultBar.hidden = false;
  if (st.state === "updates") {
    const n = (st.bundles ?? []).length || st.behind;
    vaultRender("ready", {
      label: `Add ${n} new note${n === 1 ? "" : "s"} to Library`,
      note: describeBundles(st),
    });
  } else if (st.state === "pulled") {
    vaultRender("success", { label: "Added to Library", note: "✓ " + describeBundles(st) });
    setTimeout(() => vaultCheck(), 4000);
  } else if (st.state === "up-to-date") {
    vaultRender("idle", { label: "Library", note: "up to date" });
  } else if (st.state === "offline") {
    vaultRender("offline", { label: "Library", note: "vault host unreachable — will retry" });
  } else {
    vaultRender("offline", { label: "Library", note: st.detail || "error" });
    console.error("vault error", st.detail);
  }
}

async function vaultCheck() {
  if (vaultBusy || vaultDisabled) return;
  vaultBusy = true;
  try {
    vaultApply(await invoke("vault_check"));
  } catch (err) {
    console.error("vault_check failed", err);
    vaultApply({ state: "error", detail: String(err) });
  } finally {
    vaultBusy = false;
  }
}

function vaultFastPoll() {
  vaultFastUntil = Date.now() + 3 * 60 * 1000;
}

vaultBtn.addEventListener("click", async () => {
  if (vaultBusy || vaultBtn.disabled) return;
  // Idle-state click = manual "check now"; ready-state click = pull.
  const pulling = vaultBar.classList.contains("ready");
  vaultBusy = true;
  vaultRender("working", { label: pulling ? "Pulling…" : "Checking…", enabled: false });
  try {
    vaultApply(await invoke(pulling ? "vault_pull" : "vault_check"));
  } catch (err) {
    console.error("vault action failed", err);
    vaultApply({ state: "error", detail: String(err) });
  } finally {
    vaultBusy = false;
  }
});

async function vaultLoop() {
  await vaultCheck();
  const wait = Date.now() < vaultFastUntil ? VAULT_FAST_POLL_MS : VAULT_POLL_MS;
  setTimeout(vaultLoop, wait);
}

// ---- S31: the Assay (docs/15 §13) --------------------------------------------------
// The Survival Audit as a see-and-steer channel: the ◎ station carries the last verdict,
// the card opens the evidence (damage map + verbatim runs) on flag/fail, and the
// report ⇄ enforce lever writes audit-mode.txt. Pure projection — Python owns the verdict;
// terracotta is spent only on `fail`, per docs/13.

const stAssay = document.getElementById("st-assay");
const assayCard = document.getElementById("assay-card");
let assayMode = "report";
let assayOpen = false; // user clicked the ◎ station to peek (pass state has no card by default)
let lastAssay = null;

const VERDICT = {
  pass: { cls: "g", sym: "✓" },
  flag: { cls: "a", sym: "⚠" },
  fail: { cls: "f", sym: "✕" },
};

function escHtml(s) {
  return String(s ?? "").replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}
function firstWords(s, n) {
  return String(s ?? "").split(/\s+/).filter(Boolean).slice(0, n).join(" ");
}

function assayRender(st) {
  if (!st || !st.available) { stAssay.hidden = true; return; }
  stAssay.hidden = false;
  lastAssay = st;
  assayMode = st.mode || "report";
  const verdict = st.verdict;
  const v = VERDICT[verdict];

  // Station: the verdict dot + a glanceable value (survival on pass, the word otherwise).
  stAssay.className = "st" + (v ? " " + verdict : "");
  const vEl = stAssay.querySelector(".st-v");
  vEl.textContent = verdict === "pass"
    ? (st.doc_survival != null ? Number(st.doc_survival).toFixed(2) : "ok")
    : (verdict || "—");

  const held = st.held || [];
  const show = verdict === "flag" || verdict === "fail" || held.length > 0 || assayOpen;
  if (!show) { assayCard.hidden = true; assayCard.innerHTML = ""; reflow(); return; }

  assayCard.hidden = false;
  assayCard.className = verdict === "fail" ? "fail" : "";
  const cls = v ? v.cls : "g";
  const pct = st.doc_survival != null ? Math.round(Number(st.doc_survival) * 100) : 100;

  const toggle =
    `<button id="audit-toggle" title="Enforce parks a failing bundle in held/ instead of shipping">` +
    `gate: <span class="${assayMode === "report" ? "on" : "off"}">report</span> ⇄ ` +
    `<span class="${assayMode === "enforce" ? "on" : "off"}">enforce</span></button>`;

  // The damage map: the book as a track, the trouble as bands you can point at.
  const mdLines = st.md_lines || 0;
  const zones = st.zones || [];
  const runs = st.runs || [];
  let map = "";
  if (st.degeneration && zones.length && mdLines) {
    const bands = zones.map((z) => {
      const left = Math.max(0, Math.min(98, (z.line / mdLines) * 100));
      const w = Math.max(1.5, Math.min(12, ((z.chars || 0) / (mdLines * 45)) * 100));
      return `<span class="z degen" style="left:${left.toFixed(1)}%;width:${w.toFixed(1)}%"></span>`;
    }).join("");
    map = `<div class="ac-caption"><b>degeneration</b> — ${zones.length} loop zone(s) · ${st.kind} lane</div>` +
      `<div class="ac-map">${bands}</div>`;
  } else if (runs.length && st.pages_scored) {
    const bands = runs.slice(0, 40).map((r) => {
      const left = Math.max(0, Math.min(98, ((r.page || 0) / st.pages_scored) * 100));
      return `<span class="z run" style="left:${left.toFixed(1)}%;width:1.5%"></span>`;
    }).join("");
    map = `<div class="ac-caption">${runs.length} omission run(s) · ${st.kind} lane</div>` +
      `<div class="ac-map">${bands}</div>`;
  }

  // The evidence, verbatim — the tool shows what it flagged before it pulses.
  let list = "";
  if (st.degeneration && zones.length) {
    list = "<ul class=\"ac-runs\">" + zones.slice(0, 3).map((z) =>
      `<li><span class="k">${Number(z.chars || 0).toLocaleString()} ch</span> · tri×${z.max_trigram} · ` +
      `<q>"${escHtml(firstWords(z.excerpt, 6))}…"</q></li>`).join("") + "</ul>";
  } else if (runs.length) {
    list = "<ul class=\"ac-runs\">" + runs.slice(0, 3).map((r) =>
      `<li><span class="k">p${r.page}</span> · ${r.words} words · ` +
      `<q>"${escHtml(firstWords(r.excerpt, 6))}…"</q></li>`).join("") + "</ul>";
  }

  let foot = "";
  if (verdict === "fail" || held.length) {
    foot = `<div class="ac-foot"><button class="ac-remedy" data-src="${escHtml(st.bundle)}">⟳ re-convert</button>` +
      `<span class="ac-swapnote">swap: <b>manual</b> — supersede flow pending</span></div>`;
  }

  let heldHtml = "";
  if (held.length) {
    const names = held.slice(0, 2).map((h) => escHtml(h.bundle)).join(", ");
    heldHtml = `<div class="ac-held">held: <b>${held.length}</b> awaiting remedy — ${names}</div>`;
  }

  const badge = v ? `<span class="badge ${cls}">${verdict} ${v.sym}</span>` : "";
  assayCard.innerHTML =
    `<div class="ac-head"><span class="spark">◎</span>` +
    `<span class="ttl">${escHtml(st.bundle || "last convert")}</span><span class="grow"></span>${toggle}</div>` +
    `<div class="ac-body"><div class="ac-verdict">` +
    `<span class="nm">survival ${st.doc_survival != null ? Number(st.doc_survival).toFixed(3) : "—"}</span>` +
    `<span class="meter"><i class="${cls}" style="width:${pct}%"></i></span>${badge}</div>` +
    map + list + foot + `</div>` + heldHtml;

  document.getElementById("audit-toggle")?.addEventListener("click", assayToggleMode);
  assayCard.querySelectorAll(".ac-remedy").forEach((b) =>
    b.addEventListener("click", () => assayReconvert(b)));
  reflow();
}

async function assayToggleMode() {
  const next = assayMode === "report" ? "enforce" : "report";
  try {
    assayMode = await invoke("audit_mode_set", { mode: next });
    setStatus(assayMode === "enforce"
      ? "Assay: enforce — a failing bundle is held, not shipped"
      : "Assay: report only — the verdict is recorded, nothing is gated");
    if (lastAssay) { lastAssay.mode = assayMode; assayRender(lastAssay); }
  } catch (err) { setStatus(`Assay mode: ${err}`); }
}

async function assayReconvert(btn) {
  const src = btn.dataset.src;
  btn.disabled = true;
  try {
    await invoke("assay_reconvert", { source: src });
    setStatus(`Re-queued ${src} for re-convert + re-audit — watch the line.`);
  } catch (err) {
    btn.disabled = false;
    setStatus(`Re-convert: ${err}`);
  }
}

stAssay.addEventListener("click", () => { assayOpen = !assayOpen; assayRender(lastAssay); });

const ASSAY_POLL_MS = 20000;
async function assayLoop() {
  try {
    assayRender(await invoke("assay_status"));
  } catch (err) {
    console.warn("assay_status failed", err);
  }
  setTimeout(assayLoop, ASSAY_POLL_MS);
}

// ---- S34: surface switch (Dock ⇄ Room) ------------------------------------------------
// The projection principle at work (docs/16): one state, two densities. Dock is the narrow
// floating widget (autosized). Room is a wider ops window. Only the layout + window size
// change; the data is the same live pipeline. Wall + belt + drill-down are the next
// installment (docs/16 §9), staged but not wired.

const SURFACE_SIZE = { room: [760, 600], wall: [900, 500] };
let surface = "dock";

initRoom({ setStatus, dbg });

function enterSurface(name) {
  if (name === surface) return;
  surface = name;
  document.querySelectorAll(".surf-btn").forEach((b) =>
    b.classList.toggle("active", b.dataset.surface === name));
  document.body.classList.toggle("surface-room", name === "room");
  document.body.classList.toggle("surface-wall", name === "wall");
  if (name === "dock") {
    setActiveSurface("off");
    // restore the user's Dock size if they set one, else content-fit
    if (userSize.dock) applySize(userSize.dock.w, userSize.dock.h);
    else reflow();
  } else {
    setActiveSurface(name); // "room" | "wall"
    const [w, h] = userSize[name]
      ? [userSize[name].w, userSize[name].h] // their remembered size for this surface
      : SURFACE_SIZE[name];                  // else the default
    applySize(w, h);
  }
}

document.querySelectorAll(".surf-btn").forEach((b) =>
  b.addEventListener("click", () => enterSurface(b.dataset.surface)));

init().catch((err) => {
  console.error("init failed", err);
  setStatus(`Init error: ${err}`);
});
vaultLoop();
pfLoop();
watcherAutostart();
shiftLoop();
assayLoop();
lineInit();
initSizing(); // S39: start watching for a manual resize (per-surface size memory)
dbg("boot: all loops launched");
reflow();
