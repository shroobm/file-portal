# docs/37 — The Next-Stage Plan

*The operative work plan, born the night of 2026-08-17 (S86–S90): the two-machine
familiarization completed, the assistant went live, and Rab's ChatGPT-authored engineering
dossier ("File Portal — System of Operations", 42 pp, reviewing our exact HEAD `fc841a5`)
was read page-by-page and adversarially verified by an 11-agent workflow — 27 verdicts, every
one against quoted code. This document is the DISTILLATE: the next session reads THIS, not
the sources. Filed by S90; stages are Rab-signed only where §3 says so.*

## §0 Reading map — how a fresh session loads (≈10k tokens, not 100k)

1. **MUSTER first** (the skill does the mechanical open; MEMORY.md TIME-STATE carries the
   session arc). 2. **This document.** 3. Nothing else up front. Deeper sources BY POINTER,
   only when a task touches them:

| Source | When to open it |
|---|---|
| `docs/36-repository-briefing.md` | system orientation (it is also assistant corpus) |
| `SYMPTOM-INDEX.md` | before touching anything a row names |
| The dossier PDF: `C:\Users\Bndit\Downloads\File_Portal_System_of_Operations.pdf` | almost never — §2 is its verified distillate; re-read only if a §2 row is challenged |
| `sessions/S85…S90-*.md` | the assistant arc's details (corpus, budget, guard, config mirage) |
| Full verification evidence | S90's chat-session workflow journal (off-repo); §2 carries the load-bearing quotes' conclusions |

**Do not re-verify §2's verdicts from scratch** — they are code-verified at `fc841a5` with
file:line evidence. Do re-measure (muster Phase 3) anything a stage is about to EDIT.

## §1 The five stages

**Stage 0 — the truth repairs** *(Python + docs, no widget rebuild, no adoption)*
docs/35 drift ×4 (add `ask`; chunk lever = CONVERTER's Marker batch, menu 8/16/32; events.rs
is the READ side; fidelity enum gains `flag`) then **re-measure the corpus fit** (the
room_chat.py:293 comment's own rule) · **F-09** per Rab's §3 signature · `.done` reads what
it writes (compare `source_sha256`+`batch` at resume; add engine args + Marker version to the
record) · events.py gets SYM-037's torn-line healing · analyst.py drops curl for urllib (key
off argv, CWE-214) · index honesty: refresh SYM-032's stale text, file rows for F-09 and the
no-lock resume blind spot, write the real docs/08 transport entry.
*Exit: suites green · corpus re-measured · the index no longer lies about anything we know.*

**Stage 1 — the hardening slice** *(ONE widget build + Rab's adoption)*
CSP set + devtools out of release (test every surface — the chat window loads localhost) ·
bless via config (assay.rs literal) · render `spot_check` / `degeneration_flagged` /
`fixity-check` receipts · `recent_audits` rendered or dispositioned · **[signed 2026-08-17, §3.2]**
single-instance guard + named OS mutex around the Marker launch (SYM-033 prevention; the
mutex also covers `--resume`/manual runs the file-gates cannot see).
*Exit: ritual green · SHA-8 staged · Rab's hand · every new guard stepped on.*

**Stage 2 — converter tests + CI** *(the decision with two witnesses)*
Pure-seam suite: probe routing, frontmatter, estimate math, supersede take/stamp, clamps,
PLUS the dossier's negative cases (corrupt/mismatched `.done` rejected · enforce-hold
exception paths · asset tripwire · out-of-range posture per Rab's warn-vs-fail word).
Windows CI job. *Exit: the riskiest code cannot regress silently.*

**Stage 3 — the verified seam** *(two-machine, coordinate over the bus)*
`inventory.json` (per-file SHA-256) at bundle build, BOTH lanes · exporter verifies inventory
BEFORE commit (L12 verifies after; both stay) · receipt binds package digest · ONE acceptance
function for every ingest path (new/duplicate/supersede/repaired), policy carrying the SIGNED
report-mode semantics. *Exit: negative matrix green on both machines · one restore drill.*

**Stage 4 — the product**
The four held books through the Bench (guided Valentine first) · Rab's remaining ten
assistant questions (corpus-vs-retrieval verdict) · SPOT_CHECK_EVERY tuned · optional:
mini ground-truth corpus (a stratified handful of transcribed pages, real CER/WER once;
"survival" retires into honest triage).

**Parked with re-entry criteria** — SQLite state store, CDG/adapter platform, format
expansion: re-open ONLY if (a) a real 1,000-page zero-loss mission is commissioned, (b)
formats beyond PDF/EPUB/DOCX are signed, or (c) an interruption loses data the Stage-0–3
invariants should have caught. Then the dossier becomes the design's starting text, judged
against docs/10 in a dedicated design session.

## §2 The dossier, verified — digest of 27 verdicts

CONFIRMED = new + real. PARTLY = real but resized. KNOWN-SIGNED = true and already Rab's
recorded choice.

| ID | Verdict | The truth (one line) | Where | → |
|---|---|---|---|---|
| F-01 | PARTLY | "no process checks .gpu-lock" is WRONG (5 gate readers since S83–S85); converter-vs-converter gap = SYM-033; NOVEL: `--resume`/manual runs write NO lock — invisible to all gates | watch_and_convert.py:159; room_chat.py:303; assay.rs:276; convert_and_ship.py:1120-22 | St.1 mutex |
| F-02 | PARTLY | `.done` presence-trust real; source IS path-bound (sha16); config/model UNBOUND — batch/Marker change mixes slices silently; `.done` already records what nothing reads | convert_and_ship.py:731, 757-59, 769-73 | St.0 |
| F-03 | KNOWN-SIGNED | fails-open = docs/15 §12 + docs/30 §5.4 signatures; since S78 a fail never ships SILENTLY (`_raise` outside the try); the except→ship handler itself never separately signed | convert_and_ship.py:296-339 | note |
| F-04 | KNOWN-SIGNED | exporter verdict gate is supersede-only BY signed design (docs/30 §3.3 names the hole); residual: `exported` receipt carries no verdict; hand-dropped staging bypasses all | exporter.py:255-257, 317-404 | St.3 |
| F-05 | PARTLY | cat-hop = signed tradeoff BUT its docs/08 pointer DANGLES (entry never written); tar truncation overstated; real gap: no arrival inventory, L12 authenticates after commit | transfer.rs:11-12; convert_and_ship.py:939-63 | St.0+3 |
| F-06 | PARTLY | best-effort append = recorded design; writers = watcher + convert instances; SYM-037's healing exists in-repo, never applied to events.py | events.py:17-31 | St.0 |
| F-07 | PARTLY | ledger-before-completion confirmed; BUT the row records GPU cost, complete at append — estimator arguably MORE truthful; residual is spec wording | convert_and_ship.py:891-92 | note |
| F-08 | PARTLY | collision prevented by absolute numbering (SYM-002) + loud tripwire; residuals: no overwrite check at copy sites, non-`_page_N_` names bypass, warn-vs-fail unsigned | convert_and_ship.py:741-56, 781 | St.2 |
| F-09 | **CONFIRMED** | lever read ONCE per book; docs/18+20 and line.rs promise per-slice — projection-law violation, ours | convert_and_ship.py:711,718 vs loop 729+ | St.0 + §3 |
| F-10 | fair | survival is triage, never accuracy — keep the vocabulary clean (docs/34) | fidelity_audit.py | St.4 |
| F-11 | PARTLY | anchor-before-hold confirmed but anchor is archaeology, not acceptance; degraded path: vault_count falls back to anchor count; BONUS: `recent_audits` rendered by NOTHING (SYM-027 specimen); survival-avg blend already filed = docs/26 F5, awaiting the sheet | room.rs:100-104 | St.1 |
| F-13 | **CONFIRMED** | Gemini key in curl argv (CWE-214); our docstring claims a safety argv undercuts | analyst.py:126-131 | St.0 |
| F-14 | **CONFIRMED ×2** | CSP null (scaffold default, never chosen — and the webview now renders MODEL OUTPUT incl. the withheld fold, `__TAURI__` exposed); devtools cargo feature ships in RELEASE (CHANGELOG rationale was dev-scoped) | tauri.conf.json:23-25; Cargo.toml:11 | St.1 |
| F-15 | KNOWN-SIGNED | linux no per-conversion deadline = recorded S78 decision; nuance: pandoc HAS timeout=300; pymupdf4llm runs IN-PROCESS (a subprocess timeout wouldn't help) | linux main.py:320-28 | parked |
| F-16 | **CONFIRMED** | DOCX born-digital by definition — image-only DOCX bypasses probe, yield gate, and OCR entirely | linux main.py:126-28 | St.3-adjacent, ThinkPad lane |
| F-17 | **CONFIRMED** | bundle publish: no fsync, no artifact inventory; the ANCHOR copy is never verified by anything, ever; L12+fixity authenticate possibly-damaged bytes forever | bundle.py:135-141 | St.3 |
| F-18 | PARTLY | census 67 unsigned @ 76 sites CONFIRMED exactly (known SYM-027 backlog); their "28/29 acceptance" CONTRADICTED — we run **33/33** at the same HEAD | observability/ | note |
| F-19 | confirmed | windows-converter absent from CI — the S86 item-7 decision, second witness | ci.yml | St.2 |
| F-20 | **CONFIRMED ×4** | docs/35 drifts: `ask` omitted · chunk lever wrong consumer+domain · events.rs called a writer (read side; contradicts single-writer law) · enum missing `flag` — THIS IS ASSISTANT CORPUS | docs/35:58,62,76,100 | St.0 |
| C02 | KNOWN-SIGNED | deferral gate real + signed (docs/33 §2.3); honest caveat: cooperative check-then-act, ms-wide double-proceed window; perimeter excludes non-watcher runs | watch_and_convert.py:104-149 | St.1 mutex |
| C25/C26 | PARTLY | line_state 20-key / room_metrics 7-key lists EXACT for the configured arm; both have a second `available:false` shape any frozen contract must carry; docs/16's `uptime_s` designed, never built (doc stale) | line.rs:159-89; room.rs:18-20,106-14 | note |
| AppB | CONFIRMED | exactly 42 commands, one registration site | main.rs:615-658 | — |

## §3 Signature register (Rab's, all OPEN at filing)

1. **F-09 semantics**: re-read per slice (honors the signed promise; the lever exists for
   mid-book VRAM steering, S60) ~or~ immutable-per-job (dossier's reproducibility argument).
   Fable recommends per-slice. **SIGNED per-slice (Rab, 2026-08-17, in-chat: "F-09
   per-slice signed") — built S94.**
2. **SYM-033 prevention + named mutex** (Stage 1's third bullet). **SIGNED (Rab,
   2026-08-17, in-chat: "Stage 1 GO with the mutex") — built S94.**
3. **Asset posture**: warn (today) vs fail/quarantine on out-of-range (Stage 2 encodes it).
4. Stage 2 GO · Stage 3 GO.
5. Standing from before tonight: docs/26 signature sheet (5) · stale-hold reap countersign ·
   docs/34 rule 8 · GLM second-reader · wrapper · SPOT_CHECK_EVERY 10→3–5.
6. **Conversion-completeness slate** (filed S97, 2026-08-20; full decision frames = docs/41;
   expands item 3's Stage 2 asset posture — docs/37 §1 line 50 already queues the asset
   tripwire there). P-0 wiring: render `asset_delta`+`embedded_images` on the Assay card ~or~
   sign them REPORT-silent (they are 2 of the glass detector's 64 live glitches). P-1
   figure/vector coverage audit: host in-converter at :998 (zero plumbing, extends card-lock)
   ~or~ out-of-band desktop re-score (no lock cost, can back-fill anchor/) ~or~
   ThinkPad-with-shipped-inventory (bundle-contract change); instrument PyMuPDF-only ~or~
   admit a JVM for PDFFigures 2.0; coverage-by-bbox-overlap semantics; report-only first
   (`audit-mode.txt` is LIVE at `enforce` — a gate parks books day one). Fable recommends:
   P-0 render now; P-1 in-converter, PyMuPDF-only, report-only.
7. **#598 tripwire** (figure transmuted to prose; live specimen `bojieli` 105 rasters → 4
   assets, degeneration clean, verdict `flag`): join docs/15 §12's fail list (a signature
   event — §12 is SIGNED at exactly two fail signals) ~or~ flag-only localizer ~or~
   receipt-note-only if a prose'd chart is acceptable for a text-first vault. Fable
   recommends flag-only until §9 calibration shows the false-alarm rate. Depends on item 6's
   P-1.
8. **DPI operating point**: measured probe on the already-clipped book (Beer DIAGNOSING —
   layout ceiling 87.1 DPI vs the 96 default; grounding measured corpus headroom −9 %…+228 %,
   geometry-determined) ~or~ per-page render-to-the-budget (the real lever, a converter
   change) ~or~ leave it and record why. A global DPI bump is the wrong shape. Fable
   recommends the one-book probe first; SYM-039's derived `ocr_dpi` stamp must be reworked in
   the same commit as any override.
9. **Generative-SR standing ban** (fabricated glyphs are fluent — invisible to every gate we
   own): record force_ocr-style ban ~or~ deferred-with-criteria (ground-truth set + no-SR
   diff lane) in docs/15 §10. Zero code either way.
10. **The echo skill** — the prompt-echo protocol mechanized: full-context sweep + append-only
    terminology lexicon + readings/preview/deltas before interpreting a deep commission, stop
    for his word. **SIGNED Reading B (Rab, 2026-08-20, in-chat: "YES YES YES YES IT IS
    READING B, GO DO THAT SHIT CLAUDE!") — built S98** (`.claude/skills/echo/`, selftest 5/5,
    live sweep stepped on; lexicon in from day one per the recommendation his GO landed on).
11. **The claim convention + the relay** — authorship stamps on sections/rows/commits, the
    co-authored parallel-sitting record, and the append-only UTC LLM-to-LLM relay where each
    model carries the other's message + suggested prompt to Rab at open ("two signals as
    one"). **SIGNED A+B+convention (Rab, 2026-08-20, in-chat: "A+ B with a convention… user
    always gets 2 signals as one for coordination", + "They should record these messages in
    UTC") — built S99** (coordination/authorship.md + relay.md, docs/43, both bootstraps,
    muster standing orders; Codex's claims + relay reply are the open half, invited).
12. **The concordance amendment** — carrier labels every carry `agree`/`conflict`/`unverified`
    (unverified the DEFAULT; unlabeled = violation) · carried text must-quote, never
    paraphrased · a `conflict` **must name the probe that settles it**, runnable by either
    model or its agents, so factual disputes end at measurement and only judgment/priorities/
    authorization reach Rab · never impersonate. Debated across two ChatGPT relays (it
    endorsed; endorsement is discussion, not authority). **SIGNED (Rab, 2026-08-20, in-chat:
    "Sign it, and then lets run a test") — built S100** (`coordination/relay.md` §amendment +
    `coordination/selftest.sh` 11/11, whose first run went red on its own bad assertion).

## §4 Stage 0 pre-mortem — deviations solved ahead of the curve (S92)

*Each Stage 0 task, its known trip points, and the recourse — so the next instance executes
instead of discovering. Facts marked `Observed S92` were verified at filing.*

**T1 · docs/35 fixes ×4** — trips: (a) docs/35 is CORPUS → after editing, RE-MEASURE (the
recipe, verbatim — assemble then tokenize):
`marker-env python -c "import sys; sys.path.insert(0, r'C:\...\windows-converter'); import room_chat; t,_=room_chat.load_corpus(); open(OUT,'w',encoding='utf-8').write(room_chat.SYSTEM+'\n\n'+t)"`
then `C:\Users\Bndit\ml\llama\llama-tokenize.exe -m <qwen3 blob> -f OUT --show-count` (blob
path: read `~\.ollama\models\manifests\registry.ollama.ai\library\qwen3\8b`, layers→model
digest→`blobs\sha256-<digest>`; if the model is gone, measure with the vocab of whatever
model the assistant actually runs, and say so — docs/34 conditions). (b) If the number
moves, THREE stale sites cascade: `room_chat.py:293` comment · docs/36 §4.E · docs/36 §7
risk row. (c) Section numbers in docs/35 should not shift (citations resolve per-doc; §N is
display, but stability is free). (d) Corpus edits reach the assistant only at Rab's next
widget restart — tell him to restart ONCE, after Stage 0 closes, and then do the fourth ask.
(e) Run `room_chat_acceptance.py` after (24/24 expected; it re-loads the corpus).

**T2 · F-09 re-read per slice** *(only with Rab's signature in his prompt; absent → do the
rest, leave F-09 flagged, never guess)* — move the `chunk_batch()` read + `_with_batch`
inside the slice loop. Trips: (a) the `chunking` event (~:721) reports the run-start value —
fine, each slice's print/`.done` carries its own. (b) No suite exists yet (Stage 2): verify
by py_compile + review; the fix ships `Intended`, exercised at the next real chunked
convert — SAY SO in the closeout, no over-claim. (c) DESIGN TENSION with T3, resolved in
advance: batch is a PERFORMANCE knob (VRAM/speed), not an output-identity input — T3 must
NOT gate resume on batch equality, or a mid-book lever change (the very point of F-09)
invalidates good slices. Record batch for forensics; gate on identity only.

**T3 · `.done` identity** — at the skip branch (~:731): parse `.done`; re-convert the slice
(loudly) if `source_sha256` mismatches or if new identity fields (engine `extra` args,
Marker version — reuse the existing `import marker` provenance) mismatch. Do NOT gate on
`batch` (see T2c). Legacy `.done` files lacking new fields: **moot — `.chunk-work` is EMPTY
(`Observed S92`)**, no interrupted run spans the upgrade; still code the missing-field case
as re-convert-and-log (cheap, correct for the future).

**T4 · events.py torn-line healing** — port `append_receipt`'s last-byte check (SYM-037).
Trips: emit() is hot — the check is one `seek(-1)` read, keep the never-raise contract.
**A guard born today gets its tripwire today**: a ~15-line `events_selftest.py` (seed a torn
file, emit, assert both lines parse) ships in the same commit; Stage 2 absorbs it later.

**T5 · analyst.py urllib swap** — replace the curl subprocess with urllib (room_chat's ask()
idiom); key goes in the Request header object, off argv. Trips: (a) PRESERVE the free-tier
pacing + 3-retry backoff semantics exactly — they are load-bearing (rate limits). (b) TLS:
curl bundled its own trust; stdlib ssl must prove itself — probe once in-session with a
keyless request to the Gemini endpoint (expect a 4xx JSON, which proves TLS + reachability
without spending a key call); if TLS fails on this box, STOP and file rather than shipping a
broken swap. (c) Error mapping: HTTPError/URLError → the existing backend-failure path
(original text kept, not journalled). Ships `Intended` + TLS `Observed`; first real Gemini
run completes the proof.

**T6 · index honesty** — SYM-032 refresh (append a dated status update; the index is
append-only in spirit — never rewrite the row's history) · new rows for F-09 and the
no-lock-resume blind spot: **next free IDs are SYM-041/042 (`Observed S92`; re-verify by
grep before writing — the fork lesson)** · the real docs/08 transport entry (read docs/08's
format first; transfer.rs:11-12 and docs/01:91 point at it). ALL of these files may be CRLF:
Edit tool or `sed -b`/`printf '%s\r\n'` appends; verify `CR==LF` counts after (SYM-029).

**Cross-cutting recourse:**
- **Commit per task**, not one omnibus — an interrupted session then loses nothing (context
  exhaustion mid-session is survivable by design).
- **CI**: expect green; the S91 fix removed all third-party action downloads. If red: `gh`
  is UNAUTHENTICATED on this box — the working route is the stored git credential:
  `TOKEN=$(printf "protocol=https\nhost=github.com\n" | git credential fill | grep ^password= | cut -d= -f2)`
  then the Actions REST API. `head_sha` filtering needs the FULL sha (S91 §10.1 was this).
- **GPU**: Stage 0 is CPU-only (llama-tokenize included). Rab's widget/model: untouchable.
- **Origin at open**: the ThinkPad may have pushed (their reply asked them to pull/adopt) —
  a `behind N` row means pull first, and their lane's rows are lane-filtered noise to the
  clock, by design.
- **config.toml**: Rab's-hand territory, always (docs/37 §4).
- **Rab's sequencing**: close Stage 0 → he restarts the widget once → fourth ask. If the
  fourth ask is withheld AGAIN: the raw is in the fold and `room-chat-withheld.jsonl` —
  diagnose from evidence, not reproduction.

## §5 Live-state notes a fresh session must not re-derive wrongly

- Assistant: adopted exe `6CA0DEF0`; corpus = docs/20+35+36, fit **13,076/16,384 tok**
  (re-measured S93 after the Stage 0 docs/35 repairs; re-measure on ANY corpus change);
  `max_tokens=2048` fix is ON DISK — **live only after
  Rab's next widget restart**, and his fourth ask of the engineer question is still pending.
- `config.toml` is Rab's-hand/widget-verified territory — a packaged session reads its own
  MSIX mirage on that path, permanently (SYM-007 4th firing; verify via widget boot log).
- Session numbers are machine LANES; symptom IDs one namespace; **the close pushes**.
- ThinkPad lane owes: pull + `MUSTER_LANE` adoption + its untracked CLAUDE.md counts
  (coordination reply 2026-08-17T03-05); F-16 lands in its lane.
