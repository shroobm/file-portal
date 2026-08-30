# S112 · Fable lane record — the Okular commission — 2026-08-30

⟨claimed: Fable lane · occupant: Claude Fable 5 · S112 · 2026-08-30⟩

**This is a LANE RECORD inside the open S112, not a second S112 closeout.** The session record
is `sessions/S112-desktop-2026-08-28.md` (Codex lane, in progress on VW-E2-R2); its §8 records
Rab's post-Echo direction selecting continuation of S112, and the 2026-08-30 muster collision
stays observed, not concealed. This file exists so the Fable lane's intent is recorded before
work (docs/28 chokepoint) **without writing into a file the Codex lane holds uncommitted**.

## §1 Session Intent — Rab's commission, verbatim, unedited hereafter

> "I want you to run an investigation on the source code implementations of Popper and any
> other formatting and text reading tool. I want you to look at the repair bench and learn
> what can be utilized for ux, ease of use, ease of scan and reading, low latency, observable
> and useful features, that okular has directly. Also, Codex is owrk on a ticket, E2-R2...
> anyway. Do the complete search, orchestrate your agents based on file portal skills and
> orchestration contracts, and make your own fleet for okular. Do a thorough look at the code
> base, and make sure you can find everything you can digest into file portal for that
> effectiveness."

Mid-turn: *"Boot up for the session"*.

**Reading taken (stated, not echoed — Rab was away; autonomy in force):** "Popper" = Poppler
(Okular's PDF library; no Poppler source tree is on this machine — `ls Downloads | grep -ci
poppler` → 0 — so Poppler is covered through Okular's bridge + bounded web reading, tagged).
Deliverable = a research **digest** (docs/49, claimed by this lane via relay MSG-FAB-0044)
mapping Okular 20.08 mechanisms → File Portal adoption candidates, with citations. **No product,
pipeline, vault, bench, widget, or adoption change.** Adoption stays Rab's hand. Alternate
readings (implement bench changes now / research scoped only to feed VW-E2-R2) were considered
and set aside: no implementation verb appears in the commission, and the digest is the
prerequisite of both alternates, so nothing is lost if Rab meant either.

## §2 Starting state — `open.sh` card, verbatim

```text
════════ MUSTER · OPEN · 2026-08-30T06:22:16Z ════════
[0] IDENTITY
    ledger newest    S111  4e613696
    this session     S112  ·  desktop  ·  2026-08-30
    advisory         S112 is named in the INHERITED tree (4e613696) — read each, do not blanket-correct:
                     sessions/S111-desktop-2026-08-27.md 
[1] GROUND
    verifier         666AF259  (repo == ~/.claude)
──────── MUSTER · 2026-08-30T06:22:16Z ────────
[1] MEMORY ....... ✓ /c/Users/Bndit/.claude/projects/C--Users-Bndit-Documents-Claude-Code-Memory-Backup/memory/MEMORY.md
[2] SOFT clock ... ✓ 84 (tally == hook)
[3a] LEDGER ORDER  ✓ 94 Desktop-lane rows ascend (S16 → S111)
[3b] LEDGER PARSE  ✓ 94/119 rows parsed · 21 discarded, newest at row 21 · tail = last 5 · 4 other-lane: ThinkPad-S43 ThinkPad-S67 ThinkPad-S78 ThinkPad-S79
[3] HARD clock ... ✓ 4e613696 (S111) == ledger 4e613696, ancestor of HEAD
    WORKING TREE . 8 uncommitted · feat/library-pipeline
VERDICT .......... ✓ CLEAN — clocks reconcile
    muster exit      0
    origin           ahead 3 — unpushed local work; the close must push
[2] LIVE
    pipeline         held 5 · anchor 24 · pending 0 · drop 0
    levers           audit=enforce · analyst=local · batch=16
    gpu-lock         absent
    events           147 line(s)
    open-tasks       110 item(s) · last written 2 days ago  *** not written in 2d — is it still true? ***
    error-bin        45 row(s) — read the CLASS table before you probe · last written 2 days ago  *** not written in 2d — is it still true? ***
    symptoms         64 row(s), 26 open · last written 35 hours ago
    relay            90 entries · run `gate.py status` for the board
    widget           down (table read, no match)
    python procs     0
    ollama           2
    installed exe    4DCB73E2  (adoption is Rab's hand — docs/19 §0.3)
    vault            6 note(s) · tip 70c60e6
    thinkpad         UNREAD — host did not answer; NOT a statement that it is down or clean
[3] PIN
    --since          4e613696
    closeout         sessions/S112-desktop-2026-08-30.md
                     COLLISION — a closeout for S112 exists under a different machine/date
════════ mechanical half: INCIDENT (exit 1) — reconcile before work ════════
```

**Collision reconciliation (Observed):** `sessions/S112-desktop-2026-08-28.md` §8 records that
Codex's own 2026-08-30 muster hit this same exit-1 and that Rab's post-Echo direction selects
continuation of S112. This lane inherits that adjudication rather than re-deciding it.

Pinned reference for this lane's work: `4e613696` (the session pin; this lane's own first
commit is the opening commit of this file).

## §3 Register intersection (Phase 3b/4)

- Touched this lane: `coordination/relay.md` (append MSG-FAB-0044 + a close entry),
  `docs/49-*` (new), this file. OPEN-TASKS: one row will be added at close (digest review
  awaits Rab) — re-measured then. Everything else stays `Historical`.
- Symptom rows intersecting the commission (named, not acted on): **SYM-003** (table-loop
  disease — the bench is the response; this digest feeds the bench), **SYM-052** (no
  truncation in the md pane), **SYM-029** (CRLF discipline — this file is LF like other
  sessions files), **SYM-056** (delivered-markdown rendering damage — reading-surface
  relevance), register B22 (the ~1 s whole-file rebuild — the latency pain the Okular latency
  lane grounds against).
- Codex-lane in-flight paths this lane MUST NOT touch (Observed via `git status`):
  `.claude/skills/echo/lexicon.md`, `coordination/SIGNATURES.md`,
  `sessions/S112-desktop-2026-08-28.md`, `wiki/conversion-quality.md`, `.codex/`,
  `docs/48-visual-witness-evidence-contract.md`, `docs/contracts/`,
  `windows-converter/visual_witness_capture.py`. No push this sitting: S112 publication
  authority is already reserved to Rab in the Codex record; origin-ahead backlog is his call.

## §4 Fleet ground (measured by the orchestrator, 2026-08-30, per docs/47 §2)

Okular tree `C:\Users\Bndit\Downloads\okular-v20.08.0`: 896 files; core/=130, ui/=188,
generators/=351, shell/=11, conf/=41, mobile/=40, interfaces/=5, autotests/=45. Line counts:
core/document.cpp 5469 · ui/pageview.cpp 5100 · core/textpage.cpp 1876 · core/generator.h 811 ·
core/tilesmanager.cpp 675 · ui/pagepainter.cpp 1279 · generators/poppler/generator_pdf.cpp
1925 · part.cpp 3434. sha256 anchors: CMakeLists.txt `fb376b39…`, core/document.cpp
`60983f2a…`, ui/pageview.cpp `9a14e0ea…`. Generators present: chm comicbook djvu dvi epub fax
fictionbook kimgio markdown mobipocket ooo plucker poppler spectre tiff txt xps. The tree is
not a git repo checkout of this project; lanes read in place, read-only.

The bench ground: `prototypes/repair-bench/bench.html` read in full (1431 lines) this sitting
by the orchestrator, before the fleet was written.

## §5 Close terms (stated at open)  ⟵ §6 records how they were met

Digest lands as `docs/49-*`; most consequential finding hand-checked by the orchestrator,
differently-shaped, before it reaches Rab (docs/47 §4); relay entry written back before close;
commits touch only this lane's new files; no clock advance (S112 stays open, Codex lane holds
the close); glass/close.sh belong to the session close, not this lane sitting — said out loud
here rather than implied clean.

## §6 Outcome — 2026-08-30, second half of the sitting

- **Delivered:** `docs/49-okular-digest.md` (13 ranked candidates + ranked-out + pipeline
  extras, corrections, nulls, all-107 tables) · artifact "The Okular Digest" (same content,
  clickable v20.08.0 citations) · evidence dump **D0005** `sha256 981f2959…` (supersedes
  D0004 — pre-critic downgrade metadata + clumsy subject; noted, not concealed) ·
  OPEN-TASKS **A49** (SEMANTIC, Rab's) · relay `MSG-FAB-0044/0045`.
- **Instrument:** run `wf_61b440a5-0c1` — 8 sweep lanes (claude-fable-5; wave one's 7 audits
  died on the Fable usage cap), 7 audit lanes re-run on **claude-opus-5** (separate pool held),
  sweeps replayed from cache; then 1 Opus completeness critic over the digest itself.
  `Observed` totals from run notifications: 1,580,245 + 793,482 + 180,539 subagent tokens.
- **Audit:** 404 audit rows across the 7 code lanes, 404 MATCH / 0 DRIFTED / 0 NOT_FOUND;
  **popplerweb lane UNAUDITED** (12 findings / 36 citations, flagged wherever cited); 23 tag
  downgrades + 3 number corrections; dominant defect class = caller+callee-as-second-method
  (SYM-001 at fleet scale). Substantive falsifications caught: LAT-12 (swapped debounce
  labels; thumbnail scroll undebounced), TG-11 geometry (chars+space-rects, not words —
  port-critical), TG-13 newline placement, AU-01/AU-12 (incl. a stale comment in Okular's own
  source), S-01 non-streaming, S-06 dropped conjunct, LAT-04/GEN-11 fourth conjunct.
- **Critic (docs/47 binds the orchestrator too):** 22 defects filed against MY digest — 2
  CRITICAL (the 404/404 framing concealed the unaudited lane; the fourth-conjunct correction
  was dropped between my own hand-read and the text), 9 MAJOR (incl. the docdata size-in-key
  HAZARD my §1 had framed as a feature, and dropped findings OBS-10/tiles/S-03/08/11/14/TG-14),
  11 MINOR (incl. downgrade count 24→23 and my "differently-shaped" hand-check that was the
  same instrument). All folded into docs/49 + artifact before commit. My own §5 close-term
  "hand-checked … differently-shaped" was itself the overclaim — corrected in docs/49 §0, left
  standing above per appends-never-erase.
- **Boundary:** Okular tree read-only throughout; VW-E2-R2 paths untouched (Codex's two new
  selftest/verify files observed landing mid-sitting; distance kept); no push; no clock move;
  no wiki edit (conversion-quality.md is Codex-dirty — wiki re-stamp deferred to session
  close); registers: one row ADDED (A49), none struck.
- **Residue:** OPEN-TASKS.md carries 36 pre-existing lone-LF endings at HEAD (mixed-ending
  file; observed, not repaired — not this lane's row to fix without a word). Muster SKILL.md's
  "run close.sh at every close" not run this sitting: not a session close, SYM-064
  credential-hang hazard, push reserved — stated, not skipped silently.

§1 remains byte-identical.

⟨claimed: Fable lane · Okular digest complete · adoption remains Rab's · 2026-08-30⟩

## §7 Subsequent commission — OK-0/1/2/7 build, signed

Rab's words, verbatim: *"Do do quarantine only, just implement it. Signing on OK-0, OK-1,
OK-2, OK-7, use opus 5 models if you need"* then *"No just implmenet, no quarantine"*.

Reading: implement the four signed tickets directly in the live bench
(`prototypes/repair-bench/bench.py` + `bench.html`) — no quarantine copy, no flag-gating.
Scope stays bench-only: no pipeline, vault, widget, converter, or audit-verdict mutation; the
bench's existing safety layers (`.md.bench-bak`, append-only `manifest["repairs"]`, sandbox
and reading modes, loopback token) are preserved, and OK-0's UUIDs apply to NEW repair records
only — existing manifest entries are never rewritten. Every new behavior lands with its
tripwire in the same commit (docs/32 §6); the page harness (`test_bench_page.py`) and
`acceptance.py` must stay green. Opus 5 subagents authorized for verification lanes. Recorded
before the first code edit.

### §7.1 Build outcome (same sitting)

- **Shipped into the live bench:** OK-0 — `fpr-<uuid4hex>` identity on every NEW
  `manifest["repairs"]` record (three creation sites; legacy records untouched, enforced by
  test). OK-1 — per-book viewport store under a STABLE id (bundle `source_sha256[:16]`, or a
  sha16 of the PDF bytes in reader mode), jump history (page-change pushes, same-page
  overwrites, 100 RAM/10 persisted), ↶↷ + Alt+←/→, per-viewport Marks tab (★ / ✎ rename / ✕,
  identity-keyed), restore-on-open that still binds zone context (`selectZone(0, keepView)`).
  OK-2 — 120 ms-delayed dpi-30 placeholder with nav-token staleness guards. OK-7 —
  `/api/trimbox` GET (raster-measured box, corner-median paper estimate, +4% pad, 50% floor,
  cached; constants live at call sites) + CSS crop via `#pageinner` (overlay coordinates
  proven invariant), auto/manual-rect modes, reader-mode trim drags allowed.
- **Verification:** harness 45/45 (was 19; +26 tripwires, positive+negative controls each).
  3-lens Opus 5 adversarial review (run `wf_e9a94a09-a08`): 32 findings, 2 CRITICAL — the
  `#pagephold` author-`display` beating `[hidden]` (would have stuck the placeholder over
  every page; the in-file `.modal[hidden]` precedent corroborated it), and restore leaving
  `zone=null` so writes fell to `ctxRange` lines 1–40 ("folder mode" provenance, ✦ fix
  rewriting front matter). All confirmed findings fixed; the review also REFUTED my own
  same-URL-no-load-event theory with a spec citation (the cascade was the real mechanism —
  the phNav guard stays as hardening). Accepted-not-fixed, named: a benign extra history
  entry after a repair when saved page ≠ zone page; listener accumulation only on a
  permanently erroring raster.
- **Not done, said out loud:** no live-browser exercise (server not started — held bundles
  are Rab's hand; the JS layer is source-verified and reviewed, `Intended` until the bench
  next opens). `acceptance.py` not run this sitting (needs marker-env fitz + the sandbox
  copy of the real Valentine; the stdlib harness's live-wire tests cover the route layer).
- docs/22 §repairs schema updated (id field + the pre-existing collapse-mode drift).
