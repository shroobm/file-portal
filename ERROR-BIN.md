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
| **QUOTING** | A script dies on its own delimiters: backslashes, nested quotes, a trailing `\'`, a regex mangled in transit. Cheap when it crashes; expensive when it half-writes | Anything containing backslashes or nested quotes goes in a FILE via `Write`, never a heredoc | 009 |
| **OVER-CLAIM** | A list of candidates is reported as a list of findings. Most of it is right, which is what makes the rest of it dangerous | A delegated list is a list of **candidates**; every item that will produce a recorded change gets its own probe | 010 |

**8 classes, 10 rows.**

---

## §B THE ROWS

*All ten `Observed 2026-08-27` by the session that made them — self-reported, not re-verified by
this digest. Surfaces and file citations are the reporting session's.*

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

---

## §C WHAT THESE HAVE IN COMMON

### 1. Seven of the ten are one failure in eight costumes

`Observed` — counted from §B, not recalled. **001, 002, 003, 004, 005, 006, 010** are the same
move: *a stand-in for a measurement was quoted as the measurement.* Only the stand-in changes.

| row | the proxy that was quoted | the thing it stood in for |
|---|---|---|
| 001 | a subagent's `Verified` | running the probe |
| 002 | the raw file | the body index the producer actually uses |
| 003 | memory of the registers | a grep of the registers |
| 004 | my own regex | the rows |
| 005 | the harness token counter | the context window |
| 006 | a print truncated at 2600 chars | the file |
| 010 | a delegated list of 13 | thirteen probes |

Two more (**007**, **008**) present as harness mechanics but land in the same place: silence read
as calm, and a backup assumed to exist because the command that would have written it ran.
`Inferred` — the proximate cause in both is shell semantics, so they are classed HARNESS-MISUSE,
but the escape route is identical. **009 is the only purely mechanical row in the file.**

### 2. Two of the ten were caught by method

`Inferred` from the "how it was caught" column of §B:

| catch mode | rows | n |
|---|---|---|
| A method chosen **because the claim mattered** — a second differently-shaped count; a re-probe before striking | 004, 010 | **2** |
| The machine failing **loudly** — traceback, `No such file`, a completion notice at ~2 s | 007, 008, 009 | 3 |
| An **unrelated read** of `bench.py` / the resolver's source | 001, 002, 003 | 3 |
| **Rab**, with a screenshot | 005 | 1 |
| Continuing the probe after the alarm had already been sounded | 006 | 1 |

`Inferred`, and load-bearing: **001, 002 and 003 all name the same source read.** The input does
not state they were one act (`Unknown`), but three of the ten — including the single most
consequential row in the file — were caught in the neighbourhood of one read that happened for a
different reason. That is luck with a good alibi.

### 3. The catches anti-correlate with the damage

`Observed` — four rows record the claim reaching a human or another vendor **before** it was
checked: **001** (Rab *and* the Codex bus), **005** (Rab), **006** (Rab, plus a correction drafted
on the false premise), **010** (Rab). Of those four, exactly one (010) was caught by a method of
mine, and only after it had already been reported.

`Inferred`, and the reason to keep this file: **the three that crashed cost minutes and reached
nobody.** The four that escaped ran silently to completion — no traceback, no non-zero exit,
plausible numbers. A failure that announces itself is not the class this bin exists for. Every
row here that mattered was quiet.

### 4. Three of the ten sit on a delegation boundary

`Observed` — **001, 002 (its verdict), 010** all originate in work done by a subagent or a
census and then carried forward without an independent probe. `Inferred`: this is the same
property `docs/47` (the subagent orchestration law) governs from the *commissioning* side; these
rows are its failure mode on the *receiving* side. **The law says what to give an agent; nothing
here says what to do with what it returns.**

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
§C.2 measures the bias directly: 3 of these 10 are here because the machine crashed, 1 because
Rab looked at a screenshot, and 3 because of an unrelated read. **The errors that were quiet AND
that nothing happened to bump into are not in this file, and there is no reason to believe the
noticed set resembles the whole.** The file's own §C.3 finding — that the quiet ones are the
expensive ones — implies the unsampled remainder is worse than the sample, not better.

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
