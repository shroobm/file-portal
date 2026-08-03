# `prototypes/` — the quarantine section

Experimental builds and design explorations that are **deliberately quarantined from the
pipeline**: nothing in here is imported, spawned, watched, shipped, or run by the live
system (widget, converter, exporter, watcher). CI does not touch it. It is safe to keep,
safe to ignore, and safe to delete.

**Why it exists.** Rab asked (2026-07-21) for a place to record development explorations
"passively — so if someone wants it they can have it in the quarantined section," each
given a **category** and a **name**, without any risk to the production pipeline. This is
that place. A prototype graduates into the real system only by an explicit, separate
decision — never by living here.

## Layout

```
prototypes/
  <category>/
    <name>/
      <files…>        # the prototype itself (self-contained where possible)
      DESIGN.md       # what it is, the research/references behind it, the decisions
```

## Index

| Category | Name | What it is | Status |
|---|---|---|---|
| `control-panel` | `opsroom` | A professional control-panel / dashboard representation of the pipeline — pipeline segmentation, a live transit viewer, the Survival Audit, live numbers and progress bars. Self-contained `opsroom.html`; opens in any browser; zero dependencies. Design lineage: Project Cybersyn's Operations Room (Beer + Bonsiepe) × the Claude Design System × modern observability practice. | Prototype — awaiting Rab's verdict |
| `repair-bench` | *(itself)* | **Stage G (docs/19 §7): "the human IS the vision model."** Source-PDF page ⇄ markdown side-by-side, navigated by the audit's flagged zones; drag-crop or paste a screenshot → `assets/_repair_pN_k.png` embedded `![[…]]` at the zone with `manifest["repairs"]` provenance; re-score is a preview only. `bench.py` (stdlib + pymupdf) + `bench.html` + `acceptance.py`; `README.md` is its design record. **Deviation from the mocked-data rule, by signed design:** it operates on real held bundles when a human runs it (`--sandbox` for trials) — the quarantine here means the pipeline never depends on or triggers it. | Prototype — 26/26 acceptance on a sandbox of the real Valentine; awaiting Rab's first real repair (graduation criteria: docs/19 §7) |

## Rules

- **No pipeline coupling.** A prototype must not read, write, or trigger anything the live
  system depends on. Static/self-contained or clearly-mocked data only.
- **Category + name.** Every prototype lives under `prototypes/<category>/<name>/`.
- **Document it.** Each carries a `DESIGN.md` — what it is, the references, the decisions —
  so it stands on its own if revisited later.
- **Disposable by default.** If it's rejected, it stays here as a record or is deleted; it
  never leaks into the pipeline.
