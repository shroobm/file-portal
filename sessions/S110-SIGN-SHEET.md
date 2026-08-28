# S110 SIGN SHEET — what closes the session, and what changes the next one

⟨staged by Fable lane · occupant Claude Opus 5 · 2026-08-27, on Rab's ask: *"what could I just sign
on, so we can do the proper closeout with codex"*⟩

**Blocks A and B are SIGNED (Rab, 2026-08-27).** C and D remain open; blank ink is not yet decided.
Sign by replying in any session ("sign C1, C2" works) or annotating this file by hand.

**Why this sheet exists.** S110 is lane-closed and not MUSTER-closed: Fable recorded its sitting
under §25–§29, both clocks still read S109 / `ab544d1`, and the branch is clean but ahead of its
local upstream reference. Codex is authorized as last closer and held. The items below are what
actually stands between that state and a proper close — plus the three protocol holes this session
found while looking.

---

## A — UNBLOCKS THE S110 CLOSE ✍ **SIGNED 2026-08-27**

| # | Item | Evidence / why | SIGN |
|---|---|---|---|
| A1 | **Fable commits the memory library's S109 residue** — `MEMORY.md` TIME-STATE `S108/e4d731e → S109/ab544d1`, `cookie-tally.md` header `79/3 → 82/3 (+1 to Codex)` and ledger entries #80–#82, plus the two untracked topic files (`subagent-orchestration-law.md`, `door-brief-convention.md`) that `MEMORY.md:176` and `:201` **already link** | The memory repo's last commit is `53d5c77`, **S108-era**. S109 closed 2026-08-25. This is not residue — it is **S109's entire soft-clock move, uncommitted for two days.** Claude Code's namespace, so Fable's lane | **✍ SIGNED** |
| A2 | **After Codex's ledger row lands, Fable writes and commits the S110 soft-clock move**, mirroring the row's SHA | The muster requires both clocks advanced together. If HARD goes to S110 while the tally reads S109, the next open correctly reports drift. A2 **cannot precede A3** — it needs the row's SHA | **✍ SIGNED** |
| A3 | **Codex writes the S110 ledger row** — ≤80 words, **separate follow-up commit, never `--amend`**, carrying both claims `⟨Fable⟩+⟨Codex⟩` | The row belongs to whoever closes last; Fable's sitting closed at `f59589c9`. `--amend` orphans the SHA just written (SYM-016's family). S108's row is the two-claim precedent | **✍ SIGNED** |
| A4 | **The close pushes — fetch first** | An unpushed close is how the 2026-08-16 fork grew 52 commits deep. `24 ahead` is measured against the local remote-tracking ref; whether origin moved is `UNREAD` without a fetch | **✍ SIGNED** |
| A5 | **Custodial fallback**, on Codex's own four properties: if Fable is unresponsive, Codex may commit Fable's exact current bytes — **unchanged · hash-recorded · attributed Fable-authored · never automatic** | A held close is worse than a declared boundary crossing. The four properties are what separate escrow from taking authorship | **✍ SIGNED** |

---

## B — THE THREE PROTOCOL HOLES THIS SESSION FOUND ✍ **SIGNED 2026-08-27**

| # | Item | Evidence / why | SIGN |
|---|---|---|---|
| B1 | **The close commits the memory library.** Add to `close.sh` and `muster/SKILL.md` | **No step covers it today.** `grep` for "commit the memory library" across the memory topics and the muster skill returns nothing. That is why S109's clock sat two days — and why `open.sh`'s `[2] SOFT clock ✓` has been reading **uncommitted bytes**. The muster validates the clock's *value* and never its *durability* | **✍ SIGNED** |
| B2 | **Disagreement gets a TERMINAL STATE.** Two rounds, then it is recorded as a *preserved disagreement* — both readings, both probes, named — and the close proceeds. **No forced alignment** | A close gate that requires agreement makes **conceding the cheapest path to closing**, and the pressure peaks when both lanes are deep in a session. It would also have forbidden the best output of the day: Codex's census *"I preserve these disagreements rather than fitting them"* (P-0/P-1 terminal vs residual, J2, `SYM-039`, BRIEF §6 item 5). **The disagreements were the finding.** ⚠ B2 constrains Codex as much as Fable — Fable drafts, **Codex endorses or amends before it is written anywhere** | **✍ SIGNED** |
| B3 | **`close.sh` REGISTER splits STRUCK from ADDED** and prints the delta as debt, the way `DEBT` does for SYM | §I currently reads *"every session either strikes an item **or adds one**"* — so **adding satisfies the gate meant to force progress.** That is how a session producing 55 governance items passes clean. Lands with a tripwire, stepped on both ways | **✍ SIGNED** |

---

## C — PACING: THE ACTUAL BUG *(open)*

*Rab's diagnosis, in his words: "the need to work quick has caused situations where you generate
your own debt that you fix. This has been the bug."* Measured: 17 error rows filed in one sitting,
and the session's product was their repair. **Zero lines of product code.**

| # | Item | Evidence / why | SIGN |
|---|---|---|---|
| C1 | **The tag is decided at PROBE DESIGN, not at write-up.** Before a claim enters a record: name the predicate · name what else could produce this number · name the second differently-shaped method — **or it is `Observed`, never `Verified`** | Today the tag was applied while writing the sentence, so it recorded *confidence* rather than *method shape*. All four falsified claims had exactly one predicate. This is the only rule that stops them **at the source** rather than downstream, where Codex caught three and accident caught one | ______ |
| C2 | **Rab names what the session is for, at open.** One line | Given full autonomy, Fable chose census → sweep → backfill → counter fix. All defensible; **none was C0.** The roadmap existed and nothing in the stack noticed it was ignored | ______ |

---

## D — THE ONE THAT SHIPS *(open — no default offered)*

| # | Item | Evidence / why | SIGN |
|---|---|---|---|
| D1 | **C0: does a book ship with its losses named, or must the audit be green?** | The north star says *"with every loss named."* C0's done-when is **2 of 3 met** — Ashby converted end to end (`wall_s 1088.7`, events 137→147) and `events.jsonl` advanced; only the **held/ 5** disposition remains. If ship-with-losses-named, C0 closes this week on five yes/no calls. If audit-must-be-green, it is days of detector calibration. **This is the only item on this sheet that moves the north star, and the only one Fable will not recommend** | ______ |

---

## ORDER OF OPERATIONS — forced, not preference

1. **Fable: A1.** Separate repo; does not touch `file-portal`.
2. **Codex: A3 → A4.** Ledger row, fetch, push, hand-observe CI, report the actual verdict *including any red or `UNREAD`*.
3. **Fable: A2.** Needs the row's SHA, so it cannot precede step 2.
4. **Either lane runs `open.sh` and pastes the card** as proof both clocks reconcile. **That is the acceptance check — not either lane's assertion.**

**Ownership for B:** B1 and B3 are `muster`/`close.sh` edits — Fable's lane per the 2026-08-27 split, each landing with its own tripwire. **B2 is drafted by Fable and endorsed or amended by Codex before it is written.**

## ASSURANCE CHECKS — what stops this being got wrong

- **Both repos are git.** Every step in A is reversible by `git reset`. Nothing is destructive.
- **A2 is verifiable before anyone depends on it:** run `open.sh` and read `HARD clock ✓ … ancestor of HEAD` and `SOFT clock ✓`. That is exercising the guard against the change itself, the CASE 35/36 method.
- **A1's completeness is exactly checkable** — `git status` clean in the memory repo afterward. No judgment involved.
- **B3 ships with a tripwire stepped on both ways.** Twice proven this session: with the fix `52/52`; with the bug restored, the case fails.
- ⚠ **The named hazard is `ERROR-BIN.md` ERR-017 recurring in a second repo:** writing to a repo *after* committing it. The order is **write → commit → nothing.** A "confirmation" touch of the memory library after A1 reproduces today's worst protocol error.
- ⚠ **Unmitigated: something Fable does not think to check.** The only real cover is Codex, which falsified 3 of 4 `Verified` claims today.

## WHAT THIS SHEET DOES NOT COVER

- The **S108 sign sheet's 15 items**, still unsigned.
- The four commissions in Rab's own words that no register tracks — `docs/30` §5 (incl. the *"research day"* queued ahead of the Valentine, unheld in 32 sessions) · the S62 queue-order contract that `room.js:172` renders to him on the glass every launch · `docs/40`'s four theses with no adversary · `docs/36` §8.
- **J15**, live on the close card during Fable's own close: `DEBT open SYM 4` against a real 18. ~~The same defect shape was fixed in `open.sh` this session and its twin left in `close.sh`.~~ ⚠ **THAT CLAUSE WAS FALSE WHEN WRITTEN — corrected `Observed` 2026-08-27 (E1).** What this session fixed in `open.sh` was the **register** counter (`[A-F]` → `[A-FJ]`, CASE 35) — a *different line*. **J15's own instance at `open.sh:251` was untouched since 2026-08-24**, so the card kept printing `4 open` against **18**, under-reporting by 4.5× at every session open. As written, this sentence pointed the next fixer away from the live site. **NOW FIXED**: the counter reads both `` `open` `` and `**OPEN**`, anchored on the status column so a marker quoted inside another row's prose is not counted, tripwired as **CASE 37** and stepped on both ways — 54/54 with the fix; with the bug restored it reads `4 row(s), 1 open` and both assertions fail. **`close.sh`'s DEBT twin is still live — that is B3.**
