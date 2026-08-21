# 45 · The S105 Circle — findings on the S97–S104 arc

⟨claimed: Fable · S105 · 2026-08-21⟩

**Commission:** `docs/44` §3, run 2026-08-21. Four independent lanes, methodologically different
so they could not share a blind spot: **A** record provenance (git archaeology + byte reading) ·
**B** execution (ran every guard, stepped on four) · **C** empirical (re-ran P-1 on the corpus and
*looked at* 36 rendered pages) · **D** adversarial reasoning over the arc as a corpus.

**This file is the next Circle's Phase-2 reference.** It ends with a bequest (§6). The single
most important finding below is that **the last Circle's bequest was never collected**, so if you
are reading this at a later Circle: §6 is the part you must not skip.

Seeded suspicions were pinned at 01:43Z before any lane reported. **Three of my own predictions
were refuted by the evidence** and are recorded as such in §5 — including my prior that the
record would come back clean.

---

## §1 The verdict on the self-assessment (`docs/44` §2)

**Not the right diagnosis.** It is a rediscovery, mis-stated, of one of three distinct families.
All three of its claims are factually wrong:

| §2 claimed | measured |
|---|---|
| "seven sessions" | **eight** (S97–S104) — S97, the one session Fable did not author, is dropped |
| "five governance builds against two product" | **4:3** counted the same way on both sides |
| "every failure in the arc has one shape" | **~6 of 19** enumerated failures fit |

And `grep "docs/32\|proxy" docs/44` → **0**. See §2.

### The three families the diagnosis collapsed into one

**Family 1 — the claim describes the neighbour of what was measured.** This replaces "ceremony
substituting for verification", and the difference matters: in nearly every instance the
verification **did** happen, often excellently. What failed is the step after — the sentence slid
one referent sideways from the probe that licensed it.

| the probe that ran | the sentence that got written |
|---|---|
| glass, unscoped | "the observability layer is clean" (SYM-046) |
| `figure_coverage` on **a bundle** | a claim about **the book** (SYM-050) |
| uncovered at **stage 2** | quoted beside figure-pages at **stage 3** (§3 F2) |
| cost of the **pre-table-veto** build | "cost 5.6 ms/page" of the shipped one |
| S98 and S99 opened | "three closeouts cited it" — S100 never did |
| docs/37 absent from the diff | "docs/37 item 6 updated" |
| docs/32 exists and predicts this | a fresh diagnosis, citing nothing |

**Why more guards cannot fix Family 1:** every guard in this project verifies a *measurement*.
Family 1 lives in the gap between the measurement and the sentence, and **nothing in the
apparatus compares a claim to the probe that produced it.** Each new guard moves the verification
frontier *down* while the claims move *up* — which is why five governance builds coincided with a
*net increase* in debt. `close.sh` is the one artifact designed against this: its docstring
commits to printing **"VALUES, never ✓."** Two lanes independently named it the arc's best work.

**Family 2 — recording discharges the obligation** (Lane D). The ritual's honesty is real, and the
honesty is the release valve. §10 Known Failures absorbs unlimited debt at zero cost, and filling
it feels like discharge.

| probe | result |
|---|---|
| new OPEN SYM rows filed in the arc | 5 |
| pre-existing OPEN rows closed | **0** of 11 |
| net symptom debt for the evening | **+4** |
| SYM-044 ("the cheapest real repair available", one line) — namings / builds | **11 / 0** |
| lines changed in `convert_and_ship.py`, `watch_and_convert.py`, `analyst.py`, exporter | **0** |

**Family 3 — plain engineering defects.** SYM-044/047/048, the selftest bugs. Ordinary, found by
the guards working, handled honestly. No governance mechanism would have prevented them.

### Rab's actual question — "is the code too complicated for you, or is this systemic?"

**A false dichotomy.** Not code complexity: the arc's product code is ~900 lines, and the one
genuinely hard problem (separating prose-shaped from label-shaped text without killing the true
positive) was solved correctly, calibrated in the right order, and *stopped* at the right place.
Not convention load either — that is the symptom presenting as the disease.

**The machinery is fine and getting better. The machinery has no output.** Eight sessions, ~264k
words of governing corpus, three new tripwire suites, and a pipeline whose open-card state is
**byte-identical** at the start and the end of the arc:

```
S97 open 2026-08-20T19:47:07Z   held 4 · anchor 23 · pending 0 · drop 0 · events 137 · vault 6
S105 open 2026-08-21T01:36:39Z  held 4 · anchor 23 · pending 0 · drop 0 · events 137 · vault 6
```

Both clocks advanced eight times across that. **Neither clock is capable of noticing.**

---

## §2 The finding that outranks the commission: the last Circle's bequest was never collected

`docs/32-proxy-substitution.md` (2026-08-14, S78) named this disease six days before the arc, and
its §2 table already contains the arc's failures — including the literal row
`the ritual step written | the ritual step runs (bare python → exit 49)`, which is SYM-046's
shape. Its §6 made a **falsifiable standing prediction**:

> the next instance will appear in whatever we build next to enforce rules 1–3 — because that
> will be a guard, and a guard is a proxy … should be checked at the next Circle rather than
> assumed.

**The arc supplied at least five confirmations and scored none of them:** `coordination/selftest.sh`
red on its own assertion (S100) · `figure_coverage_selftest` dying on its success line, FAIL branch
included (S102) · `close.sh`'s two test bugs (S103) · the S99 claim-stamp convention breaking
muster's ledger parser within minutes of birth (S99 §10a) · and `close.sh`'s CI check being unable
to fire in this cadence (§3 F16).

`docs/33` §4 handed that request forward. **The last `/circle` before this one ran at S79
(2026-08-15).** `docs/44` §3's commission was written 25 sessions later and carries none of it.
`docs/32` §7 still reads **"Not signed"** while being cited as law in eight places
(`open.sh:12`, `:200`, `selftest.sh:4`, `SKILL.md:102`, `:124`, `close.sh:15`,
`echo/SKILL.md:23`, `sweep.sh:5`). **The codebase already obeys a document the register says was
never signed.**

By `docs/21`'s founding sentence — *"the project's expensive failures were never lost code — they
were lost knowledge: a defect rediscovered"* — the self-diagnosis **is that failure, performing
itself.**

---

## §3 Findings, most severe first

| # | grade | finding | evidence |
|---|---|---|---|
| F1 | VIOLATION | P-1's headline is computed on a **pre-S60 doubled-offset bundle**; **19/20 adjudicated uncovered verdicts FALSE**. The tool prints `report not trustworthy` on that run and `docs/41:468` named the hazard a session earlier | SYM-050 |
| F2 | VIOLATION | `uncovered 625 → 309` is **arithmetically impossible** (`uncovered` ⊆ `figure_pages`, `figure_coverage.py:383`) and does not reproduce. 309 is the **stage-2** value; shipped is **239**. Propagated to 6 surfaces incl. this Circle's own commission and `MEMORY.md` | Lane C §2 |
| F3 | VIOLATION | **Two confirmed false negatives** (Cyb p34, p78) and **a third true positive nobody recorded** (IV p81, FIGURE 3.1 chopped into a garbage table, caption intact). The project had been reasoning from n=1 | SYM-049; §6 |
| F4 | VIOLATION | One of the three appended corrections is **itself false** — S100 never cited glass. SYM-046 recurring inside SYM-046's own remedy | `sessions/S100:132` vs blob `bbf6e70` |
| F5 | VIOLATION | The S102 withdrawal reached **no permanent surface** — ledger row, CHANGELOG and `MEMORY.md` all still asserted "one flag on the born-digital corpus, and it is TRUE" | `CLAUDE_README.md:1997`, `CHANGELOG.md:56` |
| F6 | VIOLATION | `acceptance.py` red ~11 sessions **because the product was fixed** — `:42` asserts `recent_audits` unrendered; it renders at `room.rs:93`, `:112`, `room.js:505` | Lane B |
| F7 | VIOLATION | **CI runs zero governance checks**; `windows-converter/` has no CI job at all | `.github/workflows/ci.yml` |
| F8 | VIOLATION | `"5.6 ms/page"` is the **unshipped** build's cost. Shipped: 37 ms/page (IV), 72 (Cyb). Also violates docs/34 — no numerator, denominator or configuration named | Lane C §3 |
| F9 | VIOLATION | The **80-word ledger cap violated 7 of 8**, mean 2.0×, worsening monotonically. docs/21:184 ships the check command; it has never been run. The only compliant row is the one Fable did not write | `CLAUDE_README.md:1992-1999` |
| F10 | VIOLATION | `.agents/skills/muster/` prints `ALL TRIPWIRES FIRED — 22/22, exit 0` while missing `close.sh`, `--enforce`, `SYM-046` and `CI` entirely, and pointing at a `.Codex/` path that does not exist. Untracked and **not gitignored** | Lane B §4 |
| F11 | VIOLATION | "S101 and S102 both closed reporting clean" is false — both were **silent** on CI. "Three closes deep" was **two**. On three permanent surfaces | Lane A F10 |
| F12 | VIOLATION | S104 §6 "Implementation Delta" names docs/37 as updated; it is absent from the diff. docs/21:105 designates that section machine-**derived** | Lane A F9 |
| F13 | VIOLATION | §15 Symptom Signatures absent **6 consecutive sessions**, and the zero-area-connector defect never reached the index. docs/21:119 — *"the index is the product"* | now fixed, SYM-049 |
| F14 | EROSION | The table veto is **0-for-11 on Cybernetics** — vetoed a Watt steam engine, a line chart, a Pask diagram, each at 99.5–100 % "table" coverage. The class called "not measured on a real specimen" had already fired 15× in the run that produced the headline | Lane C §5 |
| F15 | FRAGILE | p84's margin is 7–12× on the thresholds and **zero** on the table veto — `find_tables` gave it 0.0 while giving structurally similar diagrams 1.0. Survival is a coin flip that landed right. On Cybernetics **two of the three vetoes never fire at all** | Lane C §6 |
| F16 | FRAGILE | `close.sh`'s CI check **cannot fire in this cadence** — the close lands 1–3 min after the last work commit, so CI is always `NO-RUN`. It can only catch a red that predates the session | Lane B, Lane D D-10 |
| F17 | EROSION | The tag law — *"the spine of the whole session"* — is dead: 14.4 tags/1,000 words at S97 → **0 in S103 and S104** | Lane D D-5 |
| F18 | EROSION | The relay has **2 entries, both Fable→Codex, 0 carries**; its *write-back* half was silently dropped in 4 consecutive closes while its selftest stayed 11/11 green. Stamps 15:0, trailers 49:0 | Lane A F3/F4 |
| F19 | EROSION | One "the guard bites" case in each of two suites is a **proven constant** — `coordination/selftest.sh:82` stayed green while the real guard tripped red; `figure_coverage_selftest.py:191` is arithmetic on literals | Lane B, proven by planting a real violation |
| F20 | EROSION | `/echo` served **1 commission in 7**; its Phase-0 carve-out was invoked or silently assumed 6/6 times. A gate that always opens | Lane B §3 |
| F21 | EROSION | SYM-044's Guard column names a tripwire that **does not exist** (`docs/37 §4 T3, 6/6` — docs/37 contains no "6/6"; it is S93 prose about an ad-hoc probe) | Lane A F11 |
| F22 | EROSION | `docs/19:68` named a **four-generation-stale** installed exe, cited by line number in the S103 ledger row | now fixed |
| F23 | EROSION | The scan lane renders as `with source figures 0 · UNCOVERED 0` — indistinguishable from a clean bill of health, on a bundle carrying 63 assets across 62 pages | Lane C §8 |

**Cost of the arc, measured:** governance/docs **3,644 lines** vs product **1,098** = **3.3:1**;
strip the unwired module and the dispositions churn and wired shipping product code is **233
lines** = **15.6:1**. By commits: **44:7**. Mean committed work per session: **8.7 minutes**.

---

## §4 HELD — checked and clean, stated because absence of findings is a finding

- **§1 Session Intent is byte-unedited in all eight closeouts.** Extracted from each opening
  commit blob and compared after CRLF normalisation. This is `docs/21`'s founding requirement,
  made checkable at S104, holding across the whole arc without exception. **The arc's best-kept law.**
- **`deb1113` was purely additive** — no claim was edited away. The no-rewrite law held.
- **S102's withdrawal is a model withdrawal** — targets a real section, quantifies, supplies the
  replacing statement, preserves the surviving true positive. F5 is about where it failed to
  travel, not its quality.
- **All four tripwire counts are honest**, re-measured: muster 26/26 · echo 5/5 · coordination
  11/11 · figure_coverage 17/17. **Muster's suite is the gold standard** — it invokes the real
  scripts 14× against fixture repos and carries an explicit labelled positive control.
- **The relay's shape guards genuinely bite** — three real corruptions planted, three alarms.
- **P-1's staircase reproduces exactly**: IV 706→477→352→269, Cyb 68→57, p84 flagged at every
  stage, all four measured specimens to the decimal. **Detection-level precision is good** —
  13.3 % false alarms (2/15); 13 of 15 flagged pages carry a real captioned FIGURE.
- **P-1's engineering was honest**: acceptance fixed *before* thresholds, the obvious metric
  (line count, 32 vs 29) measured and discarded, and the session **stopped** rather than tune to
  a sample of two.
- **`close.sh` is correct where it can act** — `--enforce` for the right reason, UNREAD never
  claims clean, only a MEASURED red exits 1, CI red path tripwired against the real red `534a6c0`.
- **CI, MEASURED**: three `completed failure` runs sit exactly where S103 said the red was.

---

## §5 Where the auditor was wrong

Recorded because a Circle that only convicts is not measuring itself.

1. **"Lane A will come back mostly clean — this project is good at writing things down."**
   Refuted: 21 findings. My model of the project was wrong.
2. **"The false-alarm rate among the remaining 269 is still high."** Refuted at the detection
   level — 13.3 %. The vetoes are **better** than their own closeout claims. It is the per-page
   *verdict* that is noise, and that is the bundle's fault, not the veto's.
3. **"At least one selftest lacks a positive control."** Refuted — all four have one. The real
   defect was sharper and elsewhere: the *bite* cases are what do not bite (F19).
4. **"p84 survives by luck — a threshold nudge would lose it."** Refuted on the two threshold
   vetoes (7–12× margin) and **confirmed** on the table veto, which is not a threshold at all.

---

## §6 THE BEQUEST — what the next Circle must collect

`docs/32` §6's prediction went unchecked for one full Circle and five confirmations. **Do not let
that happen twice.** This section exists to be collected, not admired.

1. **Check `docs/32` §6's prediction against whatever was built since this file was written.**
   It has now confirmed five times. If it confirms again, stop treating it as a prediction and
   treat it as a law.
2. **Check whether Family 1 has a check yet.** The open question this Circle could not close:
   *what compares a claim to the probe that produced it?* Today, nothing. `close.sh` is the only
   artifact that even tries.
3. **Re-measure P-1 on a CLEAN bundle.** Every number in `docs/44`, `docs/41`, `CHANGELOG`, the
   S102/S104 rows and `MEMORY.md` about Investment Valuation is computed on a poisoned bundle.
   Until that re-run exists, P-1's large-book behaviour is **UNREAD**, not "noisy".
4. **Four specimens now exist for P-2**, where the project had one: Cyb **p84** (vector diagram,
   labels landed as prose) · Cyb **p34** and **p78** (vector figures silently dropped, SYM-049) ·
   IV **p81** (raster figure destroyed in place, caption intact pointing at nothing). These are
   two *different* failure modes and P-2 needs both.
5. **UNREAD from this Circle, stated so it is not mistaken for clean:** 219 of the 239 IV
   uncovered pages were not adjudicated; the other four anchors were not measured at all; the
   fragmentation class (SYM-049) is verified for Cybernetics only; and CI's conclusion for
   S104's own commits was never observed by anyone.
