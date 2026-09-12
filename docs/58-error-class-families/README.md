# docs/58 — The error class families

⟨claimed: Fable · S123 · 2026-09-10⟩ · mechanical half: `observability/error_families.py` (`--census`, `--place`, `--selftest`) · Rab's order, 2026-09-10T02:3xZ: *"Start describing error class families, and putting them into our project folder, so then we can derive error patterns faster, and group them accordingly."* — *"on all errors."*

## §0 What a family is, and why there are two tiers

The project keeps two registers of failure and they describe two different objects:

- **`ERROR-BIN.md`** (67 rows, 24 classes) records **method errors** — how a *claim* came to outrun its probe. The object is the agent's act; the remedy is a rule.
- **`SYMPTOM-INDEX.md`** (82 rows) records **mechanisms** — how the *system* broke. The object is code, a tool, a platform; the remedy is a fix with a tripwire.

A **family** is a set of classes (or rows) that share one mechanism, so that a new failure can be placed by its **shape** before its story is known. Every family below carries Rab's three parts (the error structure, S78): the **reason** (the mechanism), the **highlight** (the surface — what you see, and where to look), and the **solution** (the remedy pattern), plus the one **discriminating probe** that separates it from its nearest neighbour. A family's members are cited by id so the grouping can be refuted row by row; the tool refuses a new class or row that is not placed, so grouping happens at filing time, not in hindsight.

How the families were derived: three read-only Sonnet lanes read every row of both registers and the §8/§10 findings of the nineteen Desktop closeouts S104–S122 (each lane caught its planted decoy), returned one mechanism line per row and proposed groupings with evidence; the families here are Fable's synthesis over those rows and the class table read by its own hand. Each row's placement is a claim; the register row is the evidence. Counts are the census's printed lines at S123 (`Observed`), never a remembered number.

## §1 METHOD families — nine, covering all 24 classes and all 67 rows

| # | family | classes | rows |
|---|---|---|---|
| M1 | CLAIM-BEFORE-PROBE | DELEGATED-TRUST · OVER-CLAIM · PREMATURE-ALARM · STATUS-THEATRE · PHANTOM-MONITOR · REGISTER-MISS | 8 |
| M2 | WRONG-OBJECT-MEASURED | PROBE-SHAPE · METER-CONFUSION | 15 |
| M3 | NUMBER-WITHOUT-ITS-QUESTION | DENOMINATOR · PREDICATE-COLLAPSE | 5 |
| M4 | PREMISE-AGED-BETWEEN-READ-AND-USE | STALE-GROUND · STALE-SNAPSHOT · PARTIAL-PUBLISH | 7 |
| M5 | ORDER-ASSUMED-NOT-PROVEN | ORDERING · BOUNDARY-OMISSION | 9 |
| M6 | GUARD-NARROWER-THAN-THE-CLAIM | LOCK-SCOPE · DEAD-SURFACE · PROVENANCE-DROP · NAMESPACE-SCOPE | 4 |
| M7 | THE-LAYER-BELOW-ATE-THE-COMMAND | HARNESS-MISUSE · QUOTING | 15 |
| M8 | AN-INERT-ACT-REACHED-A-WIDER-SCOPE | RUNTIME-RESIDUE · CONTROL-LEAK | 3 |
| M9 | CONTEXT-BECAME-THE-REQUEST | DELEGATION-SHAPE | 1 |

Two families hold 30 of the 67 rows: **M2** (the probe measured the neighbour) and **M7** (the layer below ate the command). Those two are where the next error is most likely, and both have a cheap probe.

### M1 · CLAIM-BEFORE-PROBE
- **Reason.** A confidence word — `Verified`, `done`, `clean`, `running`, "unfiled", "does not exist" — is asserted from a delegated report, a launch-time memory, a truncated read or a literal label, not from a same-turn measurement of the exact predicate. The claim outran its probe.
- **Highlight.** The word sits beside, or ahead of, the evidence; nothing printed in the same turn carries that exact word with a failure branch. ERR-001 relayed a subagent's `Verified`; 006 called data absent from a print truncated at 2,600 chars; 019 called a one-shot a monitor; 048 told Rab a file did not exist from two differently failed probes; 064 quoted "5 of 166" from memory when the run said 4.
- **Probe.** *Which same-turn printed line, with a failure branch, does this word rest on?* If the answer is a report, a memory or a label, it is this family.
- **Solution.** Your own `Observed` premise before any consequential word; a delegated `Verified` is `Reported` until re-probed; quote the printed line, never the summary; a truncated read is `UNREAD`, not absent.
- **Members.** ERR-001, 003, 006, 010, 018, 019, 031, 048, 064.

### M2 · WRONG-OBJECT-MEASURED
- **Reason.** The probe ran, returned a number, and is internally consistent — but it measured the neighbour: the raw file instead of the indexed body (002), the session budget instead of the context window (005), a convenience accessor with its own bug (049), a `grep` that strips the byte it counts (051), a post-override API field instead of the log (059), a fixture whose stamp the parser rejects (065).
- **Highlight.** One plausible number, the only reading in view; a second, differently shaped read of the same object gives a different answer.
- **Probe.** *A second measurement of a different shape on the same object — do the two agree?* Disagreement is a finding, never a tie broken by the later run.
- **Solution.** Read how the producer indexes the thing before measuring it; any result entering a claim gets a second method of a different shape; a number is re-measured, never quoted.
- **Members.** ERR-002, 004, 005, 015, 028, 038, 049, 050, 051, 057, 058, 059, 065, 066 — and PROBE-SHAPE is the most frequent class in the bin (13 rows).

### M3 · NUMBER-WITHOUT-ITS-QUESTION
- **Reason.** A count is quoted without its population (147 items across five surfaces vs 104 in one file, 012), a byte total without its delimiter rule (045), a per-chunk mean presented as a share of windows (061); or one number secretly sums two predicates over one population (014: the "21 misses" were 21 successes). Wrong by *question*, not by amount.
- **Highlight.** Two totals for "the same thing" in one session that both defend themselves; or a number that stays plausible when inverted — the only tell of a collapse.
- **Probe.** *Name the population and the single predicate; recompute; does the number move?* If a count could be two tests, it is two numbers.
- **Solution.** docs/34: numerator, denominator and conditions in the same sentence; occurrence, distinct-value and delimiter-inclusive counts are separate measurements.
- **Members.** ERR-012, 014, 041, 045, 061.

### M4 · PREMISE-AGED-BETWEEN-READ-AND-USE
- **Reason.** A value read or validated once — a GROUND number inherited from a residue section (011), a beat 89 minutes old on a 30-second bus (016), a record loaded then saved without re-reading (020), evidence edited between validation and append (027), an interpreter pin assumed to be the verifier's own (067) — is trusted at a later moment. Time of check is not time of use; a crash between two publications leaves a half (021, 032).
- **Highlight.** Framing numbers stated as background rather than probed; a heartbeat that goes stale across work units; an orphan that passed its earlier check.
- **Probe.** *Re-derive the value from its live source at the moment of use — does it match what was assumed?*
- **Solution.** GROUND is a claim and gets its probe before it is handed to anyone; revalidate at the write boundary (lock + compare-and-swap, a digest, a fresh `ls`); when verifying another lane, its environment is quoted from *its* notes.
- **Members.** ERR-011, 016, 020, 021, 027, 032, 067.

### M5 · ORDER-ASSUMED-NOT-PROVEN
- **Reason.** A sequence is inferred from membership rather than proven from boundary events: a beat written after the "clean" commit (017); four posts read as two rounds without receipt before send (024); receipts dated 2099 accepted for a 2026 terminal (036); a timeout that could never fire because an earlier interactive wait had no bound (039); an act performed before the record naming it (060, 063); the wrong SHA named after an amend (062).
- **Highlight.** "Recorded before acting", "two full rounds", "clean after commit" — contradicted by re-reading the actual boundary.
- **Probe.** *Name the two boundary events; read their real timestamps or commit order (`git show --stat` on both SHAs; receipt UTC vs terminal UTC).*
- **Solution.** State the boundary rule mechanically — every write first, commit last, then nothing; a round ends at receipt, not at send; the record commits before the first act; after an amend, re-read both commits before naming either.
- **Members.** ERR-017, 024, 034, 036, 039, 060, 062, 063 — and 022 (a terminal accepted equal readings; the boundary predicate absent).

### M6 · GUARD-NARROWER-THAN-THE-CLAIM
- **Reason.** The validator, lock or record covers most of the surface and misses the one property that defines correctness: a lock around the sidecar save but not the id allocation and the append (025); a lane address recorded, the occupant dropped on handoff (026); a durable field with no renderer (023); an allocator that scans one sidecar while the namespace spans two (035).
- **Highlight.** A high pass rate (108/108, 146/146) beside a defect that one differently scoped negative control exposes at once.
- **Probe.** *Enumerate every surface the claim touches (reads, effects, occupants, references); plant one violation outside the tested scope — does the guard fire?*
- **Solution.** Draw the transaction boundary around every shared premise and effect; every durable field ships with a named consumer; one namespace is defined by all of its allocation and reference surfaces.
- **Members.** ERR-023, 025, 026, 035.

### M7 · THE-LAYER-BELOW-ATE-THE-COMMAND
- **Reason.** The execution layer changed the command before the runtime saw it, and the empty or wrong result was read as evidence about the product: shell quoting and backslashes (009, 013, 029, 042, 053), backticks run as substitutions inside a committed README (054), a `cd` persisting into later relative probes (047, 052), a `||` that short-circuited a backup (008), a background launcher that exited at once (007), Git's dubious-ownership refusal read as "no evidence" (040, 043, 044), a stale test double (033), the wrong crate directory (046).
- **Highlight.** A script dies on its own delimiters, or a probe returns empty/wrong and it looks like a finding ("missing", "firing", "restored") until the same object reads fine through a different form.
- **Probe.** *Rerun the identical intent through a form immune to the suspected artefact — a file via `Write`, an absolute path, an explicit `safe.directory` — does the result change?*
- **Solution.** Anything with backslashes, nested quotes or backticks goes in a file; every path after a `cd` is absolute; every repo-identity-sensitive Git call carries its scope; a backgrounded command is the whole job.
- **Members.** ERR-007, 008, 009, 013, 029, 033, 040, 042, 043, 044, 046, 047, 052, 053, 054. Six of the fifteen are QUOTING's exact shape, two of them inside the sessions that filed the rule — the family the project pays for most often.

### M8 · AN-INERT-ACT-REACHED-A-WIDER-SCOPE
- **Reason.** A read-only or private act left residue or reached an audience: the first live lock file dirtied the tree (030); `uv run` built a venv and a lockfile out of a JSON read (055); a planted decoy was named in the closeout the fleet read as ground (056).
- **Highlight.** `git status` shows new residue after a "read"; a control meant to stay private appears in a document the subjects can read.
- **Probe.** *Diff the scope boundary — `git status`, the audience list — immediately before and after the inert step.*
- **Solution.** Classify every runtime path as tracked or ignored when it is introduced; keep a planted control in private scratch until the fleet that must not see it has returned.
- **Members.** ERR-030, 055, 056.

### M9 · CONTEXT-BECAME-THE-REQUEST
- **Reason.** Benign work was refused because the agent's name, inherited priming and adversarial verbs became part of the effective request (037).
- **Probe.** *Resend the same scoped, local, read-only task under a fresh neutrally named agent — does it succeed?*
- **Solution.** Agent identity and inherited context are prompt inputs; frame QA with its local artefact and no external target.
- **Members.** ERR-037.

## §2 MECHANISM families — sixteen, covering all 82 symptom rows, plus the closeout patterns without a row

| # | family | rows | status (from the rows' own cells) |
|---|---|---|---|
| S1 | BYTES-CHANGE-BETWEEN-LAYERS | 8 | 6 fixed · 1 open (SYM-082, Codex's) · 1 Historical |
| S2 | GREEN-WITHOUT-A-MEASUREMENT | 7 | 2 fixed · 4 open · 1 Historical |
| S3 | A-DEFAULT, CAP OR CUT WEARING A NUMBER | 6 | 4 fixed · 2 open |
| S4 | FAILED-PROBE-RENDERED-AS-NEGATIVE | 5 | 2 fixed · 3 open |
| S5 | A-GUARD-OFF-THE-PATH-THE-WORK-TAKES | 7 | 3 fixed · 4 open |
| S6 | THE-CHILD-OUTLIVES-THE-KILL | 6 | 6 fixed |
| S7 | PRODUCED-BUT-NEVER-PROJECTED | 9 | 2 fixed · 7 open |
| S8 | A-FACT-FROZEN-WHILE-THE-WORLD-MOVED | 7 | 6 fixed · 1 open |
| S9 | THE-WRONG-REFERENCE-OBJECT | 6 | 6 fixed |
| S10 | IDENTITY-FROM-THE-WRONG-EVIDENCE | 4 | 1 fixed · 3 open |
| S11 | UNBOUNDED-OR-UNGUARDED-EFFECT | 6 | 5 fixed · 1 open |
| S12 | PLATFORM-OR-LIBRARY-SEMANTICS-TRAP | 6 | 4 fixed · 1 open · 1 Historical |
| S13 | MODEL-OUTPUT-HAZARD | 2 | 1 fixed · 1 open |
| S14 | CONFOUNDED-COMPARISON | 1 | open |
| S15 | THE-INSTRUMENT-MANUFACTURES-THE-FINDING | 2 (+7 closeout findings) | 1 fixed · 1 open |
| S16 | GUARD-COARSER-THAN-THE-DEFECT | 0 (+4 closeout findings) | no row yet |

The status column is the first word of each row's own Status cell, measured at S123 (`family_status_check.py` over the register: 49 fixed · 30 open · 3 Historical of 82); the tool counts rows, not fixes. The first draft of this column was quoted from a reader's digest and was wrong in five families — caught by the re-measure before the file was committed, the M1 shape in the act of describing it.

### S1 · BYTES-CHANGE-BETWEEN-LAYERS
- **Reason.** The layer between you and the bytes rewrites them. `core.autocrlf=true` stores LF and checks out CRLF, so a blob is never a byte-prefix of its checkout and a manifest built from both sources disagrees with itself (029, 078, 079, 082 — four instances since S115, with `schemas.json` and `docs/contracts` pinned `-text` as the fixes); MSYS turns a leading-slash flag into a Windows path (031's `/FI`, 080's `/Create`); the harness collapses an escape level (036); a second toolchain keeps its own state (004's `known_hosts`, 017's PID column).
- **Highlight.** "Not a byte-prefix", "edited", a hash that disagrees with the checkout on a file nobody touched; a Windows tool erroring on a path-shaped argument from Git Bash and working from PowerShell.
- **Probe.** `git show HEAD:<f> | grep -cU $'\r'` against `grep -cU $'\r' <f>`; the identical command from PowerShell and from Git Bash.
- **Solution.** Compare line-ending-blind and build the reference in its own convention; pin `-text` for anything byte-exact; a manifest names which bytes it hashed; `/Flag` tools go through PowerShell or `MSYS_NO_PATHCONV=1`.
- **Members.** SYM-004, 017, 029, 036, 078, 079, 080, 082. Method twin: **M7**.

### S2 · GREEN-WITHOUT-A-MEASUREMENT
- **Reason.** A pass is derived from something other than the property: a stub that shares the code's own assumption (001), a digest suite that compares the tool's output to itself (055), an audit blind to structural validity (056), a detector whose exit code means nothing without `--enforce` (046), a `continue-on-error` step's post-override API field (075), the exit code of the wrong pipeline stage — `tail` after `pytest` (038), `grep -q` under `pipefail` killing its producer with SIGPIPE so a present string reads absent (077).
- **Highlight.** Green everywhere; a hostile mutation (swap the algorithm, fail the gated stage, read the job log) goes red at once.
- **Probe.** *Mutate what the check claims to verify — does it go RED?* A guard nobody has watched fire is a proxy with a reputation (docs/32 §5).
- **Solution.** Assert against an independently computed second method; an unmeasurable branch returns `UNREAD`, never a best case; read the log, not the badge; a gating command's status is read standalone, and presence checks use a count form.
- **Members.** SYM-001, 038, 046, 055, 056, 075, 077. Method twin: **M1**.

### S3 · A-DEFAULT, CAP OR CUT WEARING A NUMBER
- **Reason.** An unmeasured branch returns a value that looks measured: `1.0` survival on nothing to compare (057), a stored `[:25]` cap read as the population (066, 070), `getattr(marker, '__version__', 'unknown')` standing in for an identity (044), a key truncated by a paste and still accepted (005), a 400-character cut with no marker (052).
- **Highlight.** "open = 0" when the population exceeds the cap; a suspiciously round perfect score; a value with no visible cut.
- **Probe.** *Force the unmeasurable branch or exceed the cap — does the surface print UNREAD or the total, or a plausible number?*
- **Solution.** Carry `{shown, total, unseen}` through every consumer; never encode "not measured" as a real number; mark every cut.
- **Members.** SYM-005, 044, 052, 057, 066, 070. Method twin: **M3**.

### S4 · FAILED-PROBE-RENDERED-AS-NEGATIVE
- **Reason.** The probe errored, timed out or could not match, and the surface printed a definite negative: `tasklist` erroring to a discarded stderr read as "widget down" (031), every non-zero `git rev-parse` collapsed into "not a git repo" (063), a line-wise regex missing a re-wrapped phrase read as a stripped count (071), a detached invoke dying silently read as "nothing happened" (024, 034).
- **Highlight.** A confident absence — down, clean, gone, no drift — with no error trace anywhere, while the thing is present.
- **Probe.** *Make the probe fail on purpose (bad path, wrapped text, refused command) — does the surface say UNREAD?*
- **Solution.** A failed probe renders `UNREAD`, never a negative observation; check the call succeeded before counting anything from its output. This is the tag law's rule 4 in code.
- **Members.** SYM-024, 031, 034, 063, 071. **111** (S130: the events-mode tracker printed a failed post-event read as an empty command line and a dropped stop event as a live process). Method twin: **M1** (PREMATURE-ALARM).

### S5 · A-GUARD-OFF-THE-PATH-THE-WORK-TAKES
- **Reason.** The lock, detector, trigger or job object sits on one entry path and the work takes another: only the watcher writes `.gpu-lock`, a manual or `--resume` run never does (042); the job object governs only the watcher the widget spawned (047); CI triggered on master while work was pushed to a feature branch for 205 commits (018) and the ritual ran clippy but never fmt (020); zero-area connectors dropped before clustering (049); a fleet's servers outlive a harness that audits files, not processes (054); a lock nothing ever read (032).
- **Highlight.** A busy/covered/clean signal reads negative while the resource is in use, because the path in use never wrote the signal.
- **Probe.** *List every entry point that touches the guarded resource; one with zero writes to the signal is a live instance.*
- **Solution.** Put the guard where every path must pass — an OS-enforced mutex, a process census, the branch the work actually lands on — rather than adding one more path-specific writer.
- **Members.** SYM-018, 020, 032, 042, 047, 049, 054. **113** (S130 post-close: the ledger row's parser runs at the next OPEN, never at the close that writes the row). Method twin: **M6**.

### S6 · THE-CHILD-OUTLIVES-THE-KILL
- **Reason.** The kill or close is scoped to the direct child or one window; the real worker is a grandchild (a venv launcher's interpreter, 006, 068), the next command of a `;` chain (021), a second full factory from a second launch with no single-instance guard (033), a window whose teardown never reaches process exit (069); two survivors then share the card and fault the driver (022).
- **Highlight.** The UI says stopped; Task Manager shows the worker minutes later; no error anywhere.
- **Probe.** *Kill the intended parent, then census survivors by command line and parent pid.*
- **Solution.** Kill the whole tree (`taskkill /T /F`); wire every window's destroy to the app's teardown so the job object fires; never chain GPU work with `;`; a single-instance guard.
- **Members.** SYM-006, 021, 022, 033, 068, 069. Closeout kin: a supervisor that dies with its parent (S114 F6, S120 F6 → J52).

### S7 · PRODUCED-BUT-NEVER-PROJECTED
- **Reason.** A phase computes and stores a correct value and no renderer reads it (027's silent fields; 058, 060 — `assay.rs` exports `analyst`, `main.js` never reads it), or reads a different object, or shows it beside an unrelated verdict (059); a surface promises a live lever the code read once and baked in (041, 043, 061); the audit measures attribution and calls it survival (053); the bench reads one of two damage kinds (026).
- **Highlight.** The payload is perfect and the operator never sees it, or sees it next to a verdict it did not produce — Rab's "a glitch, not a bug".
- **Probe.** *Grep the producer for the key, then every renderer for a read of that key — writes without reads.*
- **Solution.** docs/29's disposition rule: every field a producer writes for operator evidence ships with a consumer and a contract test; label composites with the phase that measured them.
- **Members.** SYM-026, 027, 041, 043, 053, 058, 059, 060, 061 — the largest open family (7 of 9 open), all in the Room's status surfaces.

### S8 · A-FACT-FROZEN-WHILE-THE-WORLD-MOVED
- **Reason.** A number, SHA, date or topology assumption typed once and never regenerated: an orphaned closing SHA after an amend (016), prose counts that drift from the code (039), an unclamped bundle name (014), a dependency unpinned so CI resolved a newer minor (019), a destroy handler written in the one-window era that killed the watcher when a second window closed (023), a test asserting a frozen anchor equals live HEAD (065), a gate keyed on the filename's date (072).
- **Highlight.** A guard goes red immediately after its own passing commit, after a rewrap, after midnight, with the property unchanged; a doc contradicts a live command.
- **Probe.** *Re-derive the cited value from its live source — `rev-parse`, the suite, `importlib.metadata` — and diff; advance the dimension the guard reads while holding the property constant.*
- **Solution.** Cite the command that produces a number, never the number; compare against a live re-derivation, not a frozen anchor; `merge-base --is-ancestor`, not equality.
- **Members.** SYM-014, 016, 019, 023, 039, 065, 072. Method twin: **M4**.

### S9 · THE-WRONG-REFERENCE-OBJECT
- **Reason.** An index or comparison target is computed from the wrong object: a page offset added to an already absolute number (002, and its attribution twin 050); an assembly key on a stem the sanitiser rewrote (013); "newest row" taken as `tail -1` of an out-of-order table (028); zone line numbers from the convert-phase body after the analyst shortened it (025); the pre-analyst body audited against the post-analyst one (073).
- **Highlight.** Hundreds of pages "missing" or two runs of identical bytes scoring differently while the content, checked by eye, is present.
- **Probe.** *Trace one flagged item by hand to its reference object — does the formula double-apply, or do two texts get compared?*
- **Solution.** Repair the reference map before scoring, and record which reference every audit measured.
- **Members.** SYM-002, 013, 025, 028, 050, 073. **114** (S131: the near-exact reference was Marker's own body, loop included — the reference carried the disease). Method twin: **M2**.

### S10 · IDENTITY-FROM-THE-WRONG-EVIDENCE
- **Reason.** An identity or authority check reads a proxy an impostor would also carry: a launcher's pid compared to the actor's parent (081); a local counter for a namespace shared across machines or concurrent sessions (040, 045); a decision string's length standing in for a human's ruling (062).
- **Highlight.** A guard fires on the honest case (the launcher) or passes the dishonest one (any ten characters).
- **Probe.** *What evidence would an impostor lack that this check actually reads?* If nothing, it is this family.
- **Solution.** Bind identity to something only the real party has — a digest handshake, a global allocation surface, Rab's own act — never to a number that another process can hold.
- **Members.** SYM-040, 045, 062, 081. Method twin: **M6** (PROVENANCE-DROP, NAMESPACE-SCOPE).

### S11 · UNBOUNDED-OR-UNGUARDED-EFFECT
- **Reason.** A destructive or blocking act has no guard: an `rmtree` over a held bundle carrying repairs (009); an append that assumes the file ends in a newline (037); a fixture port that reached the live bench through `SO_REUSEADDR` (010); a credential fill that waited fourteen minutes for an interactive prompt (064); a report written beside the bundle that made the body scan count two bodies (030); an `xrefs=True` flag costing 34 s a page (048).
- **Highlight.** Held state gone, a torn line, a test hitting production, a close hanging with no error.
- **Probe.** *Name the precondition the act assumes; violate it in a fixture — what happens to the held state, the port, the clock?*
- **Solution.** Fail closed on the precondition; bound every external wait; a fixture never reaches a live port; an artefact never lands where its producer scans.
- **Members.** SYM-009, 010, 030, 037, 048, 064. Method twin: **M5/M8**.

### S12 · PLATFORM-OR-LIBRARY-SEMANTICS-TRAP
- **Reason.** The platform means something other than its name: `force_ocr=True` keeps the old text (012); inotify reports a cross-watch move as a plain create (011); MSIX virtualises AppData writes into the container (007) and kills the running app on servicing (051); a uv base interpreter missing (008); a fail-closed bundle reprocessed at every startup (015 — a cost, not a risk).
- **Highlight.** The flag or event does the opposite of its name; a write that "succeeded" is nowhere on disk.
- **Probe.** *Read the producer's own definition of the flag or event — its source or its docs — before trusting the name.*
- **Solution.** Bank the definition in the register the first time; verify the config from the boot log, never from the writing surface (SYM-007 ×4).
- **Members.** SYM-007, 008, 011, 012, 015, 051.

### S13 · MODEL-OUTPUT-HAZARD — SYM-003 (table-loop degeneration), SYM-074 (a bare `</think>` leaked into shipped markdown), SYM-115 (S131: `/no_think` leaked and the chunk was cut at it). Probe: diff output against input under the fence; count repeats and control tokens. Solution: the fence, the degeneration gate (J29), the think-leak filter.

### S14 · CONFOUNDED-COMPARISON — SYM-035 (arms run in a fixed order; the incumbent always runs on a cool card, the artefact scales with n). Probe: swap or interleave the arms.

### S15 · THE-INSTRUMENT-MANUFACTURES-THE-FINDING
- **Reason.** The audit or census has its own preprocessing bug or unstated input-shape assumption and creates false loss or coverage indistinguishable from real defects: the ladder strips the markdown escape before unescaping (076); degeneration measured on raw markdown where empty table cells drive the trigram (067); and, in the closeouts, the word-ratio blind to CJK (S116 Lane A), the numeral census counting ids (S119 F8), the coverage metric that does not look at pixels (S108), unmeasured-as-zero (S114 F7), and S119's headline: two thirds of "the model's 3 % loss" was the audit's.
- **Highlight.** A damning or reassuring number that moves sharply when the same artefact is re-read through a second extractor while the artefact does not change.
- **Probe.** *Re-derive the figure through a second, independently built path — does the number move while the artefact stays?*
- **Solution.** Gate the audit on ground truth from a second-shaped check before it flags; state the input-shape assumption and test outside it; `UNREAD` is never `0.0` or `1.0`.
- **Members.** SYM-067, 076 (+ S108 scan-1, S114 §9-F7, S116 §9-LaneA, S118 §8-F2, S119 §8-F1/F2/F8).

### S16 · GUARD-COARSER-THAN-THE-DEFECT — no symptom row yet; four closeout findings: a threshold veto summing partial text and table coverage (S104 §8-1), a one-directional survival guard blind to duplication (S116 §8-F3), a per-chunk threshold's blind zone between "obviously bad" and "perfect" (S117 §8-F2), a window-overlap fraction that cannot see one changed digit (S118 §8-F3 → J45). Probe: plant a defect one notch below the guard's resolution. Filed here so the next instance gets its row.

*Rows since this section was written (the table above is S123's, Historical): SYM-110 (S126, the guard's false-deny shapes — one grammar for two shells, fails closed on what it cannot read) and SYM-116 (S137: the same heredoc construct the guard over-denied also let a program-fed `git reset` pass — coarser than the defect in both directions). `error_families.py` is the source; run `--census`.*

## §3 The placing walk — how to group a new failure in under a minute

1. **Is the object a claim or a mechanism?** If an agent said something the evidence did not support, it is a METHOD family (ERROR-BIN); if a program did the wrong thing, a MECHANISM family (SYMPTOM-INDEX). Both may apply to one incident — file both rows.
2. **Run the probes in this order**, stopping at the first that bites: *which printed line does the claim rest on* (M1) → *does a second-shaped measurement agree* (M2) → *what population and predicate* (M3) → *was the premise read now or earlier* (M4) → *what is the boundary event's timestamp* (M5) → *which surface did the guard miss* (M6) → *does the result change through a harness-immune form* (M7) → *did the tree or the audience change* (M8). For mechanisms: *do the bytes differ across the layer* (S1) → *does the check go red when mutated* (S2) → *is this a default, cap or cut* (S3) → *did a failed probe render as a negative* (S4) → *which path never writes the signal* (S5) → *who survived the kill* (S6) → *who reads this field* (S7) → *is the fact frozen* (S8) → *which reference object* (S9) → *what evidence would an impostor lack* (S10) → *which precondition* (S11) → *what does the platform's own definition say* (S12).
3. **`python observability/error_families.py --place "<the symptom in your words>"`** prints the nearest families and their probes from signature words; it says `UNREAD` when nothing matches — then walk §3.2.
4. **File the row with its class (ERR) or place its id (SYM) in `error_families.py`** — `--census` exits 1 until you do, so an unplaced row cannot close a session quietly.
5. **A rediscovered defect is a MUSTER failure** (docs/21 §5 rule 4): if the family already has your row's shape, the register was not read at the open.

## §4 What the families say about the project

- **Method errors cluster where the tool layer and the measurement meet.** M2 and M7 hold 30 of 67 rows; both have probes that cost one command. The bin's own §A table still reads "23 classes, 45 rows" — a frozen fact (S8) inside the register of frozen facts; the census reads 24 classes and 67 rows.
- **Mechanisms cluster in the seams:** the byte layer (S1, four `autocrlf` instances across three files and two tools), the Room's projection surfaces (S7, seven open rows), and the guards themselves (S2, S5, S15, S16 — twenty rows that are checks failing at being checks; docs/32's prediction, counted).
- **Every open mechanism family has a cheap probe.** The debt is not diagnosis; it is running the probe at the open.

## §5 Provenance and residue

Built S123 (2026-09-10) from three Sonnet readers over every row (67 + 82 + 19 closeouts, 83 findings) and Fable's own read of the class table; every placement is refutable by its row; single-lane synthesis, no second vendor. Not done: the closeout findings marked NOT FILED by the third reader (about forty) have no rows and therefore no census — §2's S15/S16 name the two that recur; the rest await the next open that touches them. The `--place` signatures are keyword heuristics and say `UNREAD` when they do not match; they are a door, not a judge.

**Appended 2026-09-10 (post-close, Desktop S123).** The §2 counts are the 03:2xZ measurement over 82 SYMPTOM-INDEX rows. Three rows arrived after it: the ThinkPad lane's SYM-083 (fastembed's 256-batch × 512-token padding — S11) and SYM-084 (Taildrop only between same-user devices; a tagged node has no user — S12), and this lane's SYM-085 (a peer's uncommitted bytes in the shared checkout have no guard; ERR-068 — S11). `error_families.py --census` refused the two it had not seen (exit 1) until they were placed — its first refusal on real rows. The census is the count; this table is a photograph of it.

**Appended 2026-09-10 (S124, J55).** The closeout findings §5 called "not done" are done: 24 symptom rows (SYM-086..109), 9 method-error rows (ERR-…-069..077) and 5 tickets (J57..J61) were filed from the S104–S122 closeouts — five reader lanes proposed 79 candidates with quotes, every decoy refuted, every quote re-found in its closeout by hand before a row was written; 28 already-filed and 13 not-a-defect candidates are recorded with their reasons in `sessions/S124-desktop-2026-09-09.md` §8. **S16 GUARD-COARSER-THAN-THE-DEFECT now has five rows** (SYM-090, 091, 093, 096, 104) where §2 says "no symptom row yet"; S15 gained three (094, 095, 097), S7 four (092, 102, 103, 106), S12 four (086, 101, 105, 109), S5 two (089, 107), S8 two (098, 108), and S1/S2/S3/S11 one each (087, 100, 088, 099). The §2 counts are the 03:2xZ photograph over 82 rows; `error_families.py --census` is the count (109/109 · 77/77 at filing).
