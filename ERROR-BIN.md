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

| tag | meaning |
|---|---|
| `Observed` | a command was run or a row was counted; the result is quoted |
| `Inferred` | a reading of the evidence in this file, not a measurement |
| `Unknown` | named because it is not known, and should not be guessed |

---

## §A THE CLASSES — the actual product

*Derived from the ten rows below (`Observed` — every class name and every rule text comes from
the input lines; the "from the inside" column is the digest's characterisation, `Inferred`).*

| Class | What it looks like from the inside | The rule that prevents it | Rows |
|---|---|---|---|
| **DELEGATED-TRUST** | You hold a verdict you did not produce. It arrives wearing a confidence word — `Verified`, `confirmed`, `done` — so it reads like a measurement. Nothing about it feels like a quotation | A consequential act (a message to Rab, a post to the bus, a struck register line) needs an `Observed` premise of **your own**. A subagent's `Verified` is `Reported`, not `Observed` | 001 |
| **PROBE-SHAPE** | The probe runs. It returns numbers. Nothing errors. The numbers are real — they simply answer a different question, because your model of the artifact is not the consumer's model of it | Before measuring against a file, read how the **producer** indexes it. Any count that enters a claim gets a second method of a **different shape** first | 002, 004 |
| **REGISTER-MISS** | The finding feels new. Nothing in memory contradicts it, and the absence of a contradiction reads as the absence of a record | "Unfiled" / "in no register" / "nobody has noticed" is a claim about a **file** and requires a grep of that file. A defect rediscovered is a MUSTER failure (`docs/21` §5 rule 4) | 003 |
| **METER-CONFUSION** | A number is on the panel, it has plausible units, and it is the only number in view. You report it. It measures the neighbour of what was asked | When reporting a number the user asked for, confirm the meter measures **the thing they named** | 005 |
| **PREMATURE-ALARM** | The evidence is not where you looked, so you conclude it does not exist — and you say so before the probe has finished running | Finish the probe before narrating its verdict. A truncated read is **UNREAD**, not absent | 006 |
| **HARNESS-MISUSE** | The command returns 0. The tooling reports success. The work never happened, or happened somewhere else, and the silence afterwards reads as calm | A backgrounded command must be the whole job, not a launcher for another background job. Never restore from a path whose write you did not confirm — verify the backup exists before destroying the original | 007, 008 |
| **QUOTING** | A script dies on its own delimiters: backslashes, nested quotes, a trailing `\'`, a regex mangled in transit. Cheap when it crashes; expensive when it half-writes | Anything containing backslashes or nested quotes goes in a FILE via `Write`, never a heredoc | 009, 013 |
| **OVER-CLAIM** | A list of candidates is reported as a list of findings. Most of it is right, which is what makes the rest of it dangerous | A delegated list is a list of **candidates**; every item that will produce a recorded change gets its own probe | 010 |
| **STALE-GROUND** *(added 2026-08-27, row 011)* | You are writing the GROUND block for a fleet. The framing numbers came from an earlier report and feel like settled background rather than claims, so they get stated instead of probed — and then every downstream agent inherits them as given | GROUND is a claim like any other and gets a probe **before** it is handed to anyone. A **residue** section is the least-verified part of a report, not the most | 011 |
| **DENOMINATOR** *(added 2026-08-27, row 012)* | Two totals appear in one session. Both were honestly obtained; neither is wrong. Nothing states what either one counts, so the reader has no choice but to assume they are comparable | `docs/34`: every measured number names its **numerator, denominator and conditions**. Two totals of different populations must never appear in one session without their populations stated | 012 |

**10 classes, 13 rows.**

---

## §B THE ROWS

*All thirteen `Observed 2026-08-27` by the session that made them — self-reported, not re-verified
by this digest. Surfaces and file citations are the reporting session's. Row 013 is the one
exception to "self-reported by the session": it was observed by the digest run and filed by the
session, which says so in the cell.*

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

---

## §C WHAT THESE HAVE IN COMMON

### 1. Eight of the thirteen are one failure in eight costumes

`Observed` — counted from §B, not recalled. **001, 002, 003, 004, 005, 006, 010, 011** are the
same move: *a stand-in for a measurement was quoted as the measurement.* Only the stand-in
changes.

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

Two more (**007**, **008**) present as harness mechanics but land in the same place: silence read
as calm, and a backup assumed to exist because the command that would have written it ran.
`Inferred` — the proximate cause in both is shell semantics, so they are classed HARNESS-MISUSE,
but the escape route is identical. **012** is the one genuinely different epistemic failure in
the file: not a proxy quoted as a measurement, but two real measurements of different populations
laid side by side with neither population named.

**009 and 013 are the only purely mechanical rows — and they are the same defect, filed twice.**
`Observed`: 013's cell states it reproduced 009 exactly. Four rows apart, hours apart, one file
apart. See §C.5.

### 2. Two of the thirteen were caught by method

`Inferred` from the "how it was caught" column of §B. **The numerator did not move when three
rows were added** — 011 and 012 introduced a new catch mode rather than joining the old one:

| catch mode | rows | n |
|---|---|---|
| A method chosen **because the claim mattered** — a second differently-shaped count; a re-probe before striking | 004, 010 | **2** |
| The machine failing **loudly** — traceback, `No such file`, a completion notice at ~2 s | 007, 008, 009, 013 | 4 |
| An **unrelated read** of `bench.py` / the resolver's source | 001, 002, 003 | 3 |
| **A delegated agent refusing the premise** and reporting the deviation | 011, 012 | 2 |
| **Rab**, with a screenshot | 005 | 1 |
| Continuing the probe after the alarm had already been sounded | 006 | 1 |

`Inferred`, and load-bearing: **001, 002 and 003 all name the same source read.** The input does
not state they were one act (`Unknown`), but three of the thirteen — including the single most
consequential row in the file — were caught in the neighbourhood of one read that happened for a
different reason. That is luck with a good alibi.

### 3. The catches anti-correlate with the damage

`Observed` — **six** rows record the claim reaching a human, another vendor, a fleet, or a tracked
register **before** it was checked: **001** (Rab *and* the Codex bus), **005** (Rab), **006** (Rab,
plus a correction drafted on the false premise), **010** (Rab), **011** (**seven agents**, as their
GROUND), **012** (Rab *and* written into `OPEN-TASKS.md` §0, where it persists). Of those six,
exactly one (010) was caught by a method of mine, and only after it had already been reported.

`Observed`, and it is the trajectory that matters: **001's wrong claim reached two audiences;
011's reached seven** — and 011 happened *after* 001 was filed, with the same rule already written
down. The blast radius grew by 3.5× while the rule sat in the register.

`Inferred`, and the reason to keep this file: **the four that crashed cost minutes and reached
nobody.** The six that escaped ran silently to completion — no traceback, no non-zero exit,
plausible numbers. A failure that announces itself is not the class this bin exists for. Every
row here that mattered was quiet.

### 4. Delegation causes four of the thirteen — and now catches as many as method does

`Observed` — **001, 002 (its verdict), 010, 011** all originate in work done by a subagent or a
census and then carried forward without an independent probe. 011 is the deepest of them: the
inherited claim was not a subagent's *finding* but a subagent's **residue**, the section of a
report explicitly reserved for what it could not establish.

`Observed` — and in the same file, **delegated agents caught 2 of the 13** (011, 012), which is
exactly as many as every deliberate method of my own caught (004, 010). `Inferred`: this is the
property `docs/47` (the subagent orchestration law) governs from the *commissioning* side, now
visible from both ends at once — **the law's "deviation is the report" clause is doing more
verification work in this file than my own probes are.** The law says what to give an agent;
nothing in it says what to do with what an agent returns, and every one of these four rows is a
failure on the return leg.

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

So the honest reading, `Inferred` but hard to escape: **writing a rule into this register changed
nothing about the behaviour it names, inside the same session, on the same day.** Both recurrences
were caught by something outside me — a traceback, and a fleet refusing its own GROUND. `Observed`:
**no row in §B names this file as how it was caught. Zero of thirteen.**

What *is* propagating is the thing with teeth: `docs/47`'s "deviation is the report" clause, signed
before this file existed, is what caught 011 and 012. A register that is written at the end of a
task is a record. It becomes a rule only when something forces it to be **read at the start of
one** — which is precisely what row 013's own rule says, filed by the run that proved it.

**This section is the file arguing against its own sufficiency.** Leave it in.

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
§C.2 measures the bias directly: of these 13, **4** are here because the machine crashed, **3**
because of an unrelated read, **2** because a delegated agent refused the premise, **1** because
Rab looked at a screenshot, **1** because a probe was allowed to finish — and **2** because I
chose a method. **The errors that were quiet AND that nothing happened to bump into are not in
this file, and there is no reason to believe the noticed set resembles the whole.** The file's own
§C.3 finding — that the quiet ones are the expensive ones — implies the unsampled remainder is
worse than the sample, not better.

`Observed`, from the append of rows 011–013: **adding three rows did not move the method count.**
It stayed at 2. Every added row entered through a channel outside my own intent.

**What would make it less biased** (proposals, unsigned, `Inferred`):

1. **An adversarial lane that files rows against a session's transcript, not against its
   self-report.** The author is the worst-placed observer of the errors the author did not see.
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
   Today that column names it zero times out of thirteen.
