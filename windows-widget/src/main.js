// Renders one drop-target tile per configured portal and sends dropped files to the Rust
// backend's `send_to_portal` command. Kept framework-free on purpose — see docs/07-development-guide.md.

import { invoke } from "@tauri-apps/api/core";
import { getCurrentWebview } from "@tauri-apps/api/webview";

const portalsEl = document.getElementById("portals");
const statusEl = document.getElementById("status");

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

function tileForPosition(x, y) {
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

    if (type === "over") {
      const tile = tileForPosition(position.x, position.y);
      if (tile !== activeTile) {
        activeTile?.classList.remove("drag-over");
        activeTile = tile ?? null;
        activeTile?.classList.add("drag-over");
      }
      return;
    }

    if (type === "leave") {
      activeTile?.classList.remove("drag-over");
      activeTile = null;
      return;
    }

    if (type === "drop") {
      activeTile?.classList.remove("drag-over");
      const tile = activeTile ?? tileForPosition(position.x, position.y);
      activeTile = null;
      if (!tile) return;

      const category = tile.dataset.category;
      tile.classList.add("sending");
      setStatus(`Sending ${paths.length} file(s) to ${category}...`);

      try {
        const report = await invoke("send_to_portal", { category, paths });
        const failedCount = report.failed.length;
        setStatus(
          failedCount === 0
            ? `Sent ${report.sent.length} file(s) to ${category}.`
            : `Sent ${report.sent.length}, failed ${failedCount}. See logs.`
        );
      } catch (err) {
        setStatus(`Error: ${err}`);
      } finally {
        tile.classList.remove("sending");
      }
    }
  });
}

init();
