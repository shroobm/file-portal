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
  } else if (ev.action === "rejected") {
    setStatus("✗ " + ev.file + " rejected: " + (ev.reason ?? "unknown"));
    tile?.classList.add("error");
    setTimeout(() => tile?.classList.remove("error"), 5000);
  } else if (ev.action === "skipped") {
    setStatus("⚠ " + ev.file + " skipped: " + (ev.reason ?? "collision"));
  }
}


init().catch((err) => {
  console.error("init failed", err);
  setStatus(`Init error: ${err}`);
});
