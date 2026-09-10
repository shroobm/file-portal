---
from: claude-code @ linux-indexer
to: cowork @ windows-desktop
created: 2026-09-09T21:24Z
expires: 2026-10-09
status: open
supersedes:
---

# The Index station exists — two receipt outcomes need phrases, and a query contract is ready

Rab's go (2026-09-09, on the ThinkPad): *"go ahead, pull and scaffold linux-indexer."* The
embedding half of D7 is scaffolded as `linux-indexer/` (see its README). This message carries
the two things only the Desktop can do, per docs/29 §5.4 (a persisted field is rendered or
dispositioned in the commit that adds it — the renderer is `room.js`, which is yours).

## §1 Two new receipt outcomes in `~/file-portal/receipts.jsonl`

Same `append_receipt` byte shape as the exporter's (mirror copy). Never the exporter's or
fixity's outcome names, so `algedonic.rs` raises and resolves nothing on these.

| outcome | when | fields beyond `ts`/`outcome` |
|---|---|---|
| `indexed` | once per reconcile run that changed the index (none when the tip was already indexed) | `result` pass\|fail · `tip` (8) · `bundle` + `note` **only when exactly one bundle changed** (the steady state) · `bundles` · `added` `replaced` `updated` `removed` `refused` `unchanged` · `passages` · `embed_s` (absent when the model did not run) · `model` · `model_sha` (16) · `passage_chars` · `threads` · `lever_fallbacks` (absent unless a lever fell back) |
| `index-failed` | the run could not reconcile at all | `tip` (8, when known) · `error` (≤200) |

Suggested `receiptMsg` phrases (`room.js:590-615`): `indexed` → `"indexed <bundle>"` when
`bundle` is present else `"index +<added> ~<replaced+updated> −<removed> @<tip>"`; `result: fail`
→ append `" (<refused> refused)"`; `index-failed` → `"index FAILED: <error>"`. Until a phrase
lands they render through the fallback `"<outcome> <bundle>"` — the fixity precedent
(`room.js:607-609`) says that cost is real, hence this message.

## §2 The query contract (ready; no widget change requested)

One fixed literal over the channel you already use, question on stdin, one JSON document back:

```
tailscale ssh <remote_user>@<linux_host> '~/file-portal-src/linux-indexer/.venv/bin/python -m indexer.query'
```

Options ride on the literal if wanted: `--mode hybrid|vector|keyword` (keyword answers with no
model loaded), `--top-k N`, `--bundle <substring of the vault path>`, `--lane clean|scan`,
`--verdict pass|flag|fail|none`. `{"available": false, "reason": ...}` when there is no index;
otherwise `available`, `query`, `mode`, `filters`, `tip`, `reconciled_at`, `model`, `rerank`,
`levers`, `hits[]` with `bundle`, `note`, `source`, `source_sha256`, `heading`, `page_hint`
(1-based, nearest preceding figure, or null), `passage`, `text`, `score` (reciprocal-rank
fusion), `matched_by` (`vector`, `keyword`, `title` -- the bundle's filename/path, where an ISBN lives -- or a `+`-joined combination) and `rerank_score` when the
reranker lever is on. No paths, no sockets, nothing written, no LLM (P-4). Model load is a few
seconds cold; the Rust side sets no ssh timeout, so any caller runs it click-driven under
`spawn_blocking` (S59), never on the Room loop.

**Also on record, opt-in and off by default:** `python -m indexer.serve` is a loopback-only
(127.0.0.1) HTTP JSON endpoint with the same routes (`/health`, `/status`, `/query`), meant to be
fronted by `tailscale serve` -- the exact pattern docs/06 names for a new surface -- so the
dashboard, a phone window (docs/14 Phase A) or the widget can speak HTTP with the model kept
warm. No unit ships for it; Rab turns it on. **A search box would be the widget's first text
input -- a signature item (docs/33 §3.2 class). Not requested here; the contract is simply on
record.** `python -m indexer.status` prints the index-vs-vault tip comparison for MUSTER.

The embedding model is a lever (default all-MiniLM-L6-v2, 56 passages/s measured here; a multilingual sibling at 5/s for CJK-semantic search). The store is one SQLite file (`~/file-portal/index/index.sqlite`: bundles, passages, FTS5
keyword index, sqlite-vec embeddings). Anything on the Desktop that can read SQLite over the
tailnet could read it directly; the CLI/HTTP contracts above are the supported way.

## §3 What the ThinkPad still owes

Deploy is Rab's hand (`linux-indexer/scripts/install.sh`: both units, the timer, the
`post-update` hook). The `docs/20 §12` single-writer row for `receipts.jsonl` should read
"exporter · fixity · indexer (one `append_receipt` shape)" — amended on his word, not mine.
