// Renders one drop-target tile per configured portal and sends dropped files to the Rust
// backend's `send_to_portal` command. Kept framework-free on purpose — see docs/07-development-guide.md.

// No bundler in this project (see docs/07-development-guide.md), so we can't resolve bare
// module specifiers like "@tauri-apps/api/core" -- use the global API Tauri injects instead
// (enabled via app.withGlobalTauri in tauri.conf.json).
const { invoke } = window.__TAURI__.core;
const { getCurrentWebview } = window.__TAURI__.webview;
const { getCurrentWindow } = window.__TAURI__.window;

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
          setStatus(`Sent ${report.sent.length} file(s) to ${category}.`);
          if (report.sent.length > 0) pollStatuses(report.sent, category);
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
const PF_POLL_MS = 15000;
const PF_FAST_POLL_MS = 4000;
let pfFastUntil = 0;
let pfWorking = new Set(); // ids clicked this session, until their card disappears

const BASE_HEIGHT = 224;
const CARD_HEIGHT = 76;

function pfEta(s) {
  if (s == null) return "?";
  return s < 90 ? `~${s}s` : `~${Math.round(s / 60)}m`;
}

function pfResize(count) {
  const { LogicalSize } = window.__TAURI__.dpi;
  getCurrentWindow()
    .setSize(new LogicalSize(480, BASE_HEIGHT + count * CARD_HEIGHT))
    .catch((e) => console.warn("resize failed", e));
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
      `<button class="pf-btn${rec === "local" ? " recommended" : ""}" data-backend="local" ${working ? "disabled" : ""}>🔒 Local ${pfEta(local.eta_s)}</button>` +
      `<button class="pf-btn${rec === "gemini" ? " recommended" : ""}" data-backend="gemini" ${working ? "disabled" : ""}>☁ Flash ${pfEta(gemini.eta_s)}</button>` +
      `<button class="pf-btn" data-backend="none" ${working ? "disabled" : ""}>Ship as-is</button>` +
      `</div>`;

    el.querySelectorAll(".pf-btn").forEach((btn) =>
      btn.addEventListener("click", () => pfDecide(card.id, btn.dataset.backend))
    );
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
    if (st.state === "stopped") {
      watcherRender(await invoke("watcher_start"));
    } else {
      watcherRender(st);
    }
  } catch (err) {
    console.warn("watcher autostart failed", err);
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

init().catch((err) => {
  console.error("init failed", err);
  setStatus(`Init error: ${err}`);
});
vaultLoop();
pfLoop();
watcherAutostart();
shiftLoop();
