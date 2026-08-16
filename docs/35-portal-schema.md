# docs/35 — The Portal Schema

**What this is:** the manual of the File Portal *itself* — every folder and file class in the
pipeline, what writes it, what reads it, and what it means. Commissioned by Rab at the S85 open:
*"a schema regarding the file portal knowledge corpus, and manual, which should describe
everything regarding the file, and all the folders and files within."*

**Who reads it:** the operator, and **the embedded assistant** — this document is part of the
chat corpus, and every claim in it is written to be citable line-by-line. Static truths live
here; **live values do not** — the assistant renders live state through the projection path as
data and may point at this schema to explain what a value *is*, never to restate what it
currently *says* (docs/33 §2.1, signed).

**Ground truth:** compiled S85 (2026-08-16) by direct observation of the tree, the manifests,
and the writers' source. When this document and the disk disagree, the disk wins — measure,
then fix this document.

---

## 1. The two roots

| root | machine | what it is |
|---|---|---|
| `C:\Users\Bndit\ml\library\` | Desktop | **the pipeline root** — the factory floor; everything below lives under it |
| `C:\Users\Bndit\Projects\file-portal\` | Desktop | **the repo** — code, docs, session records; nothing here is pipeline state |

The vault (the factory's *output*) is a separate git repository on the ThinkPad, mirrored
locally; books arrive there only through the exporter's guarded rails.

## 2. The pipeline root, folder by folder

### 2.1 `drop/` — the intake conveyor
Drop a PDF here and the watcher (`windows-converter/watch_and_convert.py`, spawned inside the
widget's Job Object) picks it up on a 5-second poll and starts a conversion.
- `drop/done/` — source PDFs that converted successfully, moved here byte-identical. **These are
  the originals**: their sha256 is the bundle identity everywhere else (a held bundle's folder
  name is the first 16 hex of its source's sha256).
- `drop/failed/` — source PDFs whose conversion exited non-zero, moved here for retry or triage.

### 2.2 `anchor/` — the converted library, Desktop side
One folder per successful conversion (plus `[analyst-local]`-suffixed variants for analyst
re-runs). Each is a **bundle** — see §4 for anatomy. The anchor is what ships to the ThinkPad
and what the widget's stations count.

### 2.3 `held/` — the quarantine ward
Bundles whose Survival Audit verdict is `fail` while `audit-mode.txt` reads `enforce`. Folder
name = source sha256 first 16 hex. A held bundle waits for the Repair Bench (the human is the
vision authority) or a deliberate re-convert; a bundle carrying human repairs is never deleted
(SYM-009). The exporter refuses `fail` bundles fail-closed, so nothing held can reach the vault.

### 2.4 `pending/` — the gate's waiting room
Bundles awaiting a routing decision (which analyst backend, or a gate card's resolution).
Normally empty; an occupant means a decision is owed.

## 3. The pipeline root, file by file

### 3.1 The levers (single-value text files; the widget writes, python reads)
- `analyst-mode.txt` — `local` | `gemini` | `off`: which analyst backend the next conversion
  uses. `local` = qwen3:8b via Ollama, air-gapped; `gemini` = cloud, text leaves the machine.
- `audit-mode.txt` — `report` | `enforce`: whether a `fail` verdict merely reports or actually
  parks the bundle in `held/`.
- `chunk-batch.txt` — analyst chunk batch size (integer).

### 3.2 The marker files (presence-is-the-message)
- `.gpu-lock` — written by the watcher before a conversion, deleted after. **It is a busy
  SIGNAL, not a lock** — nothing is prevented by its existence (SYM-032); readers (room-chat,
  the parity harness) treat it as "a conversion is running" and yield voluntarily.
- `chat-hold.json` — written by the chat server when a model is loaded on the card; the watcher
  reads it before converting and **defers** until it clears (the signed deferral gate, docs/33
  §2.3). Contains `{port, model, ts}`. Sole writer: the chat server.

### 3.3 The ledgers and logs (append-only)
- `events.jsonl` — the factory's event stream. One JSON object per line:
  `{ts, pid, stage, event, …}` where `stage` ∈ intake/convert/analyst/audit/gate/ship/chat and
  stage-specific fields follow (e.g. `{"stage":"audit","event":"held","bundle":…,"verdict":"fail"}`).
  Emitted from python via `windows-converter/events.py` and from Rust via `events.rs`.
- `conversion-ledger.jsonl` — one line per conversion with the measured facts:
  `{ts, source, source_sha256, pages, lane, chars_per_page, wall_s, s_per_page, run_wall_s,
  resumed_slices, chunked, slices, batch, peak_vram_mib}`. This is where ETAs learn from.
- `watcher.log` / `watcher-stderr.log` — the watcher's narrative and last words.
- `widget-boot.log` — the widget's startup record, including watcher lifecycle notes.
- `bench-stderr.log`, `chat-stderr.log` — the Repair Bench's and chat server's last words.
- `algedonic-acks.jsonl` — acknowledgements on the alarm channel (docs/30).

## 4. Bundle anatomy (one converted book)

```
<Book Title>/
├── <Book Title>.md      the converted markdown — the book itself
├── assets/              extracted images: _page_<N>_Picture_<M>.jpeg / _page_<N>_Figure_<M>.jpeg
│                        (N is the ABSOLUTE source page — SYM-002's fix)
└── manifest.json        the bundle's papers, keys below
```

`manifest.json` keys (observed on real bundles):
- `source`, `source_sha256` — the original PDF's name and full sha256 (the identity).
- `engine` (`marker`), `lane` (`clean` | `scan`), `lane_reason`, `chars_per_page_detected` —
  how the converter routed it and why.
- `pages`, `converter_version`, `marker_version`, `converted_at`.
- `fidelity` — the Survival Audit's block: `verdict` (`pass`|`fail`), and under `convert`:
  scores, page flags, `tripwires.degeneration_detail.worst[]` (loop sites, line-keyed) and
  `runs[]` (omission runs, page-keyed — text the OCR dropped).
- `analyst` — the analyst pass record: backend, model, chunks passed/rejected/failed, timing.
- `supersede` — present only on deliberate remedy re-converts (authored by the widget's ⟳
  alone); the exporter's replace-in-place rail keys on it.

## 5. The repo, mapped for the assistant

- `windows-converter/` — the Desktop lane: `watch_and_convert.py` (intake watcher + deferral
  gate), `convert_and_ship.py` (Marker + bundle + ship), `analyst.py` (the link-fenced LLM
  pass), `fidelity_audit.py` (the Survival Audit), `room_chat.py` (the embedded assistant's
  server), `corpus_schema.py` (this schema's live half), `backend_parity.py` (+selftest).
- `windows-widget/` — the Tauri widget: `src-tauri/src/*.rs` (watcher, chat, bench, room,
  assay, config…), `src/room.js` + `index.html` (the surfaces).
- `linux-receiver/`, `linux-converter/`, `linux-dashboard/` — the ThinkPad lane: allocator,
  converter/exporter (the vault's only writers), dashboard.
- `docs/` — the signed designs and findings; notably `20` (operator manual), `21` (closeout
  contract), `29` (observability), `32` (proxies), `33` (the chat surface Circle), `34` (the
  measurement language), `35` (this schema).
- `sessions/` — one closeout per session; `SYMPTOM-INDEX.md` — retrieve failures by symptom;
  `CLAUDE_README.md` — the Change Ledger (the hard clock).
- `prototypes/` — quarantined explorations, zero pipeline coupling (`repair-bench` graduated
  pieces, `room-chat` pre-graduation home, `glm-ocr-probe` evidence).

## 6. What the assistant may and may not do with this document

It may **cite** any line here to explain what something is. It may **point** at a surface or a
live value rendered beside its answer. It may not restate live values in prose, may not alter
asset embeds (the link fence), and must **refuse** when the corpus does not contain the answer —
a refusal is the system working. Every answer carries a citation that mechanically resolves, or
the answer is replaced by the refusal (`room_chat.py`'s `_enforce_citation`, built S79).
