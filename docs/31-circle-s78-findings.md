# docs/31 — Circle findings, S78 (2026-08-14)

**Commission (Rab):** assess S78's own build against its own signed criteria — (1)
`observability/` against docs/29 §5.1–§5.4 and the §8.3 signature, (2) docs/30 against docs/18
§4 Stage D and the source it claims to have verified, (3) the clock repair (ledger reorder,
`muster.sh` [3a], SYM-028/029).

**Deliverable class: assessment.** Nothing was mutated during the Circle. The gate is §5.

Three lanes, deliberately methodologically different: **A** judged code against law by execution,
**B** re-derived every factual claim from source by methods different from the author's, **C**
attacked the clock repair with adversarial fixtures. Lanes A and C converged independently on
the lead finding, which is why it is ranked first.

**Direct answers to the commission's three questions:**

1. **No.** The detector does not implement what was signed. The signed mode crashes on every
   real input, and the acceptance suite tests the one input that cannot fail.
2. **Mostly, with three claims false and one major defect missed.** docs/30's headline survives
   with a scope correction; three of its supporting claims are wrong.
3. **The repair is sound; the signature is not executed.** The reorder is a proven pure
   permutation and [3a] works. Both decisions signed this session shipped no code.

---

## 1. The findings, most severe first

### 1.1 VIOLATION — the signed mode crashes on every non-empty diff
*(Lanes A + C, independently; reproduced by the author)*

`observability/glass_detector.py:246-252` — `subprocess.run(..., text=True)` with no
`encoding=` decodes git's output with the console codepage (cp1252 here). The repo's sources are
full of `§ — · ✓`; the `UnicodeDecodeError` is raised inside subprocess's *reader thread*, so
`run()` returns `stdout=None` and `:257` dies with `AttributeError`. The `except` at `:253`
catches only `CalledProcessError`/`FileNotFoundError` and is bypassed.

Measured: `--since HEAD`/`HEAD~1` exit 0; `HEAD~3`, `HEAD~4`, `c3f7e17`, `60acd77`, `d28ab91`
all traceback and exit 1. The two that "pass" do so only because their diffs are **0 bytes**.
The first offending byte is `0x8D`, from `◍` (U+25CD) in `observability/acceptance.py:39` — the
answer-key row for `runs`. **The tool is broken by its own source.**

With `encoding="utf-8"` added, `--since 60acd77` returns 25,817 chars and finds **18 keys** the
signed mode currently cannot see.

### 1.2 VIOLATION — the §5.4 acceptance test exercises the only input that cannot fail

`observability/acceptance.py:110-117`. Its own comment names the hazard exactly: *"a `--since`
that silently ignored its argument would report a clean scope forever and look exactly like
success."* The test then written is `--since HEAD` — an empty diff. It cannot distinguish a
working filter from a no-op, and it cannot reach the decode path. **`PASS — 13/13` was reported
while the feature was broken for every real range.** This is the SYM-001 shape (two checks
sharing an assumption) in the harness explicitly written to avoid it.

### 1.3 VIOLATION — Mode D reproduced inside the instrument built to prevent Mode D

`glass_detector.py:259` filters added lines with `"key":` — which cannot match Rust struct
fields or `#[serde(rename)]`, the widget lane's entire dialect (7 Serialize structs, 30
fields). Also blind to `dict(**kwargs)` and f-string keys. Add `pub chunks_skipped: u64` to
`status.rs`, render it nowhere, and the signed closeout reports `0 keys in scope · ✓ no unsigned
glitches`.

### 1.4 DEAD — both decisions signed this session shipped no code

- **docs/29 §8.3** (detector runs in the closeout ritual, `--since` mode): zero callers
  repo-wide. `CLAUDE_README.md` §4 and `docs/21` were never amended. Worse, the artifacts
  contradict the signature — `observability/README.md:76` still reads "has not been signed…
  wired into nothing" and `glass_detector.py:31` still reads `UNSIGNED`, while `docs/29:185`
  cites that README as authority. A citation loop.
- **docs/30 §5.4** (a `fail` verdict raises algedonically regardless of `audit_mode`):
  unimplemented. All four S78 commits touch only docs, `SYMPTOM-INDEX.md`, and
  `observability/`; `windows-widget/` and `windows-converter/` are untouched.

**This is SYM-027's class reproduced inside the session that legislated against it.** docs/29
§5.4 demands same-commit disposition; the tool was built in `e41523f` and signed in `bd4c4b9`
with the wiring in neither.

### 1.5 VIOLATION — an unacknowledged park stops alarming after seven days
*(Lane B; the most severe defect in the system rather than in S78's own work)*

`algedonic.rs:25` `WINDOW_S = 7 * 86_400`, applied at `:166`. The module's contract at `:5-6`
says a pain fact surfaces "until someone clicks ⚑". It actually surfaces until someone clicks ⚑
**or a week passes**. Four books sit in `held/`; one escalates. **Valentine's park crossed out
of the window at 11:18 on 2026-08-14, unacknowledged, with no trace of the transition.**

The founding incident this stage exists to prevent lasted **five days**. The margin is two.
docs/30 audited this module for silent-discard defects and never mentions `WINDOW_S`.

### 1.6 VIOLATION — `MAX_ALERTS` discards the oldest, and the counts are computed after it

`algedonic.rs:170` truncates a **newest-first** list to 12, so it drops the *oldest* alerts —
those most likely to satisfy `escalated = age_min >= m`. Acked alerts are never filtered out
first, so they consume slots. `:187-188` then counts `unacked`/`escalated` over the truncated
list. A night of 12 fresh `intake/failed` evicts a month-old park and renders a count that is
measured, wrong, and unfalsifiable from the glass — docs/29's disease inside the module docs/30
was auditing for it.

### 1.7 VIOLATION — a receipts alert has no resolution path, and re-arms on restart

`algedonic.rs:151-158` retires a receipt alert only on a later `exported`/`exported-supersede`/
`blessed` row for the same bundle. A refusal resolved by **deleting** the bundle — exactly what
SYM-015 records doing — can never produce one. Live: five identical `supersede-held` rows for
`claude-code-up-and-running`, one per exporter restart; Rab acked the `2026-08-06` occurrence,
the `2026-08-09` restart minted a new `ts` → new id → **re-alarmed**. Escalated right now, age
≈6,830 minutes, for a problem closed five days ago. The re-alarming logic docs/30 §4 certified
as "correct" re-alarms on a **restart**, not a recurrence.

### 1.8 VIOLATION — `--since` disables stale-signature detection, and `--since` is the signed mode

`glass_detector.py:341`. Proven by execution with a planted stale signature: visible on a plain
run, silent under `--since`, and `--enforce --since` exits 0. `dispositions.json:9-11` states
that a DEAD entry outliving its session "is itself a defect" — the only detector of that is
switched off in the only mode signed.

### 1.9 VIOLATION — the answer key is a selection, and the omissions are the failures

`acceptance.py:5-8` claims docs/29 §7's findings "row for row". `ANSWER_KEY` has 9 rows; §7 has
~16 field-level findings. Of the 8 dropped, **7 are cases the detector gets wrong**: `note`,
`model`, `gates`, `secs`, `cycle`, `rect` all falsely `glass`; `sha` absent from the census
entirely. The one that would have passed (`delta`) was also dropped. Root cause is a fifth
undisclosed limit: the detector matches key **name** against one flat blob with no notion of
producer **site**, so `gates`/`secs`/`model`/`rect` are cleared by the *transcribe proposal*
rendering at `bench.html:838` while §7.10's complaint is about the same names persisted into
`manifest["repairs"][]` at `bench.py:944-948`. §7.10's own wording is "goes dark **once
persisted**"; the detector cannot express "once".

### 1.10 VIOLATION — two silent-pass modes survive `--enforce`

A typo'd producer glob prints `producers: (none matched)` then `✓ no unsigned glitches`, exit 0
— renaming `bench.py` turns the bench lane green forever. A typo'd `--lane` name prints
**nothing at all** and exits 0; `:301` never validates the name against the config.

### 1.11 VIOLATION — the harness could stay green through a full revert of S76/S77

A signed `GLASS` disposition yields verdict `"glass"`, indistinguishable in the JSON from
glass-by-reference. `ANSWER_KEY`'s four "must now read glass" rows can therefore be satisfied by
**signing** rather than by **wiring**. Compounding: `dispositions.json:51` is `{}`, so
acceptance section [3] contributes one vacuous check and the entire §5.2 mechanism is
unexercised by the suite claiming to prove it. (Lane A exercised all three validators by hand:
they work.)

### 1.12 VIOLATION — producer trees are listed in the renderer column

`dispositions.json:41-47` lists `linux-converter/converter/*.py` and the widget's `*.rs` as
*renderers* of the converter lane. **22 distinct keys score `glass` with nothing human-facing
naming them.** Cleanest cases are producer-matching-producer: `lane_reason`,
`converter_version`, `chars_per_page_detected` (`convert_and_ship.py:827-830`) are cleared by
the **Linux sibling converter's local variable names**. Mirror hole: `linux-converter/converter/
exporter.py` *is* a producer (`_receipt()` at `:110` writes `receipts.jsonl`) and appears in no
lane's producer list — which is why §7.9's `sha` never entered the census. Doubly blind, since
`_receipt` passes fields as `**kwargs`.

### 1.13 Counting and collection defects

- **Occurrences printed as glitches.** 93 rows / 89 distinct sites / **77 distinct
  `lane:key`** — and since a disposition is keyed `lane:key`, the actionable unit is 77. Per-lane
  headers are worse: 613 rows vs **335** distinct. Every headline number given to Rab, written
  into the commit message, and recorded in `SYMPTOM-INDEX.md:44` overstates by 17–45%.
- **The Python extractor double-harvests** (`glass_detector.py:148-157` recurses via
  `ast.walk` then again per nested dict; nested `def`s are scanned twice). `analyst.py`: 90
  harvested / 49 distinct, **+84%**.
- **Outbound HTTP bodies counted as measurements.** `analyst.py:136-140` builds the Ollama
  request with `json.dumps`; rule 3 matches any `dump`/`dumps`, so `keep_alive`, `prompt`,
  `options`, `num_ctx`, `think` enter the census as stored measurements. Five are then falsely
  cleared off `bench.py` — two errors cancelling.

### 1.14 docs/30's three false claims

- **`died` "appears only inside comments" — false.** `main.js:533-534,537` has a live binding
  and `styles.css:705` a live `.died` class. The substantive point (no `died` *event*, no
  matcher arm) holds, but the framing is unfair to docs/18: the death certificate **shipped** in
  S52 as widget state and a log line. The accurate finding is narrower — *it never becomes an
  `events.jsonl` event, so it is the one pain class structurally invisible to the derivation.*
- **"`held` is the matcher's only route for a fidelity fail" — false.** `supersede-held →
  vault-held` carries one (`exporter.py:213-223` → `algedonic.rs:143`), and the live ack ledger
  contains a human ack of exactly that. The hole is real for **first ingest**
  (`exporter.py:275-291` runs a dedup grep with no verdict check) — not universal.
  **Also unstated: `C:\Users\Bndit\ml\library\audit-mode.txt` currently reads `enforce`**, so
  §3.3's failure is *latent on this machine, not live*. The decision sheet argued a stronger
  case than the ground supports.
- **"five silent days render a calmer widget"** is true in general and **false for the example
  it invokes** — S48's silently dying watcher is now the thing the widget is loudest about
  (`watcher.rs:78-110`, `main.js:556-571`, terracotta ⏻). docs/18 spread that mitigation across
  Stages A, B and D; docs/30 graded the criterion against Stage D alone.
- **"correct *and tested*"** — the projection-discipline claim has **no test**; the four tests
  cover resolution, park semantics, re-alarming and lever validation.

### 1.15 The clock: sound repair, incomplete guard

**HELD.** The reorder is a **proven pure permutation** — verified byte-exactly via `git show >
file` and `Counter` over `open(...,'rb').splitlines(keepends=True)`: zero lines removed or
altered, each row's SHA-256 identical across the move. The 318,271-byte figure checks out
(LF blob 316,403 + 1,868 CRs). The ledger is strictly ascending S16→S77, no gaps, no duplicates.
[3a] fires correctly on out-of-order and duplicate session numbers, is robust to `|` in prose
and hex-looking words *when the SHA cell is present*, and produces no false fire on empty or
single-row ledgers. The negative test reproduces exactly.

**Still open:**
- **21 of 83 rows are silently discarded** by the parser (`muster.sh:55` requires `S<n>:` *and*
  a valid SHA cell; pre-S16 rows predate the convention). A future row that omits `S79:` is
  skipped, the *previous* row is selected, and **[3a] stays silent** — SYM-028 recurs in a form
  the new guard does not cover.
- **A missing or non-git repo still reports "rewind/fork?"** (`muster.sh:73-76`) — the exact
  misdiagnosis SYM-028 exists to prevent, reachable by another path.
- **A narrative word can be adopted as the SHA** when the cell is absent: `deadbeef`,
  `defaced`, `effaced`, or any 8-digit date such as `20260814`.
- **The SOFT clock still selects by position.** `muster.sh:29` uses `head -1`, and `MEMORY.md`
  has **two** matches — line 9 (`received 69`) and line 138 (`received 55`). It works only
  because 9 precedes 138. **The S78 repair de-positioned [3] and left the identical bug in [2].**
  And `MEMORY.md:138` is itself stale.
- **[3a] prints nothing when it passes** (`muster.sh:61-65`), while [1], [2] and [3] all print
  a ✓. A clean run is indistinguishable from a ledger that parsed to nothing. **The guard built
  in response to an observability failure is itself unobservable when it passes.**
- **`muster.sh` exists in exactly one un-backed-up copy** (4,590 bytes; neither `~/.claude` nor
  `~` is a repo). The instrument that detects tampering with the clocks is the least
  tamper-evident file in the system.

### 1.16 SYM-029: cause proven, danger overstated

Three discriminating experiments (`grep -c -P '\r'` → 0; `grep -U -c $'\r'` → 3; `grep -c
'alpha$'` → 1) **refute** the alternative hypothesis and prove `grep`, `sed` and `awk` each
strip CR on read here. But the row's claim that "git reports every touched line as changed" is
**wrong**: this repo has `core.autocrlf=true` and no `.gitattributes`, so blobs are LF and
`git diff` after a CR-stripping pass is **empty**. The damage is a phantom-dirty `git status`
and **cannot reach a commit**. The rule stands regardless; the stated danger does not.
(`grep` has `-U` as a one-flag fix; `sed` and `awk` have no equivalent — unmentioned.)

---

## 2. Refuted — recorded because a refutation is a finding

- **`pages_scored` is NOT a fudge.** The author's own seeded suspicion, refuted: it is
  genuinely referenced only as a positioning denominator (`main.js:803,805`; `room.js:393,395`),
  §5.1's letter genuinely cannot express §7.2's "never printed", and the limit is disclosed in
  three places. Scoring it GLITCH would contradict the law the detector implements. *But* the
  check's **form** is a trap: `acceptance.py:97` asserts equality on a blindness, so if someone
  deletes the run-mark rendering — making it a genuine actionable glitch — the suite goes **red
  for the detector becoming more correct**.
- **The Rust extractor is correct on this tree.** 61/61 `json!` blocks terminated correctly
  (16 contain braces inside string literals, all balanced format placeholders); 7/7 Serialize
  structs captured; zero misses. FRAGILE in principle only — a lone `"{"`, a non-`pub` or
  `pub(crate)` field, or a >400-char derive→struct gap each break it silently.
- **`MIN_KEY_LEN` drops 10 real keys** (39 occurrences) and is an undisclosed fifth limit — but
  **every one would have scored `glass` anyway**. No verdict changes today.
- **The planted-glitch negative test is honest**, not theatre: it does require exit 1 and does
  check the rendered sibling is not falsely accused. Its weakness is scope — it plants the
  simplest `return {literal}` shape, never the tuple-return that actually broke, never the Rust
  dialect, never `--since`.
- **docs/30's §1 quotation of docs/18 is accurate**; the "1 of 3 channels" count is correct;
  "385 lines", "four unit tests", `DEFAULT_MINUTES = 30`, `m_provisional: true` all exact.
- **C6, the notification sweep, HELD exhaustively** — no plugin in `Cargo.toml`, no
  notification permission in `capabilities/default.json`, no tray in `tauri.conf.json`, no
  `Notification`/`new Audio`/`alert()`/`requestUserAttention` anywhere. Two disclosures for
  exactness: `tray-icon` and `objc2-user-notifications` **are** in `Cargo.lock` as transitive
  deps of `tauri` itself (compiled, never constructed), and one `set_focus()` exists at
  `bench.rs:194` on a user click. Nothing pushes.
- **Ack-id `|` injection is a non-issue** — the id is only ever compared for equality, and
  bundle names come from Windows filenames where `|` is illegal.

---

## 3. The pattern, named

S76 named the observability class and shipped a fourth instance ninety minutes later. S77
produced two more while investigating it. **S78 built the instrument for the class and
reproduced the class inside the instrument** — §1.3 is Mode D in the Mode D detector, §1.4 is a
stored signature reaching nobody in the tool built to find values that reach nobody, and §1.15's
last two items are unobservable guards inside the fix for an observability failure.

Three sessions, three recurrences, each while actively holding the concept. This is evidence
about the **mechanism**, not about any session's carelessness, and it is the strongest available
argument that Rab's §5.4 timing signature was the correct instinct: retrospective sweeps keep
finding these because retrospection is the wrong tense. A detector that runs *after* the work is
itself subject to the defect it detects.

**Corollary for the next Circle:** every S78 artifact that reported a number reported it too
high (§1.13), and every S78 claim of "tested" was weaker than stated (§1.2, §1.11, §1.14). The
class to watch is not "did we measure it" but "did we check the measurement could fail".

---

## 4. What HELD

The ledger reorder (byte-proven). [3a]'s core behaviour and its negative test. All 9 answer-key
verdicts, factually. The three config validators. `--enforce` exit codes on documented paths.
The Rust extractor on this tree. `algedonic.rs`'s park semantics, resolution suppression,
ack-ledger append-only discipline, M-lever bounds, and the `iso` round-trip. The notification
sweep. SYM-029's byte arithmetic (4 and 1,868, both exact). SYM-027's *state* description
("built and proven but wired into nothing") — only its stated *reason* is now false.

---

## 5. The gate

### 5.1 Mechanical — unambiguous under already-signed criteria

1. `encoding="utf-8"` at `glass_detector.py:250`, **plus** an acceptance case over a range with
   a real diff (§1.1, §1.2). *Lane C: "the single highest-value fix is one line."*
2. Wire the detector into the closeout ritual per the §8.3 signature; correct
   `observability/README.md:76`, `glass_detector.py:31`, and `SYMPTOM-INDEX.md:44`, which now
   contradict the decision they cite (§1.4).
3. Implement docs/30 §5.4's signed decoupling (§1.4).
4. Report distinct `lane:key`, not occurrences, everywhere (§1.13); fix the double-harvest.
5. Enable stale detection under `--since` (§1.8); validate `--lane` names and empty producer
   globs instead of passing silently (§1.10).
6. `muster.sh`: de-position the SOFT clock's `head -1` exactly as [3] was de-positioned; make
   [3a] print on pass; count and report discarded rows; distinguish a missing repo from a
   rewind (§1.15).
7. Correct `MEMORY.md:138` (55 → 69); correct SYM-029's symptom sentence (§1.16); add
   `observability/__pycache__/` to `.gitignore`.

### 5.2 Semantic — Rab's pen

1. **`WINDOW_S` (§1.5).** A seven-day expiry on an unacknowledged alarm is a doctrine, and it
   is two days wider than the incident that motivated the stage. *Recommend: unacknowledged pain
   never expires; age it, never drop it.*
2. **`MAX_ALERTS` + post-truncation counts (§1.6).** *Recommend: filter acked first, keep the
   oldest escalated, and report the discard count on the glass.*
3. **Receipt re-arming (§1.7).** *Recommend: dedupe receipt alerts on content, not `ts`, so a
   restart cannot re-alarm; add an explicit "resolved by deletion" ack.*
4. **The answer key's scope (§1.9)** and whether the detector gains **site-awareness** — the
   fix for 7 of its 8 known-wrong verdicts.
5. **Signed-GLASS vs glass-by-reference (§1.11)** — should the two be distinguishable?
6. **Lane topology (§1.12)** — producer trees as renderers, and the unlisted `exporter.py`.
7. **Census scope (§1.13)** — are outbound request bodies "measured, stored values"?
8. **Vendoring `muster.sh` into the repo (§1.15).**

### 5.3 Consequence for the ordered sequence

Rab's order was `/circle` → disposition the backlog → build. **The Circle's result argues
against dispositioning next.** The census is not yet trustworthy — 22 keys are falsely `glass`
(§1.12), counts are inflated 17–45% (§1.13), 7 of 8 checked omissions are wrong (§1.9), and
request bodies are miscollected (§1.13). Dispositioning 77 entries against that census would
enshrine wrong judgments in a record whose entire purpose is that silence is **signed**.

*Recommend: §5.1's mechanical fixes first, then re-run the census, then disposition.* Rab's
call — flagged rather than silently reordered.

---

## 6. What the next Circle inherits

The §5.2 sheet, unsigned. Whether §5.1 was executed faithfully. The three-session recurrence
pattern (§3) as a standing hypothesis to test against S79's own work — **including this
document's**, which has not itself been audited by anyone.
