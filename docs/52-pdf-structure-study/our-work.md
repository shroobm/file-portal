# S114 — the honest account of "the stuff we had done"

Reviewer: Fable subagent, read-only lane. Written 2026-09-02T05:26Z → 05:32Z from the
repository, not from anyone's summary. Every claim carries its tag; every number below was
re-measured by me unless it says otherwise.

---

## §0 METHOD, AND A PIN THAT MOVED UNDER ME

`Observed` — **the repository changed while I was reviewing it.** My first `git log` (05:25Z)
topped out at `850bdf3`. My probe's `git rev-parse HEAD` (05:27Z) returned `8423e02`. A third
check (05:28Z) returned `f41dd1e`. Two commits landed mid-review:

| SHA | time (local −04:00) | subject |
|---|---|---|
| `8423e02` | 2026-09-02T01:27:07 | S114: authorship correction (Opus 5 → Fable 5.1) + second-sitting work log |
| `f41dd1e` | 2026-09-02T01:27:55 | J20 re-measured: the staged `1CF604CD` does not exist on disk |

Consequence, named rather than hidden: **my read of `sessions/S114-desktop-2026-08-31.md` was
stale by 59 lines** — §7b (the whole second sitting) was committed after I read the file. I
re-read it from `git show 8423e02` and folded it in. Anyone re-running this review against a
later HEAD should expect the same.

**Pins.** Session pin `14a526b` (S113 close). Controls in §6 ran at `8423e02`; I verified
`git diff 8423e02 f41dd1e -- prototypes/repair-bench/bench.py` is **empty**, so the §6 verdict
holds at `f41dd1e`. Working tree at review end: ` M coordination/ack-fable.json` + `?? .codex/`,
neither mine.

**Span reviewed:** `14a526b..f41dd1e` = **15 commits**.

---

## §1 WHAT WAS BUILT

### J19 — the maiden voyage, COLLECTED
`Observed` from the session record §7b (I did not witness the run; the run is over and its
events are the record's, not re-measurable by me now — so this is **Observed-from-record**, one
notch weaker than the rest of this document).

- Landed 2026-09-01T04:56:32Z: analyst audit `doc_survival 0.9402 · runs 25 of runs_total 404 ·
  verdict fail` → flagged → **HELD** (`14c66834bdfeaa2e`).
- First-ever goodput record: `chunks_generated 316 · chunks_resumed 641 · passed 928 ·
  rejected 29 · failed 0 · duration_s 4634.4 · goodput_accepted_tok_s 59.37`.
- The record's own arithmetic checks: 641 + 316 = 957 ✓ · 928 + 29 + 0 = 957 ✓.
- `analyst/done` **never fired** — F3/F4 confirmed live, exactly as the session predicted at open.

⚠ **A number disagrees with itself across the record, and nobody has reconciled it.**
`OPEN-TASKS.md` J19 and the S113 close both say `runs 25 of runs_total 531`. §7b says
`runs 25 of runs_total 404` for the analyst-phase audit and then, two lines later, says M6-R1
resolves it as `25 of 531 · partial · unseen 506`. **404 and 531 are both present in the same
paragraph describing the same manifest.** `Inferred`: 531 is the convert-phase audit's total and
404 the analyst-phase's, which would make both correct and the sentence merely compressed — but
I could not confirm this, because the held manifest is not in the repo (see §7). **UNREAD, and
it is load-bearing**: 531 is the number Codex's controls and my §6 re-run are built on.

### J20 — presented, NOT executed; then re-measured and **declared dead as written**
`Observed` in `f41dd1e`. The staged `1CF604CD` **does not exist on disk** —
`windows-widget/target/release/file-portal-widget.exe` is absent, so there is nothing to
Copy-Item. Two widget commits (`57a5da6`, `12f0ca9`) postdate the staged build's `2296cc0`.
Installed glass is still `4C6B073B`. The ticket now calls for a fresh rebuild on current HEAD;
adoption remains Rab's hand.

### J21 — M6-R1 review delivered
`MSG-FAB-0065` (commit `b2448ad`): **PASS with one finding** (M6-R1-F1 — the display cap applied
to the manifest verdict). Codex accepted it, found a second boundary loss Fable missed, and
fixed both in `12f0ca9`.

### J22 — three mission-control panel mocks + contract + adversarial critique
`Observed` — commit `a02b02c`, `prototypes/mission-control/`: `CONTRACT.md` (12 KB),
`CRITIQUE.md` (26 KB, 378 lines), three panel HTMLs (150–178 KB each), `voyage.js` (91 KB),
and the run's real `voyage-events.jsonl` + `voyage-manifest.json`. Five opus subagents,
1.24 M tokens. **All three panels judged `honest: false`** — but on their *self-verification*
(critique X1: a check that did not run painted a green PASS in panels A and B), not on the
dark-zone, resume-zero, alarm-load or self-containment tests, which were clean on all three.
Critic recommends graduating Panel C with three named edits. **Graduation not taken.**

### J24 — the block records the converter was discarding, BUILT AND WIRED
`Verified` — this is the substantial build of the session, and it is **not** a standalone
sidecar as a quick read suggests. `windows-converter/marker_blocks.py` (413 lines) is imported
by `convert_and_ship.py` at line 38 and referenced at ~15 sites including the split-slice merge
(`:1231`), the chunked book merge (`:1450`) and the single-file merge (`:1523`).

The load-bearing discovery is an **upstream bug in marker 1.10.2**: `FlatBlockOutput.page` is
wrong. Marker computes it as `int(block.id.split("/")[-1])` off a *Page pseudo-block*, whose
last segment is a per-page monotonic block counter, not a page number. The module's docstring
records true pages 0,1,2,3 shipping as `8, 8, 10, 26` on one probe and `12, 43, 7, 9` on another
— three distinct values for four pages, one repeated. The correct segment is index `[2]`, which
is absolute across `--page_range` slices by construction, so no offset table is needed. The
function returns `None` rather than a guess when the id is not that shape.

Design constraints honoured, all readable in the source: markdown is rendered and written
**first** by marker's own `save_output`, then the chunk render runs under one try/except that
exits 0 — *a book can lose its blocks; a book must never fail because of them*. `FP_BLOCKS=off`
restores the pre-J24 argv byte-for-byte. One `build_document` (the whole GPU cost), two renders.

### J25 — the converter bake-off, FILED; Chandra DOWNLOADED
`Observed` — `fa32902` files the ticket; §7b records the download as signed: `datalab-to/chandra-ocr-2`,
**10.61 GB / 17 files, 16.1 min**, sha-listed before pull. Two hard blockers found and recorded:
BF16 needs 10.59 GB against 8.3 GB free, and **transformers 4.57.6 cannot load it** (`qwen3_5`
absent from `CONFIG_MAPPING_NAMES`). "Do NOT upgrade marker-env." `chandra-env` waits on Rab.

### SYM-071 — filed
`46e6de4`. Muster's SOFT-clock guard is defeated by re-wrapped prose: `muster.sh:75` matches
line-wise, the S113 close wrapped `cookies **received` / `84 / given 3` across a newline, and the
guard returned `hook=` empty. Verdict CONFIG, not rewind. The row correctly names **the dangerous
converse** — nothing distinguishes `hook=` (could not read) from `hook=<wrong number>` (really
forked). **OPEN.**

---

## §2 WHAT I VERIFIED BY RE-RUNNING IT

All with `C:/Users/Bndit/ml/marker-env/Scripts/python.exe`, 2026-09-02.

| what | command | result | time (UTC) |
|---|---|---|---|
| J24 tripwire | `marker_blocks_selftest.py` | **GREEN 57/57**, exit 0 | 05:26:33 → 05:26:34 |
| pre-existing converter suite | `convert_and_ship_selftest.py` | **GREEN 85/85**, exit 0 | 05:26:53 → 05:26:54 |
| Bench source/wire | `test_bench_page.py` | **OK, 81 tests / 3.315 s**, exit 0 | 05:29 |
| Bench acceptance (real held Valentine) | `acceptance.py` | **PASS 85/85**, exit 0 | 05:29 |
| Codex's two controls | my own `cdx0043_probe.py` | **PASS** — see §6 | 05:27 |
| glass detector, session span | `glass_detector.py --since 14a526b --enforce` | **✗ exit 1 — 1 UNSIGNED GLITCH** | 05:30 |
| glass detector, Codex's pin | `--since c9b6cb1 --enforce` | **✗ exit 1 — same glitch** | 05:31 |

The J24 selftest's own negative control is worth naming because it is the thing rule 4 asks for
and it genuinely fires: the run prints `[watched-failing] structural guard: save_output must
precede the chunk render in source`, then feeds the guard a deliberately reordered sample and
reports `broken-order sample -> guard reads: RED (expected RED)`. The guard is not a tautology.
The suite also proves `FP_BLOCKS=off` reproduces the pre-J24 argv byte-for-byte, and that
markdown is byte-identical whether the block pass succeeds, faults, or is skipped.

---

## §3 FINDINGS I FOUND MYSELF (undisposed)

### FIND-1 — the glass detector is RED on this session's own span, and J24 put it there
`Verified`, two shapes. `glass_detector.py --since 14a526b --enforce` **exits 1**:

```
✗ 1 UNSIGNED GLITCH(ES) at 1 site(s) — computed, stored, reaching nobody:
    converter:blocks_engine
        windows-converter\convert_and_ship.py:1395  (_convert_chunked)
```

Second shape: `git log -S"blocks_engine" -- windows-converter/convert_and_ship.py` returns
**exactly one commit — `850bdf3`, J24**.

⚠ **This is not a contradiction of Codex, it is staleness.** `MSG-CDX-0043` claims
"glass detector `--since c9b6cb1 --enforce` reports no unsigned glitches". That message is
timestamped **05:03Z**; J24 landed at **10:01Z** (`850bdf3`, 06:01:05−04:00). Codex's claim was
true when made and is false now — I re-ran Codex's exact pin and got the same exit 1.

**This is the S113 close precedent repeating verbatim**: *"a build's new keys need same-commit
dispositions or they land on whoever closes next"* — 19 unsigned glass keys were signed at the
S113 close for exactly this reason. J24 shipped one more.

### FIND-2 — the exporter finding in the record is imprecise, and the true shape is worse
The session record lists as an undisposed J24 finding: *"exporter does not carry `blocks.json`"*.
`Verified` by reading `linux-converter/converter/exporter.py` — **that is wrong for the create
path and right for the supersede path**, and the split matters:

- **CREATE path (`:352`)** — `shutil.copytree(bundle_dir, tmp)` copies the *whole* bundle
  directory, so `blocks.json` **does** travel. It is even blob-verified: the L12 gate at `:371`
  walks `bundle_dir.rglob("*")` and `cat-file -e`s every file in the bare repo.
- **SUPERSEDE path (`_supersede_replace`, `:439-453`)** — copies **only** the `.md`, `assets/`,
  and `manifest.json`. `blocks.json` is **not** copied.

Two consequences, both `Inferred` from that source and neither exercised by a test
(`grep -c blocks linux-converter/tests/test_exporter.py` = **0**, across 10 supersede tests):

1. A superseded note gets a `manifest.json` **carrying `manifest["blocks"]` counts** with **no
   `blocks.json` beside it** — a manifest asserting geometry that is not there. That is SYM-053's
   own disease ("it looks covered because a reference exists") one level up, which is precisely
   what `_attach_blocks_safe`'s docstring says the `complete` flag exists to prevent.
2. **Worse, and the reason I rank this above the record's version:** supersede removes only
   `assets/` (`git rm -r … /assets` + `rmtree`). Nothing removes `blocks.json`. So a note created
   post-J24 **with** blocks and later superseded keeps the **old conversion's** `blocks.json`
   beside the **new** markdown and the **new** manifest — stale geometry silently paired with
   fresh text. Every bbox would point at the wrong place, and nothing would say so.

⚠ **The maiden voyage is exactly a supersede case** (`audit supersede from_verdict fail`). It
went HELD so it did not export — but its remedy re-convert is the first bundle that would walk
this path.

### FIND-3 — J24's three new event verbs reach nobody
`Verified` by grep in both consumers. J24 emits `convert/blocks` (`:670`),
`convert/blocks_partial` (`:677`) and `convert/blocks_error` (7 sites: `:683, :945, :1233,
:1369, :1454, :1527`). `grep "blocks" windows-widget/src/main.js windows-widget/src/room.js`
returns **nothing**. The J20 re-measure in `f41dd1e` independently reports `event-vocab.js` has
**0** references to `blocks` — two differently-shaped reads agreeing.

`convert/blocks_error` is the one that should worry an operator: it is the *only* signal that a
book silently lost its geometry, and it is emitted from seven places into a glass that cannot
say the word.

### FIND-4 — the 404 / 531 collision in J19's own record
See §1. **UNREAD**, and it sits underneath §6's controls.

---

## §4 UNVERIFIED / UNSIGNED

- **J24 is SEMANTIC and its OPEN-TASKS row still reads as un-built.** The row says
  "SEMANTIC (converter change — Rab's signature)". §7b says "J24 signed and built". The register
  row was not updated to record the signature or the build. `Observed`: `OPEN-TASKS.md` J24 is
  byte-identical between `fa32902` (filing) and `f41dd1e` (now) — only J20's row was re-measured.
- **`blocks.json` size on a real book: UNREAD.** Named in the record as an undisposed finding.
  The 1,377-page Damodaran is the obvious probe and it was not run. `_attach_blocks_safe`'s own
  docstring says "a 1,377-page book's blocks are megabytes" — that is an estimate, not a
  measurement, and it gates whether this ships to the vault at all.
- **The three panel mocks are UNSIGNED.** Graduation is Rab's. The critic's recommendation
  (Panel C + three edits) has no disposition.
- **J23's 13 contested census dispositions: untouched this session.** Still Rab's signature.
- **SYM-071 is filed but unfixed.** The row prescribes the repair (parse TIME-STATE joined;
  distinguish UNREAD from mismatch) and demands a tripwire stepping on **both** directions.
  Neither exists.
- **SYM-053 / SYM-056 / SYM-067 / SYM-054 remain open.** J24 built the *instrument* SYM-053 needs
  (page + bbox), but nothing consumes it yet — the audit's `run_page: null` is still null because
  no code reads `blocks.json` back.
  > *Correction 2026-09-04:* SYM-067 FIXED by J29 `8aa8936` (amended `d9bfaaa`), post-close; SYM-053 / SYM-056 / SYM-054 remain open as written.
- **Chandra: downloaded, unrunnable, unscoped.** Two blockers stand; `chandra-env` waits on Rab.
- **CI status for this session's HEAD: UNREAD by me.** I did not observe a CI run for
  `850bdf3`, `8423e02` or `f41dd1e`. The project's own law is that CI is observed by hand after
  the push.

---

## §5 WHAT IS OWED (promises in the record not yet discharged)

1. **Codex's review ask (`MSG-CDX-0043`).** The record marks it "**Owed**". → **Discharged in §6
   below: PASS.** Codex further asks that, on PASS, `OPEN-TASKS` J21 and the `docs/50` M6-R1
   record be repaired. **Still owed — Fable's lane, not mine** (the brief forbids me touching
   either).
2. **The Gmail draft for the maiden voyage.** J19's row requires it "per the standing
   pipeline-run protocol". §7b records the report delivered to Rab at ~05:15Z but **names no
   Gmail draft**. `Unknown` whether it was created — I did not check the mail account.
3. **J19's register corrections (F4).** The session's own F4 says OPEN-TASKS J19 and the S113
   record both wrongly claim goodput "populates at `analyst/done`", and that **both registers
   need the correction**. J19's row is byte-identical since filing. **Not done.**
4. **The 40-tail / accumulator glass (J20)** — ticket declared dead as written; the replacement
   rebuild has not been run.
5. **Dispositions for J24's new keys** (FIND-1) and for its three event verbs (FIND-3).
6. **A tripwire for SYM-071**, stepping on both directions.
7. **F7's consumer fix** — `main.js:482` still renders a resumed convert's `s_per_page` raw, so a
   resumed book publishes "1377pp @ 0.0s/p". `Verified` still present: `grep -n "s_per_page"
   windows-widget/src/main.js` → `:482`. No ticket filed for it that I can find.

---

## §6 CODEX'S ASK — DISCHARGED: **PASS**

Probe: `…/scratchpad/pdfua/out/cdx0043_probe.py`, run under the marker-env interpreter at
05:27Z. Ran at `HEAD = 8423e02`; `bench.py` is unchanged at `f41dd1e`, so the verdict holds at
current HEAD. `bench.LEGACY_RUN_CAP = 25`; `evidence_count` signature is
`(shown, raw_total, raw_cap, *, legacy_cap)` — **no `display_cap` parameter remains**, which is
M6-R1-F1's fix visible in the signature itself.

**POSITIVE CONTROL — `shown=60, runs_total=531, runs_capped_at=100`** → PASS

```json
{"shown": 60, "total": 531, "capped_at": 100, "completeness": "partial",
 "complete": false, "unseen": 471, "label": "60 of 531",
 "remedy": "full-evidence review required",
 "reason": "471 located defect(s) are not shown"}
```

partial ✓ · `60 of 531` ✓ · unseen **471** ✓ · total 531 ✓ · complete false ✓.

**NEGATIVE CONTROL — `shown=101` against producer cap 100** → PASS, both ways

- total **absent** → `malformed`, reason `shown count exceeds its producer cap of 100` ✓
  (note the reason now names the **producer** cap, not the display cap — the exact wording
  defect `MSG-FAB-0065` reported is gone).
- total **present** (`531`) → still `malformed`, `unseen = None` ✓ — no number invented from a
  contradictory declaration.

**ISOLATION — crossing 40 must no longer change the verdict.** The variable `MSG-FAB-0065`
isolated:

| shown | completeness | label | unseen |
|---|---|---|---|
| 39 | partial | 39 of 531 | 492 |
| 40 | partial | 40 of 531 | 491 |
| 41 | partial | 41 of 531 | 490 |
| 60 | partial | 60 of 531 | 471 |

Monotone across the old boundary. The 40-row display limit no longer touches the manifest verdict.

**HARNESS NEGATIVE CONTROL (rule 4 — I watched my own checker fail).** I asserted the positive
case was `complete` when it is `partial`; the harness printed
`FAIL [deliberate] positive case mislabelled as complete` and counted it. The checks are not
vacuous. That deliberate failure was then popped before the verdict.

**SECOND BOUNDARY LOSS — `Bench.state()` sliced retained runs to 40 before `12f0ca9`, and does
not after: CONFIRMED.** Method: `git show` of both versions (a differently-shaped instrument
from the `evidence_count` probe — source diff, not execution), because `state()` needs a bundle.

- **Before** — `git show 46e6de4:prototypes/repair-bench/bench.py`, `def state` at `:460`,
  line **474**: `for r in self.runs()[:40]:`
- **After** — `git show 12f0ca9:…`, `def state` at `:458`, line **474**: `for r in self.runs():`
- **Current HEAD** — `sed -n '470,478p'` shows `for r in self.runs():` with the comment
  *"The producer already bounds this retained list. A second 40-row slice hid reviewable sites
  and made the state count disagree with the manifest population."*

Zones were never sliced in either version (`for z in self.zones():` both sides) — so the loss was
runs-only, exactly as Codex described.

**VERDICT: PASS.** Both controls reproduce, the isolation is clean, the second boundary loss is
confirmed present-then-absent. I also independently re-measured Codex's own claimed counts rather
than quoting them: `test_bench_page.py` **81/81** and `acceptance.py` **85/85** with the real
held Valentine untouched — both as claimed.

**One caveat attached to the PASS, not a finding against the fix:** `531` is the number the
controls are built on, and §1/FIND-4 shows the record carrying both `404` and `531` for this
manifest. The control is a *synthetic* triple and passes regardless of which is true — but if a
reader takes "60 of 531" as a statement about the real held book, that provenance is UNREAD.

**Boundary respected:** I did not edit `OPEN-TASKS.md`, `docs/50`, or anything else in the repo.
No widening into M6-R2.

---

## §7 RESIDUE — what I did not read, could not verify, or worked around

- **I did not read the held manifest.** `held/14c66834bdfeaa2e` is not in the repo (it lives
  under `~/ml/library`, outside my brief's read scope and untouched). Everything in §1 about
  J19's numbers is **Observed-from-record**, not re-measured. The 404/531 collision is therefore
  UNREAD, not resolved.
- **I did not run the panels.** J22's three HTML mocks were not served or rendered by me;
  `CRITIQUE.md`'s findings are reported here as *the critic's* observations, tagged as such. I
  read the critique's cross-cutting section (X1–X5) and skimmed no further — **I read 70 of 378
  lines of `CRITIQUE.md`.** Sampling never promotes: I can speak for X1–X5 and nothing else.
- **I did not verify CI** for any commit in the span.
- **I did not check Gmail** for the owed draft (§5.2), so that item is `Unknown`, not "missing".
- **I did not exercise the exporter.** FIND-2's two consequences are `Inferred` from reading
  `_supersede_replace` and confirming zero `blocks` coverage in `test_exporter.py`. I did not
  build a fixture bundle and run a supersede. The *source facts* (create uses `copytree`;
  supersede copies three things and rm's only `assets/`) are `Verified` by reading.
- **I ran tests that write.** `acceptance.py` created
  `prototypes/repair-bench/.sandbox/b6fbdd75f6242f53--20260902-012901` inside the repo. It is
  gitignored (`prototypes/repair-bench/.gitignore:2`) and was mine (timestamp matches my run);
  **I removed it and the now-empty `.sandbox/`.** `git status` at review end shows only
  ` M coordination/ack-fable.json` and `?? .codex/`, neither of which I touched. Declared because
  "I did not modify the repo" would otherwise be false.
- **A tooling note against myself:** an ERR-009 hook warned that my probe used a heredoc
  containing backslash escapes — the pattern that has failed five times in this project. It
  happened to work here (quoted delimiter, escapes inside a Python string), but the remedy is
  the Write tool, and I should have used it.
- **HEAD moved twice mid-review** (§0). Anything I read before 05:27Z was read at `850bdf3`.
