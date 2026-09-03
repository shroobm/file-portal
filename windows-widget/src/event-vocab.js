// One event vocabulary for every operator surface.  The converter emits machine fields;
// Dock, Room, and Wall may compact the sentence, but they cannot silently recognize different
// recovery states.  Keep the literal stage/event keys here: convert_and_ship_selftest T7 reads
// this shared source as the parity tripwire.

// NUM-3 + M6-R1 (signed 2026-08-31): the one way a capped count may reach any glass.
// Known totals use N of M even when the list is complete. A legacy list is exact only below
// its producer cap; at/over the cap (or with a malformed total) it names both UNREAD and the
// operator's remedy instead of letting the retained count masquerade as the population.
// UI display limits never enter this decision; displaySliceNote reports them independently.
export function countOfTotal(shown, total, producerCap = null) {
  const shownOk = typeof shown === "number" && Number.isInteger(shown) && shown >= 0;
  const totalOk = shownOk && typeof total === "number" && Number.isInteger(total) && total >= shown;
  const capOk = typeof producerCap === "number" && Number.isInteger(producerCap) && producerCap > 0;
  const shownLabel = shownOk ? shown : "?";
  if (!shownOk || (producerCap != null && !capOk) || (capOk && shown > producerCap) ||
      (total != null && !totalOk)) {
    return `${shownLabel} of at least ${shownLabel} — total UNREAD · re-convert to measure totals`;
  }
  if (totalOk) return `${shown} of ${total}`;
  if (capOk && shown >= producerCap) {
    return `${shown} of at least ${shown} — total UNREAD · re-convert to measure totals`;
  }
  return `${shown}`;
}

export function displaySliceNote(available, limit, surface) {
  const availableOk = typeof available === "number" && Number.isInteger(available) && available >= 0;
  const limitOk = typeof limit === "number" && Number.isInteger(limit) && limit > 0;
  if (!availableOk || !limitOk || available <= limit) return "";
  return `${surface} shows first ${limit} of ${available} · open Repair Bench for the full retained list`;
}

export function eventPhrase(e, { compact = false, unknown = null } = {}) {
  if (!e) return unknown;
  const s = (v) => String(v ?? "").slice(0, compact ? 34 : 40);
  const icon = (glyph) => compact ? "" : `${glyph} `;
  const k = `${e.stage}/${e.event}`;
  const map = {
    "intake/detected": `${icon("📥")}${s(e.source)} — on the belt`,
    "intake/deferred": `${icon("⏸")}${s(e.source)} — deferred while assistant holds the card`,
    "intake/stale-hold-reaped": `${icon("⚠")}stale assistant hold reaped · ${s(e.reason)}`,
    "intake/stale-lock-reaped": `${icon("⚠")}stale GPU signal reaped · ${s(e.source)}`,
    "intake/failed": `${icon("✗")}${s(e.source)} — intake FAILED (${e.exit_code ?? "?"})${e.timeout_s ? ` · outer cap ${Math.round(e.timeout_s / 3600)}h` : ""}`,
    "convert/probe": `${icon("⚙")}probing ${s(e.source)} — ${e.pages}pp ${e.lane || ""}`.trim(),
    "convert/slice": `slice ${e.slice}/${e.slices} pp ${s(e.page_range)} · ${Math.round(e.wall_s || 0)}s${e.resumed ? " · resumed" : ""}${e.recovered ? ` · recovered @${e.batch}` : ""}`,
    "convert/stalled": `${icon("⚠")}pp ${s(e.page_range)} STALLED — recovery ladder engaging`,
    "convert/slice_retry": `${icon("↻")}pp ${s(e.page_range)} — retrying at batch ${e.batch ?? "?"}`,
    "convert/slice_retry_succeeded": `${icon("✓")}pp ${s(e.page_range)} — recovered at batch ${e.batch ?? "?"}`,
    "convert/slice_split": `${icon("⑂")}pp ${s(e.page_range)} — splitting range (depth ${e.split_depth ?? "?"})`,
    "convert/timeout": `${icon("✗")}pp ${s(e.page_range)} — Marker timeout ${Math.round(e.elapsed_s || 0)}s`,
    "convert/chunk_batch_invalid": `batch lever invalid (${s(e.value)}) — using ${e.fallback ?? "?"}`,
    "convert/chunk_batch_unreadable": "batch lever unreadable — using default",
    "convert/ollama_unloaded": `ollama released ${e.count ?? "?"} resident(s) — VRAM margin cleared`,
    "convert/asset_range_warning": `${icon("⚠")}pp ${s(e.page_range)} — assets outside slice range`,
    "convert/converted": `${icon("⚙")}converted ${s(e.source)} in ${Math.round(e.wall_s || 0)}s${e.retry_wall_s ? ` (+${Math.round(e.retry_wall_s)}s retries)` : ""}${e.resumed_slices ? ` · ${e.resumed_slices} resumed` : ""}`,
    // J24 (commit 850bdf3, convert_and_ship.py:670-683): block records ride beside the book,
    // never gate it — "blocks never fail a book" is the law, so blocks_error names the reason
    // and says so out loud rather than leaving a reader to guess whether the CONVERT failed too.
    "convert/blocks": `${icon("▦")}${s(e.source)} — block records: ${e.blocks_total ?? "?"} blocks over ${e.slices_with_blocks ?? "?"}/${e.slices_total ?? "?"} slices`,
    "convert/blocks_partial": `${icon("⚠")}${s(e.source)} — block records INCOMPLETE · ${typeof e.slices_total === "number" && typeof e.slices_with_blocks === "number" ? e.slices_total - e.slices_with_blocks : "?"} of ${e.slices_total ?? "?"} slices missing${e.page_unresolved ? ` · ${e.page_unresolved} pp unresolved` : ""}`,
    "convert/blocks_error": `${icon("✗")}${e.source ? `${s(e.source)} — ` : ""}block records error (${s(e.phase)}${e.page_range ? ` @ pp ${s(e.page_range)}` : ""}): ${s(e.error)} — conversion unaffected`,
    "audit/scored": `scored ${s(e.source)} · survival ${e.doc_survival != null ? Number(e.doc_survival).toFixed(3) : "?"}`,
    "audit/flagged": `${s(e.source)} — verdict ${e.verdict}`,
    "audit/verdict_fail": `${s(e.bundle)} — verdict FAIL · algedonic`,
    "audit/held": `${s(e.bundle)} — held · enforce`,
    "audit/supersede": `${s(e.source)} — remedy carried · replaces on pass`,
    "audit/supersede_ignored": `${s(e.source)} — remedy dropped · sha mismatch`,
    "gate/pending": `${icon("✳")}${s(e.bundle)} — awaiting YOUR routing decision`,
    "gate/auto_routed": `${icon("✳")}${s(e.bundle)} — rule auto-routed local`,
    "gate/resolved": `${icon("✓")}task complete — check the Library button`,
    "gate/failed": `${icon("✗")}routing failed: ${s(e.error)} — pick a route to retry`,
    "analyst/start": `${icon("🧠")}analyzing ${s(e.bundle)} (${e.backend})…`,
    "analyst/done": `${icon("🧠")}analysis done · ${e.chunks_passed ?? "?"}✓ ${e.chunks_rejected || 0} protected`,
    "ship/shipped": `${icon("⇈")}${s(e.bundle)} — shipped to vault ✓`,
    "ship/failed": `${icon("✗")}ship failed: ${s(e.error)}`,
  };
  return map[k] ?? unknown;
}
