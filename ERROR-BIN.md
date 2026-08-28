# ERROR BIN — the register of the assistant's own mistakes

**Retrieve by the SHAPE OF THE MISTAKE, not by what broke.** You are here because you are about
to do something — relay a verdict you did not produce, quote a count, measure a file, tell Rab a
number, background a command, assert that something is unfiled. Read the **CLASS table** first
and check whether the move you are about to make is already in it. The rows underneath are
evidence for the classes; the classes are the product.

**These are Claude's own errors, self-reported.** Opus 5, Fable lane. They are not product bugs
and they are not hypotheticals — they are reasoning and instrumentation failures by the
assistant. `SYMPTOM-INDEX.md` indexes what the *system* does wrong; `OPEN-TASKS.md` indexes what
the project has *not done*; this file indexes what the *assistant* does wrong. Nothing here is
softened. A row that says a wrong claim reached the principal and the other vendor says exactly
that.

**Seeded 2026-08-27** from ten error lines self-reported by a single working session (Desktop,
Fable lane), on Rab's instruction that session: *"Any error you have, document that in claude
prompt error bin, send it as a line of error code, to a sub agent that digests it into the error
bin markdown."* Rows are the session's own words, restructured; the class table, the commonality
section and the append protocol are this digest's work and are tagged accordingly.

**Extended 2026-08-27**, same day, same session: rows **011–013**, two new classes, and every
derived count re-run. Rows 001–010 are byte-identical to the seeding pass — this file appends, it
does not rewrite. **Row 013 was produced by the verification run of this file's own first pass**,
and is filed rather than quietly fixed.

**Extended again 2026-08-27**: rows **014–016**, one new class, counts re-run a second time. Rows
001–013 byte-identical. **Row 014 is the most consequential row in this file** — a `Verified`
number that was numerically identical to its own inverse, which reached Rab, the Codex bus *and*
a permanent `SYMPTOM-INDEX.md` row before another vendor falsified it. Read §C.6 before trusting
any count in this repo, including the ones in this file.

**Extended 2026-08-28 by the Codex lane under Rab's transferred S111 commission:** rows
**017–019**, three distinct classes. Provenance is intentionally split: Codex independently
caught 017; Fable caught 018 by reading its own adjacent contradictory output; Rab's question
forced the liveness probe that caught 019. The old §C analyses remain explicitly scoped to
rows 001–016; §C.7 appends the current 19-row reading instead of silently rewriting history.

| tag | meaning |
|---|---|
| `Observed` | a command was run or a row was counted; the result is quoted |
| `Inferred` | a reading of the evidence in this file, not a measurement |
| `Unknown` | named because it is not known, and should not be guessed |

---

## §A THE CLASSES — the actual product

*Derived from the nineteen rows below (`Observed` — every class name and every rule text comes
from the input lines; the "from the inside" column is the digest's characterisation, `Inferred`).*

| Class | What it looks like from the inside | The rule that prevents it | Rows |
|---|---|---|---|
| **DELEGATED-TRUST** | You hold a verdict you did not produce. It arrives wearing a confidence word — `Verified`, `confirmed`, `done` — so it reads like a measurement. Nothing about it feels like a quotation | A consequential act (a message to Rab, a post to the bus, a struck register line) needs an `Observed` premise of **your own**. A subagent's `Verified` is `Reported`, not `Observed` | 001 |
| **PROBE-SHAPE** | The probe runs. It returns numbers. Nothing errors. The numbers are real — they simply answer a different question, because your model of the artifact is not the consumer's model of it | Before measuring against a file, read how the **producer** indexes it. Any count that enters a claim gets a second method of a **different shape** first | 002, 004, 015 |
| **REGISTER-MISS** | The finding feels new. Nothing in memory contradicts it, and the absence of a contradiction reads as the absence of a record | "Unfiled" / "in no register" / "nobody has noticed" is a claim about a **file** and requires a grep of that file. A defect rediscovered is a MUSTER failure (`docs/21` §5 rule 4) | 003 |
| **METER-CONFUSION** | A number is on the panel, it has plausible units, and it is the only number in view. You report it. It measures the neighbour of what was asked | When reporting a number the user asked for, confirm the meter measures **the thing they named** | 005 |
| **PREMATURE-ALARM** | The evidence is not where you looked, so you conclude it does not exist — and you say so before the probe has finished running | Finish the probe before narrating its verdict. A truncated read is **UNREAD**, not absent | 006 |
| **HARNESS-MISUSE** | The command returns 0. The tooling reports success. The work never happened, or happened somewhere else, and the silence afterwards reads as calm | A backgrounded command must be the whole job, not a launcher for another background job. Never restore from a path whose write you did not confirm — verify the backup exists before destroying the original | 007, 008 |
| **QUOTING** | A script dies on its own delimiters: backslashes, nested quotes, a trailing `\'`, a regex mangled in transit. Cheap when it crashes; expensive when it half-writes | Anything containing backslashes or nested quotes goes in a FILE via `Write`, never a heredoc | 009, 013 |
| **OVER-CLAIM** | A list of candidates is reported as a list of findings. Most of it is right, which is what makes the rest of it dangerous | A delegated list is a list of **candidates**; every item that will produce a recorded change gets its own probe | 010 |
| **STALE-GROUND** *(added 2026-08-27, row 011)* | You are writing the GROUND block for a fleet. The framing numbers came from an earlier report and feel like settled background rather than claims, so they get stated instead of probed — and then every downstream agent inherits them as given | GROUND is a claim like any other and gets a probe **before** it is handed to anyone. A **residue** section is the least-verified part of a report, not the most | 011, 016 |
| **DENOMINATOR** *(added 2026-08-27, row 012)* | Two totals appear in one session. Both were honestly obtained; neither is wrong. Nothing states what either one counts, so the reader has no choice but to assume they are comparable | `docs/34`: every measured number names its **numerator, denominator and conditions**. Two totals of different populations must never appear in one session without their populations stated | 012 |
| **PREDICATE-COLLAPSE** *(added 2026-08-27, row 014)* | One probe, one number, and it is internally consistent every way you turn it. What is invisible from inside is that the number is summing **two or more different tests** over the same population — so it is not wrong by an *amount*, it is wrong by a *question*. The tell, and it is the only one: it stays plausible when inverted | When a probe produces one number, ask what DISTINCT predicates that number is summing. A count is a claim about a population **and** about a test; two tests over one population are two numbers, never one. **A number that looks plausible in both directions is evidence of collapse, not of correctness.** This class is **not self-catchable** — see §C.6; it needs an independent prober denied your relay, registers, prior reports, memory and expected counts | 014 |
| **ORDERING** *(added 2026-08-28, row 017)* | A write after the commit feels like confirmation of the state just committed. The confirmation is itself the act that invalidates that state | When a clean committed sidecar is required: perform every write first, commit last, then no further write. Read-only verification may follow; the last write must be the commit | 017 |
| **STATUS-THEATRE** *(added 2026-08-28, row 018)* | A literal health word sits beside real probe output. Because it cannot render failure, its confidence is unrelated to what the probe found | A status claim must be derived from the probe and must have a failure branch. A health word that can only print success is decoration | 018 |
| **PHANTOM-MONITOR** *(added 2026-08-28, row 019)* | Launch or remembered output is treated as current liveness. A one-shot that fired once is remembered as a watcher that still exists | Claim “running” only from a same-turn PID/handle or a fresh heartbeat. A monitor persists after events; a one-shot is a trigger | 019 |

**14 classes, 19 rows.**

---

## §B THE ROWS

*Rows 001–016 were `Observed 2026-08-27` by the session that made them — self-reported, not
re-verified by this digest, with the exceptions their cells name. Rows 017–019 were filed by the
Codex lane on 2026-08-28 from the preserved S110 record; each row names who actually caught it.*

| ID | Class | Surface | What I claimed | What was true | How it was caught | The rule that would have prevented it |
|---|---|---|---|---|---|---|
| ERR-2026-08-27-001 | DELEGATED-TRUST | census subagent → Rab + the Codex bus | Relayed a subagent's `Verified` about manifest pointer drift to **both the principal and the other vendor** without running the probe myself | The claim was wrong three ways | Only when I read `bench.py:118` **for an unrelated reason** | A consequential act needs an `Observed` premise of MY OWN; a subagent's `Verified` is `Reported`, not `Observed` |
| ERR-2026-08-27-002 | PROBE-SHAPE | held bundle `.md` files | Measured manifest line pointers against the RAW file and reported drift of −18/−18/−20/+18 as `Verified` | The audit indexes the **BODY** — `bench.py:118` says so outright; most of the "+18" was the frontmatter my probe never stripped. Body-index delta for Ashby is **+88** | Reading the consumer's source | Before measuring against a file, read how the PRODUCER indexes it |
| ERR-2026-08-27-003 | REGISTER-MISS | `SYMPTOM-INDEX.md` | Asserted the pointer-drift finding was "in no register" | It is **SYM-025**, filed S76, **with a built fix** (`Bench._resolve_zone_line`, excerpt-anchored) that already covers the danger I claimed was live | The resolver's own docstring naming SYM-025 | A defect rediscovered is a MUSTER failure (`docs/21` §5 rule 4); grep the registers BEFORE the word "unfiled" |
| ERR-2026-08-27-004 | PROBE-SHAPE | `SYMPTOM-INDEX.md` | Regex `^\| (SYM-\d+) \|` counted **53** rows and I built a §C comparison on it, concluding "SYM-039 is listed open but is not open" | `grep -cU` says **56**. SYM-037/038/039 carry `*(was SYM-0xx, ThinkPad lane; renumbered at the S86 fork merge)*` between the id and the pipe, so my regex dropped exactly those three. **SYM-039 IS open.** My conclusion about it was an artifact of my own instrument | Cross-checking against `grep`, a differently-shaped method | Any count that enters a claim gets a second method of a DIFFERENT SHAPE first |
| ERR-2026-08-27-005 | METER-CONFUSION | usage reporting to Rab | Told Rab context was **"99.3 % free"**, from the harness `total_tokens left` counter | That is a **session token budget**, not the context window; the real bar was 324.8k/1M = **32 %**. Off by ~45× on the quantity he actually asked about | Rab sending a screenshot of the real meter | When reporting a number the user asked for, confirm the meter measures the thing they named |
| ERR-2026-08-27-006 | PREMATURE-ALARM | Ashby `manifest.json` | Announced to Rab **"the data isn't there, the census may have fabricated it"** and began drafting a correction | The fields existed; I had truncated my own print at 2600 chars and never reached them | Seconds later, by grepping the raw file | Finish the probe before narrating its verdict; a truncated read is UNREAD, not absent |
| ERR-2026-08-27-007 | HARNESS-MISUSE | Bash `run_in_background` | Nested `( … ) &` INSIDE an already-backgrounded command; the outer command returned instantly and the relay watcher died at once | The watch reported nothing and **I nearly read its silence as calm** | The task-completion notice arriving in ~2 s | A backgrounded command must be the whole job, not a launcher for another background job |
| ERR-2026-08-27-008 | HARNESS-MISUSE | `open.sh` backup/restore | Wrote `cp X /tmp/f \|\| cp X <scratchpad>/f` then restored from the SCRATCHPAD path; the `\|\|` short-circuited, so the backup only ever existed in `/tmp` | The restore silently failed and left `open.sh` carrying the reintroduced bug | The restore's own `No such file`, plus a follow-up grep | Never restore from a path whose write you did not confirm; verify the backup exists before destroying the original |
| ERR-2026-08-27-009 | QUOTING | bash heredoc → python → regex | Three separate failures in one sitting: a `print f""` syntax error, an unterminated string from a trailing `\'`, and `(?<!\\)\|` mangled to `(?<!\)\|` | Each aborted the script; twice nothing was written, once I had to verify no partial write had occurred | Tracebacks | Anything containing backslashes or nested quotes goes in a FILE via `Write`, never a heredoc |
| ERR-2026-08-27-010 | OVER-CLAIM | report to Rab | Reported the census's **"13 items already done"** as a finding without re-probing | At least **3 were not done** — B17, B18 still open; J10 only half-moved, and striking it would have claimed **C0 closed** | Re-probing each myself before striking | A delegated list is a list of CANDIDATES; every item that will produce a recorded change gets its own probe |
| ERR-2026-08-27-011 | STALE-GROUND | GROUND handed to a **7-agent fleet** | Asserted in the GROUND block that `sessions/` holds **"~110 closeout files"** and that **"every other session's own left-open section is UNREAD"** — and dispatched 7 agents on it | **Both halves false.** Measured after the fact by me: `ls -1 sessions/ \| wc -l` → **48**, closeout-shaped → **46**, earliest is S67. And `OPEN-TASKS.md:7` says in its own header that it was built "by sweeping **all 42 closeouts** in `sessions/` (S67→S106)" — 46 minus S107/S108/S109/S110 = **exactly 42**. The files were swept **five sessions ago** | **By the fleet itself** — multiple agents refused the premise and reported the refutation as their headline, which is the behaviour the orchestration law's *"deviation is the report"* clause exists to buy | I inherited the "~110 / all unread" figure from a census subagent's **RESIDUE** section and passed it on as GROUND without one `ls`. GROUND is a claim like any other and gets a probe before it is handed to anyone; a residue is the least-verified part of a report, not the most |
| ERR-2026-08-27-012 | DENOMINATOR | numbers reported to Rab | Quoted **"147 open items"** to Rab and wrote **"104 open"** into `OPEN-TASKS.md` §0 in the same session, without ever naming that they count different things | Not a contradiction, but presented as if comparable: **147** spans FIVE surfaces (`OPEN-TASKS` + `SYMPTOM-INDEX` + the sign sheet + BRIEF seams + S110 §23); **104** is `OPEN-TASKS.md` alone, after the day's 8 strikes. A sweep agent flagged the pair as a **live conflict in the tree** and could not tell which denominator was right | A subagent raising it as a deviation — not by me | `docs/34`: every measured number names its numerator, denominator and conditions. Two totals of different populations must never appear in one session without their populations stated |
| ERR-2026-08-27-013 | QUOTING | **this error bin's own verification run** | *(Reported by the digester; filed because it is real.)* **ERR-009's exact failure reproduced live** while the bin was being verified: `(?<!\\)\|` mangled through the shell into `re.error: missing ), unterminated subpattern` | The rule ERR-009 states was correct, and applying it — script in a file, not a heredoc — fixed it immediately | The traceback | **A rule filed in this bin is not a rule followed.** ERR-009 recurred inside the very run that documented it, which is the single best evidence that this file must be **READ at the start of a task**, not only written at the end |
| ERR-2026-08-27-014 | **PREDICATE-COLLAPSE** | five held bundles; `SYMPTOM-INDEX.md` **SYM-025** | Measured **"21 of 23 stored pointers fail to resolve on their own excerpt"**, tagged it `Verified`, **sent it to Rab, wrote it into SYM-025 as a corpus-wide upgrade, and relayed it to the Codex bus** | **FALSIFIED cross-vendor** (`MSG-CDX-0017`) by two independent probes, one a **CLEAN-ROOM probe denied the relay, the registers, prior reports, memory and expected counts.** I had **collapsed three predicates into one**: exact physical BODY line at the stored coordinate = **18/23 miss**; producer-faithful paragraph start = **17/23 miss**; the ACTUAL Bench resolver = **21/23 `anchor=excerpt`** — i.e. **21 SUCCESSES**. **The 21 I reported as misses is the count of production resolver SUCCESSES; my claim was numerically identical to its own inverse.** My load-bearing **negative control was also dead**: `c5afd9ed` #2 is producer-faithfully **CORRECT** at body line 2400, and its eight-token excerpt merely SPANS lines 2400–2401, so a one-line check returns drift — **a schema/resolver mismatch at ZERO line delta, not a stale pointer** — while `b7b711d4` #1 is a **distinct defect class** my single number had merged with it | **ONLY by the other vendor.** Nothing in my own method could have caught it: a wrong number that equals its own inverse survives every internal consistency check I ran | When a probe produces one number, ask what **DISTINCT predicates** that number is summing. A count is a claim about a population **and** about a test; two tests over one population are two numbers, never one. **And a number that looks plausible in both directions is evidence of collapse, not of correctness** |
| ERR-2026-08-27-015 | PROBE-SHAPE | `wiki/roadmap.md`, the value-ranking page | Was **one line from writing "0 vaulted books"** into the page that ranks all project value, off `ls ~/ml/vault` returning 0 | **`~/ml/vault` IS NOT THE VAULT.** `open.sh:24` resolves `VAULT_DIR` to `$HOME/Documents/Obsidian/Obsidian and Zennotes Vault/Library`. On the correct path a `-maxdepth 1` count **also** returns 0, because the six notes live in subdirectories and the muster counts `*.md` at any depth. **Two independent ways to read a populated vault as empty, inside one measurement** | Checking how `open.sh` resolves the path before trusting my own, then reconciling my 0 against the muster card's **6** | Two readings that disagree are a **finding**, not a tie to be broken by whichever ran last — reconcile them before either enters a claim. **The 0/week figure I was checking turned out CORRECT for an unrelated reason**, which would have made the wrong probe look confirmed |
| ERR-2026-08-27-016 | STALE-GROUND | the relay bus | Let my own `gate.py` **beat go 89 minutes stale** while completing two full work units, on a bus whose peer heartbeats every **30 seconds** | The peer could not see what I was doing or whether I was live; I had also **posted a conflict and then done two work units without checking for its reply** | **By Rab, not by me:** *"make sure to address relay consistently"* | This is ERR-011's stale-GROUND class pointed at the **bus** instead of at a fleet. A beat is a claim about **NOW** and it decays; the fix adopted is that **a relay check is the FIRST step of every work unit**, not a thing done when remembered |
| ERR-2026-08-27-017 | ORDERING | `coordination/ack-fable.json`; commit `b8dd262` followed by `gate.py beat` | Committed the sidecar, then announced “Tree is CLEAN” and “Zero writes” in a beat | The beat wrote the same sidecar after the commit, immediately leaving it dirty; the cleanliness announcement caused the state it denied | Codex re-grounded, observed ` M coordination/ack-fable.json`, and named the self-invalidating sequence (`coordination/relay.md:4023-4034`) | When clean committed state is required: make every sidecar write first, commit last, then no further write. Read-only verification may follow; the last write must be the commit |
| ERR-2026-08-27-018 | STATUS-THEATRE | S110 sign-sheet commit command | Printed a hardcoded `(clean — nothing blocks Codex's close gate)` directly below status output | The preceding `git status --short` printed ` M coordination/ack-fable.json`; the literal could not report failure | Fable read the adjacent contradictory output and immediately wrote “my own echo lied”; its later bus account is `MSG-FAB-0043` (`coordination/relay.md:4319-4335`) | A status claim must be derived from the probe and must have a failure branch. A health word that can only print success is decoration |
| ERR-2026-08-27-019 | PHANTOM-MONITOR | S110 relay/repository watcher | Reported the watcher live twice | It fired at 14:33 on `e0c371a`, executed `exit 0`, and had no matching process for about seven minutes; it was a one-shot described as a monitor | Rab asked “How are you holding the watcher live?”, forcing a same-turn log/process probe; Fable's later bus account is `MSG-FAB-0043` (`coordination/relay.md:4319-4335`) | Never report a background process running without a same-turn liveness probe. A monitor persists after events and leaves a fresh heartbeat; a one-shot is a trigger |

---

## §C WHAT THESE HAVE IN COMMON

**Historical denominator boundary.** §C.1–§C.6 below analyze rows 001–016 as the file stood on
2026-08-27. Their sixteen-row denominators are preserved rather than silently restated as current.
§C.7 adds the three S110 rows and names only the conclusions re-derived over all 19.

### 1. Ten of the sixteen are one failure in ten costumes

`Observed` — counted from §B, not recalled. **001, 002, 003, 004, 005, 006, 010, 011, 014, 015**
are the same move: *a stand-in for a measurement was quoted as the measurement.* Only the
stand-in changes.

| row | the proxy that was quoted | the thing it stood in for |
|---|---|---|
| 001 | a subagent's `Verified` | running the probe |
| 002 | the raw file | the body index the producer actually uses |
| 003 | memory of the registers | a grep of the registers |
| 004 | my own regex | the rows |
| 005 | the harness token counter | the context window |
| 006 | a print truncated at 2600 chars | the file |
| 010 | a delegated list of 13 | thirteen probes |
| 011 | a census subagent's **residue** section | `ls -1 sessions/` |
| 014 | **my probe's predicate** | the predicate the production resolver actually applies |
| 015 | `~/ml/vault` | `$VAULT_DIR` as `open.sh` resolves it |

**014 is this row-family's extreme, and it is a different kind of extreme.** Every other proxy
above is a *thing* standing in for another thing — a file, a path, a counter, a list. 014's proxy
is a **question**: the number was a real measurement of a predicate nobody was asking about,
reported as an answer to the predicate everyone was. §C.6.

Two more (**007**, **008**) present as harness mechanics but land in the same place: silence read
as calm, and a backup assumed to exist because the command that would have written it ran.
`Inferred` — the proximate cause in both is shell semantics, so they are classed HARNESS-MISUSE,
but the escape route is identical. **016** is the same shape pointed the other way — I *was* the
stale proxy the peer was reading, for 89 minutes, and I then ran two work units on my own
unrefreshed picture of the bus. **012** is the one genuinely different epistemic failure among
these: not a proxy quoted as a measurement, but two real measurements of different populations
laid side by side with neither population named.

**009 and 013 are the only purely mechanical rows — and they are the same defect, filed twice.**
`Observed`: 013's cell states it reproduced 009 exactly. Four rows apart, hours apart, one file
apart. See §C.5.

### 2. Three of the sixteen were caught by method

`Inferred` from the "how it was caught" column of §B. **The numerator finally moved** — 015 is the
first row in this file caught by a deliberate method *before it escaped*. It is also the only one:

| catch mode | rows | n |
|---|---|---|
| A method chosen **because the claim mattered** — a differently-shaped count; a re-probe before striking; **resolving a path the way its consumer resolves it** | 004, 010, **015** | **3** |
| The machine failing **loudly** — traceback, `No such file`, a completion notice at ~2 s | 007, 008, 009, 013 | 4 |
| An **unrelated read** of `bench.py` / the resolver's source | 001, 002, 003 | 3 |
| **A delegated agent refusing the premise** and reporting the deviation | 011, 012 | 2 |
| **Rab** — a screenshot; an instruction | 005, 016 | 2 |
| **THE OTHER VENDOR**, by clean-room falsification | **014** | 1 |
| Continuing the probe after the alarm had already been sounded | 006 | 1 |

`Inferred`, and load-bearing: **001, 002 and 003 all name the same source read.** The input does
not state they were one act (`Unknown`), but three of the sixteen were caught in the neighbourhood
of one read that happened for a different reason. That is luck with a good alibi.

`Observed` — **13 of the 16 were caught by something other than a method of mine**: 4 by the
machine crashing, 3 by an unrelated read, 2 by a delegated agent refusing its GROUND, 2 by Rab,
1 by the other vendor, 1 by letting a probe finish. **Five of those thirteen required another
mind** — 005 and 016 (Rab), 011 and 012 (agents), 014 (Codex).

### 3. The catches anti-correlate with the damage

`Observed` — **eight** rows record the claim reaching a human, another vendor, a fleet, or a
tracked register **before** it was checked: **001** (Rab *and* the Codex bus), **005** (Rab),
**006** (Rab, plus a correction drafted on the false premise), **010** (Rab), **011** (**seven
agents**, as their GROUND), **012** (Rab *and* written into `OPEN-TASKS.md` §0, where it
persists), **014** (**Rab *and* the Codex bus *and* `SYMPTOM-INDEX.md` SYM-025**), **016** (the
bus, by omission — 89 minutes of a peer reading a stale picture of me). Of those eight, exactly
one (010) was caught by a method of mine, and only after it had already been reported.

`Observed`, and it is the trajectory that matters: **001's wrong claim reached two audiences;
011's reached seven; 014's reached two audiences and the permanent record.** Each happened *after*
the previous one was filed, with the rule already written down. The blast radius did not shrink as
the register grew.

**015 is the counter-example, and it is worth naming precisely.** It is the only row where the
error was stopped **before** it reached anything — one line short of writing "0 vaulted books"
into the page that ranks all project value. `Inferred`: what stopped it was reconciling two
disagreeing readings instead of picking the later one. That is a method, it worked, and it is
1 row out of 16.

`Inferred`, and the reason to keep this file: **the four that crashed cost minutes and reached
nobody.** The eight that escaped ran silently to completion — no traceback, no non-zero exit,
plausible numbers. A failure that announces itself is not the class this bin exists for. Every
row here that mattered was quiet, and **014 was the quietest of all: it was self-consistent.**

### 4. Delegation causes four of the sixteen — and other minds catch more than my method does

`Observed` — **001, 002 (its verdict), 010, 011** all originate in work done by a subagent or a
census and then carried forward without an independent probe. 011 is the deepest of them: the
inherited claim was not a subagent's *finding* but a subagent's **residue**, the section of a
report explicitly reserved for what it could not establish.

`Observed` — and in the same file, **other minds caught 5 of the 16** (011, 012 by agents; 005, 016
by Rab; 014 by the other vendor) against **3** for every deliberate method of my own (004, 010,
015). `Inferred`: this is the property `docs/47` (the subagent orchestration law) governs from the
*commissioning* side, now visible from both ends at once — **the law's "deviation is the report"
clause is doing more verification work in this file than my own probes are.** The law says what to
give an agent; nothing in it says what to do with what an agent returns, and every one of these
four rows is a failure on the return leg.

### 5. Are this file's rules propagating, or only being restated?

**Only being restated.** `Observed`, on the two rows that test it directly:

- **013 is a rule from this file failing during the writing of this file.** ERR-009's rule —
  *backslashes and nested quotes go in a FILE, never a heredoc* — was already written, already in
  the register, and physically on screen. The very next command that needed it was a heredoc'd
  regex, and it died on the same construct. The rule did not fire. **The traceback did.**
- **011 is 001 one level up.** 001 was a subagent's `Verified` carried to Rab and the Codex bus
  with my authority attached. 011 is a subagent's **residue** — the least-established part of a
  report — carried to *seven agents* as their GROUND, with my authority attached. Same class,
  same move, one layer higher in the stack, and **001 was already filed when it happened.**
- **016 is 011 again, filed the same day, pointed at the bus.** Its own rule cell says so
  outright. A stale GROUND handed to a fleet became a stale beat handed to a peer: 89 minutes,
  on a bus that heartbeats every 30 seconds, while I completed two work units and never checked
  for the reply to a conflict I had posted. **Third recurrence of a class after it was written
  down**, and caught by Rab.

So the honest reading, `Inferred` but hard to escape: **writing a rule into this register changed
nothing about the behaviour it names, inside the same session, on the same day.** All three
recurrences were caught by something outside me — a traceback, a fleet refusing its own GROUND,
and Rab. `Observed`: **no row in §B names this file as how it was caught. Zero of sixteen.**

**One qualification, and it cuts the other way.** 015 shows the *method* half working: two
disagreeing readings were reconciled instead of resolved by recency, and a wrong number was
stopped one line before it entered `wiki/roadmap.md`. `Observed` from its own cell — the catch is
attributed to reading `open.sh` and to the muster card, **not to this file.** The register still
has zero catches to its name; what improved was the habit, not the register's reach.

What *is* propagating is the thing with teeth: `docs/47`'s "deviation is the report" clause, signed
before this file existed, is what caught 011 and 012. A register that is written at the end of a
task is a record. It becomes a rule only when something forces it to be **read at the start of
one** — which is precisely what row 013's own rule says, filed by the run that proved it.

**This section is the file arguing against its own sufficiency.** Leave it in.

### 6. ERR-014 — the row that says self-checking has a floor

*This section exists because 014 is the only row in the file that no amount of my own discipline
would have caught. Everything above it is a discipline problem. This one is not.*

**What happened, `Observed` from the row.** I measured *"21 of 23 stored pointers fail to resolve
on their own excerpt"*, tagged it `Verified`, and pushed it to **three** places at once: Rab, the
Codex bus, and `SYMPTOM-INDEX.md` SYM-025 as a corpus-wide upgrade to a row filed at S76. It was
falsified by the other vendor (`MSG-CDX-0017`) with two independent probes, one of them a
**clean-room probe denied the relay, the registers, prior reports, memory and the expected
counts**.

**The mechanism.** One number was summing three different tests:

| predicate | result |
|---|---|
| exact physical BODY line at the stored coordinate | 18/23 miss |
| producer-faithful paragraph start | 17/23 miss |
| **what the Bench resolver actually does** | **21/23 `anchor=excerpt`** |

**The 21 I reported as failures is the count of production successes.** The claim was numerically
identical to its own inverse — which is why it survived every internal check: inverting it changes
nothing that any consistency test I ran could see.

**Its negative control was dead too, and that is the part with teeth.** The seeding pass of
SYM-025 leaned on `c5afd9ed` as the control. `c5afd9ed` #2 is **producer-faithfully correct** at
body line 2400; its eight-token excerpt merely **spans lines 2400–2401**, so a one-line check
reports drift at **zero line delta** — a schema/resolver mismatch, not a stale pointer. And
`b7b711d4` #1 is a **distinct defect class** the single number had silently merged in. `Inferred`:
a negative control that shares the collapsed predicate is not a control. This is `SYM-001`'s law
one level up — *two checks that share an assumption are one check* — where the shared assumption
is not a stub but **the question being asked**.

**Why this row outranks the other fifteen.** `Inferred`, and it is the point of the section:
every other row in this file implies a rule I could follow harder. 014 implies a rule I **cannot**
follow, because the failure is invisible from inside the frame that produced it. §C.2 has been
scoring "caught by method" as if that number could be driven to 16. **014 proves it cannot** —
there exists a class where the only detector is a prober with different priors, structurally
denied my inputs. `docs/47`'s **verifier anti-correlation** clause is listed `Intended` — signed,
untested, "a proxy with a birth certificate until it has a case that VIOLATES its property"
(`OPEN-TASKS.md` J12, `Observed 2026-08-25`). `Inferred`: **014 is that case**, and the clean-room
probe that caught it is the clause working.

**The one heuristic 014 leaves behind that is usable from inside**, quoted from its own rule:
*a number that looks plausible in both directions is evidence of collapse, not of correctness.*
That is not a proof, it is a smell — but it is the only inside-the-frame detector this class has.

**The standing consequence.** Every count in this repo — including every count in this file — is a
claim about a population **and** about a test. `Observed`: none of the count tables in §C names its
predicate. That is a live instance of this class in the very document that describes it, and it is
recorded here rather than quietly fixed.

### 7. Current 19-row reading after ERR-017–019

`Observed 2026-08-28` from §B's class and catch columns: **12 of 19** rows now share §C.1's
proxy-substitution shape — the prior ten plus 018 (typed “clean” stood in for derived status) and
019 (launch history stood in for current liveness). The deliberate-method numerator remains
**3 of 19**. The catches now include **2 by the other vendor** (014, 017), **3 by Rab** (005,
016, 019), and Fable's adjacent-output self-catch of 018. **Seven of nineteen required another
mind**: Rab 3, delegated agents 2, other vendor 2.

`Observed`: **11 of 19** claims reached a human, peer, fleet, register, or close record before the
contradiction was checked — the prior eight plus 017, 018 and 019. `ERROR-BIN.md` itself still
appears in **zero of nineteen** “How it was caught” cells. Filing the three rows therefore changes
the denominator, not the register's demonstrated prevention rate.

---

## §D HOW THIS FILE STAYS TRUE

*This protocol is the digest's proposal. It is **not signed by Rab** — he instructed the bin's
existence, not these rules. `Inferred` throughout.*

**The append rule.** Notice an error → write the line → append the row in the same session,
before close. **Never edit a row to soften it.** A correction is an appended, dated clause inside
the cell (the `SYMPTOM-INDEX.md` habit) or a new row that cites the old one. Fixed classes stay:
the recurrence is what is being guarded against, and a class cannot be "fixed", only re-armed.

**The ID scheme.** `ERR-YYYY-MM-DD-NNN` — date the error was made (not filed), `NNN` zero-padded,
sequential within that date, **never reused and never renumbered.** ERR-004 in this very file is
what renumbering costs: SYM-037/038/039's renumbering annotation is precisely what the counting
regex tripped on.

**The honest caveat, which is structural and not fixable by discipline.** A self-reported error
log contains only the errors its author **noticed**. It is a biased sample by construction, and
§C.2 measures the bias directly: of these 16, **4** are here because the machine crashed, **3**
because of an unrelated read, **2** because a delegated agent refused the premise, **2** because
Rab said something, **1** because the other vendor falsified it, **1** because a probe was allowed
to finish — and **3** because I chose a method. **The errors that were quiet AND that nothing
happened to bump into are not in this file, and there is no reason to believe the noticed set
resembles the whole.** The file's own §C.3 finding — that the quiet ones are the expensive ones —
implies the unsampled remainder is worse than the sample, not better.

`Observed`, across both appends: rows 011–013 did not move the method count at all; rows 014–016
moved it by exactly one (015). **Thirteen of sixteen entered through a channel outside my own
intent** — and §C.6 establishes that for at least one class, no channel inside my intent exists.

**What would make it less biased** (proposals, unsigned, `Inferred`):

1. **An adversarial lane that files rows against a session's transcript, not against its
   self-report.** The author is the worst-placed observer of the errors the author did not see.
   **Upgraded 2026-08-27 from a proposal to a demonstrated necessity by row 014**, which no
   self-check could have caught — and 014 also gives the design, because the probe that worked was
   **clean-room**: *denied the relay, the registers, prior reports, memory, and the expected
   counts.* `Inferred`: withholding the expected count is the load-bearing denial. A verifier told
   what number to expect is a verifier that will find it.
2. **A mechanical harvest** — grep session transcripts for self-corrections ("actually", "I was
   wrong", "correction:") and file each hit as a candidate row. Turns a memory task into a probe.
3. **File on ESCAPE, not on wrongness.** Every claim that reached Rab or the bus before it was
   independently checked gets a row, *even if it later proved correct.* §C.3 says the escape is
   the event; the wrongness is only what makes it visible.
4. **A close-time gate in `close.sh`'s `[8]` shape** — did this session file an ERR row, and if
   not, does its closeout **say so**? Warn-only first, per `OPEN-TASKS.md` §I's precedent, and a
   count that never rises should be as visible as a count that never falls.
5. **Never quote a class from this file as absolution.** Having a class named here does not mean
   the class is guarded. Nothing in this file has teeth; it is a mirror, not a gate.
6. **Read it at the START of a task, not only at the end** — row 013's rule, appended
   2026-08-27 because ERR-009 recurred during this file's own verification run, hours after being
   filed. A register consulted only at close is a record of what was already lost. `Inferred`, and
   the cheapest test of whether that ever changes: **the day a §B row can name ERROR-BIN.md in its
   "how it was caught" column is the day this file starts being a rule instead of a diary.**

   **STATUS 2026-08-27, re-measured after rows 014–016: still zero. Zero of sixteen.** `Observed`
   — no cell in §B's "how it was caught" column names this file.

   **What that number now means has changed, because the file was wired into the open this
   session.** `Observed 2026-08-27` **by my own probe, not on report**:
   `.claude/skills/muster/open.sh` `[2b]` carries an `error-bin` register row that prints
   `$(grep -cU '^\| ERR-' …) row(s) — read the CLASS table before you probe`, with a comment citing
   this very §D.6 as its reason; `selftest.sh` **CASE 36** is its tripwire, and its **negative
   control deletes the file and asserts it reads `UNREAD` rather than silence.** (Note the counter
   uses `grep -cU` — ERR-004's own remedy, applied to counting this file.)

   `Inferred`, and this is the whole point of keeping the number: **before the wiring, zero meant
   "nobody reads it." After the wiring, zero means "it is read at every open and has still never
   caught anything."** Those are different findings, and only the second one is falsifiable. The
   count is now a live experiment on whether a register that is *forced in front of you* changes
   behaviour — which is the same question `OPEN-TASKS.md` §I asked at S109 and has not yet
   answered either. **Do not let this number be quietly retired if it stays at zero; a zero that
   persists after the wiring is the more interesting result.**
