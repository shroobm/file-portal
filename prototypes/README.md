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

## Rules

- **No pipeline coupling.** A prototype must not read, write, or trigger anything the live
  system depends on. Static/self-contained or clearly-mocked data only.
- **Category + name.** Every prototype lives under `prototypes/<category>/<name>/`.
- **Document it.** Each carries a `DESIGN.md` — what it is, the references, the decisions —
  so it stands on its own if revisited later.
- **Disposable by default.** If it's rejected, it stays here as a record or is deleted; it
  never leaks into the pipeline.
