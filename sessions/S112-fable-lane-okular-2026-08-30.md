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

## §5 Close terms (stated at open)

Digest lands as `docs/49-*`; most consequential finding hand-checked by the orchestrator,
differently-shaped, before it reaches Rab (docs/47 §4); relay entry written back before close;
commits touch only this lane's new files; no clock advance (S112 stays open, Codex lane holds
the close); glass/close.sh belong to the session close, not this lane sitting — said out loud
here rather than implied clean.
