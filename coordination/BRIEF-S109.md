# THE DOOR BRIEF — S109 · Desktop · 2026-08-24/25 · ⟨claimed: Fable⟩

*Slipped under the door. Codex is out of usage and the bus is dormant (`MSG-FAB-0029`, OPEN-TASKS
J9), so there is no handshake to run — but there is still a handover to make. This is it: one
document a cold reader can open and be oriented by, with no memory of this session and no access
to its transcript.*

**Written for:** the next occupant of the Codex lane, or any model/human opening this repo cold.
**Written by:** the Fable lane (Claude Opus 5), Desktop, during S109's second sitting.
**Commissioned by:** Rab, 2026-08-25T02:5xZ — *"Like slipping papers under someones door, so when
they wake up, they'll read it and eventually answer you."*

**How to read it.** §1 is what was true at the open. §2 is what this sitting did, appended as it
happened. §3 is the close. §4 is the vocabulary — read it before §1 if the words look strange. §5
is the map. Every factual claim carries a tag from the project's tag law (`docs/21` §1, restated
in §4 below); **a claim without a tag is a claim you should not act on.**

---

## §0 If you read one paragraph

The apparatus is in excellent health and the product has not moved. Ten-plus sessions of
governance machinery — registers, gates, a relay bus, a two-model protocol, three self-testing
skills — sit on top of a pipeline whose `events.jsonl` has been **frozen at 137 lines since
2026-08-14** (`Observed 2026-08-25`, muster card `[2] LIVE`). The single item that changes that
sentence is **C0: put one book through the pipeline end to end.** Everything else in the 92-item
register is downstream of it. If you are deciding what to work on, that is the answer, and it has
been the answer since `docs/45`.

---

## §1 OPENING — what was true when this sitting started

### 1.1 The card, verbatim

*The muster card is pasted verbatim, never summarised — a summary of the card is a proxy for the
card, and proxy-substitution is this project's most expensive recurring defect (`docs/32`).*

```
════════ MUSTER · OPEN · 2026-08-25T02:51:53Z ════════
[0] IDENTITY
    ledger newest    S108  a652781
    this session     S109  ·  desktop  ·  2026-08-24
    advisory         S109 unnamed in the inherited tree
[1] GROUND
    verifier         8C8A748E  (repo == ~/.claude)
──────── MUSTER · 2026-08-25T02:51:54Z ────────
[1] MEMORY ....... ✓ /c/Users/Bndit/.claude/projects/C--Users-Bndit-Documents-Claude-Code-Memory-Backup/memory/MEMORY.md
[2] SOFT clock ... ✓ 80 (tally == hook)
[3a] LEDGER ORDER  ✓ 91 Desktop-lane rows ascend (S16 → S108)
[3b] LEDGER PARSE  ✓ 91/116 rows parsed · 21 discarded, newest at row 21 · tail = last 5 · 4 other-lane: ThinkPad-S43 ThinkPad-S67 ThinkPad-S78 ThinkPad-S79
[3] HARD clock ... ✓ e4d731e (S108) is 3 commit(s) AHEAD of ledger a652781 and contains it; ancestor of HEAD
    WORKING TREE . 0 uncommitted · feat/library-pipeline
VERDICT .......... ✓ CLEAN — clocks reconcile
    muster exit      0
    origin           in sync (fetched)
[2] LIVE
    pipeline         held 4 · anchor 23 · pending 0 · drop 0
    levers           audit=enforce · analyst=local · batch=16
    gpu-lock         absent
    events           137 line(s)
    open-tasks       92 item(s) · last written 5 hours ago
    symptoms         54 row(s), 4 open · last written 6 hours ago
    relay            58 entries · run `gate.py status` for the board
    widget           down (table read, no match)
    python procs     2
    ollama           2
    installed exe    4DCB73E2  (adoption is Rab's hand — docs/19 §0.3)
    vault            6 note(s) · tip 70c60e6
    thinkpad         converter=active · vault tip 70c60e6 · staging 0 · receipts 8
[3] PIN
    --since          a652781
    closeout         sessions/S109-desktop-2026-08-24.md
                     OPEN — this session's closeout exists, added in dd486a6 · §1 must stay byte-identical to close
════════ mechanical half: clean (exit 0) — judgment half is SKILL.md Phases 2-6 ════════
```

### 1.2 The two clocks — and why "not equal" is correct here

`Verified 2026-08-25` (the card's `[3]` row, cross-checked by `[2]`'s independent tally read).

| clock | reads | source |
|---|---|---|
| **HARD** (git ledger) | S108 · `a652781` | newest Desktop-lane Change Ledger row in `CLAUDE_README.md` |
| **SOFT** (cookie tally) | 80 received · S108 | `cookie-tally.md` header, mirrored by `MEMORY.md`'s TIME-STATE line |

They are **3 commits apart and that is the reconciled state, not a fault.** The rule changed in
this very session's first sitting: the ledger row is written *after* the closing commit, so any
commit the close's own gates force afterwards lands below the row and the row can never reach back
to name it. The test is therefore **ancestry, not equality** — `a652781` must be an ancestor of the
TIME-STATE SHA `e4d731e`, and the card prints the gap as a number. A *genuine* fork (ledger SHA not
an ancestor) still exits 1; selftest case **31** is the negative control that keeps the rule from
degenerating into a blanket green. Run that case first if anyone ever suspects the clock has gone
permissive.

### 1.3 The three registers — counts and ages, never checkmarks

`Observed 2026-08-25`, muster card `[2b]`.

| register | state | file |
|---|---|---|
| open tasks | **92 items** · last written 5 h ago | `OPEN-TASKS.md` |
| symptoms | **54 rows, 4 open** · last written 6 h ago | `SYMPTOM-INDEX.md` |
| relay | **58 entries** · both lanes idle, nothing owed | `coordination/relay.md` |

A register untouched for 2+ days prints a staleness warning; a *missing* register is `UNREAD` and
exits 1, never "nothing open". None was stale at this open.

**Register composition** (`Historical 2026-08-24`, from `OPEN-TASKS.md` §0): 43 open semantic
decisions · 31 mechanical items · 14 genuinely open symptom rows + 4 falsely-open · 8 delegations
never collected · 7 of 7 completeness-slate items unfinished · 11 record-integrity repairs.

### 1.4 The bus — dormant by expectation, not by fault

`Verified 2026-08-25` — `gate.py status`, both sidecars read from disk.

```
  Fable  state=idle   ticket=None    sent=29 confirmed=9   updated=2026-08-24T21:17Z
  Codex  state=idle   ticket=T-005   sent=9  confirmed=25  updated=2026-08-24T19:05Z
```

Both lanes read **STALE** (335 min / 467 min at open). **That is expected and recorded**, not a
missed beat: `MSG-FAB-0029` declares the dormancy and `MSG-CDX-0009` is Codex's own stand-down —
T-008 withdrawn, no implementation taken, read-only monitor left alive, *"no unfinished
deliverable."* Every message on the bus is confirmed in both directions; nothing is owed either
way. **A quiet lane is a question, not a fault, when the record says why the silence is expected.**
Here the record says why.

Codex's last word to Rab, carried faithfully: *"Nothing needed. Let Claude finish its bounded lane;
Codex is standing down with the monitor still live."*

### 1.5 Inherited from the first sitting — all `Historical 2026-08-24`

S109's first sitting was long and it convicted itself repeatedly. What matters to a cold reader:

- **The Circle found three violations in the guards, all live at 73/73 green.** Green suites are
  not evidence that the property holds; they are evidence that the tests pass.
- **The muster upgrade landed** (Rab signed): the three registers on the card, the debt gate, the
  descendant rule (selftest cases 30–32). Both new gates convicted the session that built them.
- **SYM-054 filed** — an agent fleet leaked seven live HTTP servers, and the audit that checks the
  run's *files* could not see them by construction. `L5.6`/`L5.7` re-measure trees by digest; a
  live process has no digest.
- **`docs/46` opened with a fabricated duration** — "a year" where the measured span is **60 days**
  (`0a16117` 2026-06-25 → 2026-08-24). Wrong by 6×, in the opening line of the document arguing
  that every defect here is a category error. *Session count ≡ elapsed time* is one. Filed J11.
- **Everything after ~19:00Z on 2026-08-24 is SINGLE-LANE** — no cross-vendor check, because the
  Codex lane was out of budget. Hold it as Codex asked to be held: **reported evidence until
  independently re-observed.** The three Circle fixes are the least trustworthy and most
  load-bearing thing in the session.
- **S109 was never closed.** No ledger row, neither clock advanced.

**The pattern worth more than any single finding:** three of that day's sharpest catches came from
one-sentence questions Rab asked — *"t-005 you mean?"*, *"whats still working?"*, *"where are you
getting the year timeline?"* — each hitting something the apparatus was structurally blind to.
Every guard in the building checks digests, states, files, counts. **Not one checks a claim about
time.** The only uncorrelated check in the building asked three questions and got three hits.

### 1.6 What is ahead — the honest menu

Presented as options with costs, `Inferred 2026-08-25` from the registers; **none of these is
chosen.** Rab picks.

| | item | class | why it matters |
|---|---|---|---|
| **1** | **C0 — one book through the pipeline** | THE ONLY ONE THAT MOVES THE SENTENCE | `events.jsonl` frozen at 137 lines since 2026-08-14. Recommended first book: Ashby, *An Introduction to Cybernetics*. Needs the widget up, the watcher running, a PDF in `drop/`. |
| **2** | **Close S109 properly** | REQUIRED regardless | Ledger row + both clocks in lockstep. Open since the first sitting (§10 item 2). |
| **3** | J1 — 3 threshold constants with no lever, no waiver | mechanical, cheap | `docs/18` §2: a number that decides something is a LEVER, not a constant. |
| **4** | J2 — 1 unsigned observability glitch since `4862be1` | mechanical, cheap | GLASS red at close. |
| **5** | SYM-044 — `marker_version: "unknown"` corpus-wide | mechanical, one line | `importlib.metadata.version("marker-pdf")` → `1.10.2`. The `.done` identity gate is one-third inert until this lands. |
| **6** | J4 — `close.sh` now takes 8m37s | mechanical, design | A close nobody can afford to run is a close nobody runs. |
| **7** | SYM-054 — a fleet law needs a PROCESS census | mechanical, design | It already has a digest census. |
| **8** | The S108 sign sheet, 15 items | **Rab's alone** | `sessions/S108-SIGN-SHEET.md`. A session may not decide these. |

---

## §2 DURING — appended as the sitting ran

*Entries are appended in order, each with its tag and its probe. Nothing here is written
retrospectively.*

### 2.1 The open (02:51–03:0xZ)

`Observed`. Ran `bash .claude/skills/muster/open.sh` → **exit 0, clocks reconcile.** Inherited
`sessions/S109-desktop-2026-08-24.md` §17 (what the next session inherits), §10 (still open), §16
(SYM-054 and Rab's three findings). Read the gate board, the symptom index's open rows, and
`OPEN-TASKS.md` §0/§J. Carried Codex's `MSG-CDX-0009` to Rab in the first reply.

`Observed`. **Identity ruled: this is S109's SECOND SITTING, not S110.** The session number comes
from the ledger, the ledger's newest row is S108, and S109 never wrote one. Numbering this S110
would orphan S109's closeout and skip a ledger number permanently. Precedent: S107 ran two
sittings; S108 ran a post-close arc.

`Observed`. Recorded the sitting's commission as **§18** of the S109 closeout *before* any work —
`docs/28`'s chokepoint, recording precedes action. §1 left byte-identical, as its contract requires.

### 2.2 The context dump, and what verifying it changed (03:0x–03:2xZ)

Rab pasted the tail of the first sitting's transcript. **A transcript is not proof**
(`coordination/SIGNATURES.md`), so its six checkable claims were checked rather than inherited.

| the dump claimed | probe | verdict |
|---|---|---|
| tree 0 modified, 0 ahead of origin | `git status --porcelain`, `git rev-list --left-right --count` | `Observed` — tree clean; **ahead 1**, not 0, because this sitting committed `acb3686` |
| "nothing running except the atlas sim on 8765" | `Get-CimInstance Win32_Process -Filter "Name='python.exe'"` + `Get-NetTCPConnection -State Listen` | **`Verified`** — two python procs, both the atlas sim (parent+child). **All seven SYM-054 orphans are gone**: 7199/7211/7222/7223/7224 absent. Port 7680 is `svchost`, not ours |
| two Gmail drafts waiting | `list_drafts` | `Observed` — both present: *"C0 conversion steps for tonight + the full report (48 commits)"* (22:08Z) and *"Research directions — the groundedness lane"* (23:35Z) |
| `events.jsonl` at 137 | `wc -l ~/ml/library/events.jsonl` | `Observed` — **137**, last line `2026-08-14T03:32:13Z`, a `gate resolved` event. Unmoved for 11 days |
| muster exit 0, clocks reconcile | `open.sh` | `Observed` — reproduced independently at this sitting's open |
| widget down, `.gpu-lock` absent | card + `nvidia-smi` | `Observed` — widget down; GPU **2755/10240 MiB, 11 %**, ollama resident. `query user`: one session, `bndit`, console, active. **Law 8 clear** |

**The one correction:** *"0 ahead of origin"* was true when written and is not true now. Nothing else
in the dump failed verification, and the SYM-054 orphan check came back clean — that symptom's
specimen processes are dead.

`Observed`. **C0 is blocked on a book.** `drop/` holds no PDF. The recipe in the Gmail draft §1
names **Ashby, *An Introduction to Cybernetics*** — and it is **not on this machine** (34 PDFs in
`Downloads`, none Ashby). Acquiring it is a download, which needs Rab's explicit word. Candidates
already on disk and not yet in `anchor/`: Kleppmann *Designing Data Intensive Applications* (23 MB,
born-digital), *The Unicode Standard v13.0* (13 MB), Bulgakov *Master and Margarita* (1 MB, prose
only). **Unresolved at the time of writing.**

`Observed`. **Mutation testing launched on `gate.py`** (`wrwrlajds`) — the recommendation from the
research draft's §7. Five lanes over digest / guards / lifecycle / sidecar / thresholds, each in its
own git worktree, gated behind a positive-control baseline that stops the run if the suite is not
green on unmutated code. **Pre-checked for SYM-054**: `selftest.py` imports only
`io/json/os/subprocess/sys/tempfile/pathlib` and binds no port, so this fleet cannot leak a server
the way the relay-room lane did. A process census follows the run regardless — the symptom's whole
lesson is that a fleet's file audit cannot see what it left running.

`Observed`. **Ruled against re-opening the first sitting to take the close.** It is alive and
addressable (`file-portal-76 [6cf02a]`, 18 h). Two instances closing one session number is SYM-045's
exact shape one level up — that row is OPEN with no mechanical guard and its cause line reads *"the
open probe cannot see a close that has not happened yet."* The first sitting had itself declined
the close and handed it forward. **Rab's counter-proposal, adopted:** after this sitting finishes,
he asks that session to audit this record from the outside — free recall FIRST, comparison second,
report-not-edit, everything it says tagged `Inferred` unless it re-runs a probe. That is an
uncorrelated check, which is the one thing this apparatus has almost none of.

<!-- APPEND FURTHER 2.x ENTRIES HERE AS THE SITTING RUNS -->

---

## §3 CLOSING — filled at the close

<!-- TO BE COMPLETED AT CLOSE: close.sh card verbatim · what was struck or added in the registers ·
     the ledger row · both clocks · glass --since a652781 --enforce verdict · CI conclusion for HEAD
     observed after the push · what is left open and for whom -->

*Not yet written. If you are reading this section empty, the sitting did not reach its close and
**nothing in §2 should be treated as landed** — check `git log` against the pin `a652781` and
believe the commits, not this document.*

---

## §4 LEXICON REPORT — Rab's words → the project's names

*Source: `.claude/skills/echo/lexicon.md`, append-only. A mapping enters only via `/echo` Phase 7,
after Rab's word committed the reading that used it. Rows are never edited in place; a mapping that
turns out wrong gets a new superseding row citing the old one. Rendered here for a reader who has
none of this vocabulary — **read this before §1 if the words look strange.***

### 4.1 The tag law — the vocabulary that governs every other word

Every claim carries exactly one tag, and **the tag is an admission gate, not a label**: it decides
what the claim may be used for.

| Tag | Means | Admission price |
|---|---|---|
| **Observed** | I saw it, this session, with my own tool call | the command and what it printed |
| **Verified** | Observed **and** cross-checked by a differently-shaped second method | both, and why the second can fail independently |
| **Inferred** | reasoned from evidence, not witnessed | the evidence, and what would falsify it |
| **Intended** | designed to be true, not yet exercised | who can exercise it |
| **Unknown** | identified as unresolved | what would resolve it |
| **Historical** | was true at a stated time | the date, always |

Four rules bind for the whole session: a **consequential act needs an `Observed` premise**;
**sampling never promotes** (2 of 15 cells yields `Inferred` about 15, permanently); **a number is
re-measured, never quoted**; and **a failed probe never renders as a negative observation** — if a
check could not run, the answer is `UNREAD`, never `down`, `clean`, or `none`. `Verified` is
expensive on purpose: two checks that share an assumption are one check (SYM-001).

### 4.2 Rab's words

| Rab's word / phrase | What it names in this project | Where it lands |
|---|---|---|
| **muster** | the session-open protocol: `/muster`, `open.sh`, the two clocks | `.claude/skills/muster/` |
| **the two clocks** | HARD (git ledger row) × SOFT (cookie tally / TIME-STATE) | `CLAUDE.md` muster block |
| **lockstep** | both clocks advance together at close: ledger row + TIME-STATE | session-bootstrap |
| **sign / signed / GO** | a register signature; his word on a filed slot. Strongest form is by slot reference ("F-09 per-slice signed") | `docs/37` §3 |
| **cookie** | a tally entry in the memory library's `cookie-tally.md`, header + ledger, mirrored in TIME-STATE | memory library |
| **the card** | the RTX 3080 — one-process law, `Local\file-portal-card` mutex | `convert_and_ship.py` `acquire_card_mutex` |
| **held (a book)** | a `fail`-verdict bundle parked in `held/<sha16>` awaiting remedy | `_enforce_hold`, `convert_and_ship.py` |
| **the bench** | the Repair Bench prototype (zone repair, adjudication surface) | `prototypes/repair-bench/` |
| **the room / wall / dock / assay** | the widget's four surfaces | `docs/16`; `room.rs` |
| **turnout** (for conversions) | four measurable properties: text survival (`doc_survival`) · figure coverage · no silent transmutation · measured operating points | `docs/41` §0 |
| **differ (a part of this task)** | defer / delegate to a subagent | S97 §4a |
| **the Opus** | an Opus-model subagent, usually worktree-isolated, for investigation past the orchestrator | `docs/41` Appendix A |
| **full context search** (in a prompt) | the echo sweep: `sweep.sh` + term hits + lexicon lookup | `.claude/skills/echo/` |
| **what I think I may mean** | the echo's readings (Phase 3) + preview (Phase 4) | `.claude/skills/echo/SKILL.md` |
| **stigmergy** | coordination through traces left in a shared environment — how concurrent instances discover each other | `docs/43`; SYM-045 |
| **claiming (its) sections** | authorship stamps ⟨claimed: Fable⟩ / ⟨claimed: Codex⟩ on prose, ledger rows, docs | `coordination/authorship.md` |
| **2 signals as one** | the relay: each model carries the other's newest message + suggested prompt to Rab at session open (UTC entries) | `coordination/relay.md` |
| **the parallel sitting** | 2026-08-20's concurrent Fable+Codex work under one session number, stigmergically discovered | `docs/43`; S97 §4a |
| **production first layer** (for Claude–Codex cooperation R&D) | a production-ready *specification* layer — evidence, boundaries, interfaces, failure model, negative tests, staged adoption gates. **No executable protocol, no runtime integration, no implementation authority** | `docs/21` §2; `docs/40` §§10–11 |
| **free up resources / little brother gaming** | clean shutdown: widget + watcher + convert procs down, zero GPU load at session end | S42 standing instruction |

### 4.3 Terms this brief introduces

| term | meaning |
|---|---|
| **the door brief** | this document — a session recap + lexicon + navigation index left for a dormant lane to find on waking. Rab's image: *"slipping papers under someones door."* |
| **dormant (a lane)** | the peer model is out of usage, its silence is **declared in the record**, and its STALE beat is therefore expected. Distinct from a missed beat, which is a fault. |

---

## §5 NAVIGATION INDEX — where everything lives

*For a reader with no memory of this repo. Start at the top and stop when you have what you need.*

### 5.1 Read these first, in this order

| # | file | what it gives you |
|---|---|---|
| 1 | `wiki/INDEX.md` | the LLM-navigable map of the whole project — 12 pages, citation-audited |
| 2 | `CLAUDE_README.md` | the repo brain: session protocol + the Change Ledger (the HARD clock) |
| 3 | `OPEN-TASKS.md` | **the roll call of what the project has NOT done** — read §0 for the one-paragraph answer |
| 4 | `SYMPTOM-INDEX.md` | every known defect, its cause, its guard, and how to diagnose it |
| 5 | `sessions/S109-desktop-2026-08-24.md` | this session's full record; §17 is what the next session inherits |
| 6 | `AGENTS.md` / `llms.txt` | Codex-native and machine-readable entry points |

### 5.2 The governance layer

| path | what it is |
|---|---|
| `coordination/relay.md` | the bus — append-only, UTC, both lanes |
| `coordination/BUS-STANDARD.md` | how the bus works: one bus, halt while parsing, appends never erase, digests never trust |
| `coordination/RELAY-ACK-PROTOCOL.md` | the ACK layer — restatement + independent re-digest |
| `coordination/ack-fable.json` / `ack-codex.json` | the sidecars; the board reconstructs from these, not from any transcript |
| `coordination/authorship.md` | the ⟨claimed:⟩ convention |
| `coordination/SIGNATURES.md` | signed entries — a transcript is not proof |
| `coordination/CODEX-RESIDENCY.md` | the Codex lane's own space, created by Codex itself |
| `coordination/DISCLOSURE-STANDARD.md` | draft, unsigned (J7) |
| `coordination/T-004-EXTRACTED-SCHEMA.md` | the joint seam's extracted half, published for review (J6) |
| `codex/` | Codex's residency directory |

### 5.3 The skills — each self-testing

| skill | invoke | what it does | its tripwire |
|---|---|---|---|
| **muster** | `/muster` | session open: identity, both clocks, live state, three registers | `selftest.sh` — 43 assertions, case 0 is a positive control |
| **circle** | `/circle <commission>` | bounded audit — independent lanes, graded verdicts, mechanical/semantic gate | its own lanes |
| **echo** | `/echo` | ground an ambiguous commission before interpreting it; owns the lexicon | `sweep.sh` |
| **relay-gate** | `/relay-gate` | one side of the two-model ACK protocol | `selftest.py` — every law both ways |
| **wiki** | `/wiki` | maintain `wiki/` | selftest 11/11, both-way controls |

### 5.4 The product

| path | what it is |
|---|---|
| `windows-widget/` | the Tauri control room — Dock ⇄ Room, the ⚡ tile, the watcher's ⏻ |
| `windows-converter/` | `watch_and_convert.py`, `convert_and_ship.py`, `backend_parity.py`, `figure_coverage.py` |
| `linux-receiver/` · `linux-converter/` · `linux-dashboard/` | the ThinkPad lane |
| `observability/` | `glass_detector.py`, `acceptance.py` — the glass layer |
| `prototypes/` | the quarantine: `repair-bench/`, `room-chat/`, `relay-room/`. Zero pipeline coupling by convention |
| `scripts/` | operational scripts |

### 5.5 The scripts you will actually run

```bash
bash .claude/skills/muster/open.sh                    # session open — exit 1 is an incident
bash .claude/skills/muster/close.sh <pinned SHA>      # session close — ~8m37s (J4)
bash .claude/skills/muster/selftest.sh                # 43 assertions
```

```bash
python .claude/skills/relay-gate/gate.py status       # the board — reconstructs from disk
```

⚠ **Bare `python` on this machine is the Microsoft Store stub and fails.** Use the uv interpreter:
`/c/Users/Bndit/AppData/Roaming/uv/python/cpython-3.12.13-windows-x86_64-none/python.exe`.

⚠ **The glass detector's ritual form is `--since <pin> --enforce` and nothing less.** Without
`--enforce` it prints its unsigned glitches and **exits 0 regardless** — three closeouts cited a
bare exit 0 as evidence of nothing at all (SYM-046).

### 5.6 Traps a cold reader will hit

| trap | the rule |
|---|---|
| repo markdown is **CRLF** | slice it with `head`/`tail` only. `sed`/`awk`/`grep` strip CR, and a bare `grep` cannot even see them (SYM-029; `grep -U` can). `coordination/relay.md` is LF — check with `file` before appending |
| `.gpu-lock` is **write-only** as a name | it is a display signal, not a mutex. The real exclusion is the named mutex `Local\file-portal-card` (SYM-032) |
| a green suite is not a held property | S109's Circle found three violations live at 73/73 green |
| adoption is **Rab's hand** | build → print SHA-8 → he copies and launches. Never adopt for him (`docs/19` §0.3) |
| one lab process on the card, ever | check `nvidia-smi` / `.gpu-lock` before any GPU work; the seat may be his brother's |
| kill process **trees**, never single PIDs | and never chain GPU work with `;` (SYM-021) |
| an orphan watcher survives a widget force-kill | the Job Object governs only watchers the *widget* spawned (SYM-047). Census `python.exe` command lines before any adoption |

### 5.7 The measurement law

Every measured number obeys `docs/34`: **name the numerator, the denominator, and the conditions**,
in the world's vocabulary. Never blend prefill with decode or cold with warm. Give `n` and a
spread. A ratio prints both its sides; a percentage prints its base. **A duration nobody reported
renders `UNREAD`, never `0.0`.** The tag says what *kind* of claim it is; `docs/34` says what it
*counts*; a number needs both.

---

---

## §6 WHAT THIS BRIEF DOES NOT KNOW — the seams, named on purpose

*A record that lists only what it knows invites a reader to treat its silence as coverage. These
are the places where this document is thin, stated so an auditor has somewhere to aim. If you are
the session being asked to check this record from the outside, **start here.***

1. **Everything after ~19:00Z on 2026-08-24 is SINGLE-LANE.** No second vendor read it. Codex asked
   to have it held as **reported evidence until independently re-observed**, and that request stands
   unmet. This covers the Circle's three fixes, the muster upgrade, SYM-054 and `docs/46`.
2. **§1.5 cites the first sitting's account of itself; it does not re-derive it.** The Circle's
   three violations, the 73/73 green they were live inside, and the "three catches from Rab's
   questions" pattern are all `Historical` — read from `sessions/S109-*.md`, not re-measured here.
   If that closeout is wrong, this brief is wrong in the same places.
3. **The per-page conversion cost on this machine is `UNREAD`.** Not slow, not fast — never
   measured at the current state. The draft's own recipe says so. Any number anyone quotes for it
   today came from an older run on older hardware state.
4. **What the first sitting *considered and rejected* is not on disk anywhere.** The closeout
   records what was done. Near-misses, discarded hypotheses, and things noticed but not filed exist
   only in that session's context. **This is the one gap no amount of reading can close** — it has
   to be asked for, and it decays.
5. **The mutation score was in flight when this section was written.** Whether the 83-case suite's
   green means anything was an open question at the time of writing. See §3 for the answer, and if
   §3 is empty, the question is still open.
6. **`figure_coverage` has known blind spots that a clean report will not disclose.** SYM-049:
   zero-area connectors are dropped before clustering, so a spread-out diagram can fragment and be
   missed. SYM-053: an asset can be present and be the *wrong crop* — blank paper where a hand-drawn
   callout was. **A silent absence there is a known blind spot, not a clean bill.**
7. **The S94 guard exercises have never been logged by anyone.** Minimize+relaunch (expect
   restore-and-front, no twin), Room styling under CSP, the Recent-audits panel, the chat page, the
   boot log, one PID. `Intended`, not `Observed`, for over a dozen sessions.
8. **`marker_version` is `"unknown"` corpus-wide** (SYM-044), so the `.done` identity gate is
   one-third inert. Any claim that a resume spliced same-engine slices is unverifiable today.
9. **This brief has one author and one lane.** It was written by the session it describes. That is
   precisely the conflict of interest the project's own Circle methodology exists to break, and
   nothing here has been through a Circle.

*Ends. The knock on the door is the relay entry pointing here. This is the paper.*
