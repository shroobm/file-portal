# T-004 — the EXTRACTED export: published schema v1

**Status: DRAFT, unsigned, PUBLISHED FOR REVIEW. Not adopted. Nothing built against it yet.**
⟨claimed: Fable lane · occupant: Claude Opus 5 · S109 · 2026-08-24T19:14Z⟩

> ## PRODUCED SINGLE-LANE — no cross-vendor check exists on this document
>
> This schema was written by **Claude agents only**, orchestrated by one Claude session. The
> Codex lane **ran out of budget** before it could review anything here. Per `MSG-FAB-0005`
> step 2, Codex's review of this schema is a **precondition** of the work that follows it, and
> that review **has not happened**.
>
> This is a **discount on the evidence, not a disclaimer for show.** Every design choice below
> was made and checked by the same vendor that will write the EXTRACTED export. The seam this
> schema governs exists precisely because one writer checking their own work is not enough — so
> a single-vendor schema for that seam is the weakest form the document can take. Read it as a
> **proposal from one interested party**, and weight it accordingly.

---

## §0 What this document is, and what it is not

`T-004` is a **joint** deliverable. `MSG-FAB-0005` (2026-08-24T07:39Z, digest
`sha256:d0376c28af8b0ce59dc35a73bc01ee1769f2bd82ee0b926d7e41d2ec3eb1cbaf`) split it five ways:

| step | owner | deliverable | state today |
|---|---|---|---|
| 1 | Fable | address-preserving corpus, structural extraction pass, **EXTRACTED export + manifest + this schema** | **only the schema exists — this file** |
| 2 | Codex | review this schema **before building anything against it** | **NOT DONE — Codex out of budget** |
| 3 | Codex | AUTHORED export at a pinned lab revision + deterministic comparator | NOT DONE |
| 4 | Fable | review the comparator **and independently reproduce the diff without running it** | NOT DONE |
| 5 | Joint | the diff, every unmatched term carrying evidence for exactly one of Rab's three dispositions | NOT DONE |

**This file is step 1's *schema* only.** It is the half I publicly committed to in `MSG-FAB-0005`:

> *"The EXTRACTED export needs a published schema before your comparator is written, or you are
> aiming at a moving target. I will publish it as the pilot's first deliverable, for your review,
> before any comparator work starts."*

**What does NOT exist:** no corpus, no extractor, no export, no manifest, no comparator, no diff.
No code was written for this document. **No File Portal file is read, adopted, or altered by
this schema.**

### Why the other half is missing — say it precisely

The joint half is **blocked on Codex's budget, not on Rab.** Rab has not refused anything here
and is not the bottleneck for steps 2 and 3. Separately and unchanged: steps 2–5 also remain
**blocked on Rab's signature of `CR-CDX-0001`**, which he has neither signed nor rejected. Both
blocks are live; they are different blocks, and neither is the other's excuse.

**The joint half must not be faked.** No Claude agent may write the AUTHORED export or the
comparator. That is not a resourcing preference — it is `CR-CDX-0001` clause 2 ("*neither writes
the other's export*"), and a single vendor writing both sides of a comparison produces an
artifact with no evidentiary value whatsoever.

### The cadence objection stands, unretracted

`MSG-FAB-0005` recorded a recommendation to Rab that **C0 — one book converting end to end —
should breathe before the seam starts**, because the project's measured disease is governance
outpacing product (`docs/45` M5; `OPEN-TASKS.md` §0: *"Nothing in the product has moved for ten
sessions"*). **This document is more governance.** Publishing it does not withdraw that
recommendation and must not be read as overtaking it.

---

## §1 The requirement this schema has to satisfy

From `MSG-FAB-0005`, the ADDITION attached to `CR-CDX-0001`:

> **"the diff must be independently reproducible from the two revision-pinned exports by a third
> party who trusts neither writer."**

Everything in §2–§7 is that sentence made mechanical. The test for any clause below is:

> **Could a stranger, on a different machine, holding only the two exports and this schema,
> re-derive the identical diff without running Codex's comparator and without asking Fable
> anything?**

If a clause is not needed for that, it is not in this schema. If a clause is needed and missing,
that is a defect and I want it named in review.

---

## §2 The addressing rule — and the measurement that forces it

**Rule EX-1 (load-bearing).** Every record addresses **git blob bytes**, obtained by
`git cat-file blob <commit>:<path>`. **The working-tree file is never read, never hashed, and
never cited.**

This is not stylistic. On this repo the two choices give different answers.

### The bite — the same commit, two legal checkouts

I checked commit `d6599a797f0257e69542f77af45435a1569a4949` out twice: once as it sits on this
machine (`core.autocrlf=true`, the Windows default), once into a scratch clone with
`core.autocrlf=false` (the Linux/macOS default). Both are ordinary, correct git configurations.
Neither is misconfigured.

```
both checkouts at commit: d6599a797f0257e69542f77af45435a1569a4949
  A autocrlf=true  B autocrlf=false

RULE REJECTED  (address the WORKING TREE) -> files whose digest differs between the two checkouts: 64 of 168
RULE ADOPTED   (address the BLOB)         -> files whose digest differs between the two checkouts: 0 of 168

specimen: .claude/skills/echo/lexicon.md
  A worktree sha256: 15a0dde555a30053ccbdfd7a0f2e7c6ddd3f3d47f472732e375096671c456c06
  B worktree sha256: 54030e8bfcfecd7e1dd3b6de74725853d1f0d9a923b568aef4223cc3f3797d09
  A blob     sha256: 54030e8bfcfecd7e1dd3b6de74725853d1f0d9a923b568aef4223cc3f3797d09
  B blob     sha256: 54030e8bfcfecd7e1dd3b6de74725853d1f0d9a923b568aef4223cc3f3797d09
```

**A working-tree-addressed export is not reproducible by a third party — on 64 of 168 tracked
markdown files it would hand them a digest they cannot reproduce, and the export would appear
*corrupt* to an honest reviewer on Linux.** Blob addressing is `0 of 168`. `Verified`.

Supporting census at the same commit (`Verified`): all **168 of 168** tracked `.md` blobs are
pure-LF and uniform; the **working tree** is `LF 104 · CRLF 59 · MIXED 5`. The blob layer is
already canonical. The checkout is the thing that is not.

This repo has **no `.gitattributes`** (`Observed`), so nothing pins the checkout's behaviour and
nothing will. EX-1 routes around the problem rather than trying to fix it.

The hazard is not theoretical or historical — git announced it in my own terminal while this
document was being written, about a file in this very directory:

```
warning: in the working copy of 'coordination/DISCLOSURE-STANDARD.md',
         LF will be replaced by CRLF the next time Git touches it
```

That is the working tree preparing to diverge from the blob, live, on a coordination file.
Under EX-1 it changes nothing, because EX-1 never reads the working tree.

### EX-1 corollary: the address is self-verifying

A git blob id is `sha1("blob " + len + "\0" + content)`. A third party can therefore confirm the
cited bytes are the cited bytes **without trusting either writer and without network access**:

```
blob id (git rev-parse HEAD:path) : 564a9e2b0cfbb8481e266b1aa844290aea192679
git show == git cat-file blob     : True
sha1('blob <len>\0'+bytes)        : 564a9e2b0cfbb8481e266b1aa844290aea192679
self-verifying address holds      : True
```
(`Verified`, specimen `SYMPTOM-INDEX.md`. Its blob sha256 is `ab76eb5b…`; its working-tree
sha256 on this machine is `030f570d…` — 62,813 bytes versus 62,818, five CRLF lines of drift.
The specimen is a **register file the seam actually cares about**, not a curiosity.)

---

## §3 The pin block — what an export must carry before any record

Every EXTRACTED export begins with exactly one `manifest` record. An export missing any field
below is **invalid and must be rejected**, not repaired.

| field | meaning | why a stranger needs it |
|---|---|---|
| `schema` | `fp-extracted/v1` — this document | tells them which rules to apply |
| `schema_digest` | `sha256` of this file's **blob** bytes | proves they are reading the same schema |
| `corpus_commit` | full 40-char commit SHA | the revision pin |
| `corpus_tree` | tree SHA of that commit | catches a rewritten commit with identical message |
| `corpus_paths_digest` | `sha256` over the canonical sorted `path\0blobid\n` listing of every included file | one number that fixes the entire input set |
| `included` / `excluded` | the exact path sets, and the rule that produced each | an unstated exclusion is a hidden input |
| `rules_id` | `fp-ex-rules/v1` + `sha256` of the rule table | the extraction is only reproducible if the rules are pinned |
| `extractor_revision` | commit SHA of the extractor + `sha256` of its source | claim-vs-probe applied to the instrument |
| `unicode_version` | e.g. `15.0.0` | **see §6 — normalization is Unicode-version dependent** |
| `record_count` | total records, and per-rule counts | every count states its denominator |
| `unread` | files/regions the extractor **could not** process, each with a reason | **§4 below** |
| `export_digest` | `sha256` over the canonical bytes of all records after the manifest | the artifact's own address |

Measured pins available today (`Observed 2026-08-24`): `corpus_commit`
`d6599a797f0257e69542f77af45435a1569a4949`; `corpus_tree`
`3d9047b7af2ed2791df98f7e587b9e94293e3c35`; 397 tracked files
(`md 168 · py 74 · png 49 · json 22 · rs 16 · html 14 · sh 13 · txt 8 · toml 7 · ps1 5`).
`corpus_paths_digest` and the rest are **UNREAD** — no extractor exists to compute them.

---

## §4 The UNREAD law — a failed probe is never a zero

**Rule EX-2.** If the extractor cannot process a file or a region — undecodable bytes, a parse
error, a binary path, a timeout — it emits an `unread` entry naming the path, the blob, the
region, and the reason. **It never emits zero records and calls the file clean.**

An export where `unread` is absent is invalid. An export where `unread` is the empty list is
making a positive claim that every included path was successfully processed, and that claim is
checkable by a stranger against `included`.

This is `SYM-001`'s shape and this repo's own standing hazard: *a tripwire honestly green while
the record is wrong* (`docs/45` §1, Family 1). An extractor that silently skips a file it choked
on reports "no terms here" — which the comparator will read as **"Codex fabricated this term"**.
A skipped file becomes an accusation. That is the single most damaging failure this schema can
have, and EX-2 exists only to prevent it.

---

## §5 The record — one occurrence, one record

```json
{
  "rule":      "MD-HEADING",
  "kind":      "heading",
  "path":      "coordination/DISCLOSURE-STANDARD.md",
  "blob":      "132f6df58d34a140a2ea4cc7d116a43b9dc316b5",
  "byte_start": 2,
  "byte_len":   52,
  "surface":   "The Disclosure Standard — what a lane OWES the bus",
  "key":       "the disclosure standard — what a lane owes the bus",
  "id":        "fe65cb4432005749"
}
```

**This example is a real record, not a sketch.** `git cat-file blob
132f6df58d34a140a2ea4cc7d116a43b9dc316b5`, sliced `[2:54]`, equals `surface` — checked
(`Verified`). A reader who cannot reproduce that has found a defect in this document.

- **`byte_start` / `byte_len` are authoritative and are offsets into the BLOB**, not the working
  tree, not a line number. A line number is a derived convenience and, on a repo whose checkout
  rewrites bytes, a line number is not an address. Any `line` field is advisory and non-normative.
- **`surface`** is the exact decoded blob slice. `surface` re-encoded as UTF-8 MUST equal
  `blob[byte_start : byte_start+byte_len]`. A stranger can check this on every record.
- **`key`** is `surface` under §6's normalization, and is the **only** field the comparator may
  match on.
- **`id`** = first 16 hex of `sha256(rule + "\0" + blob + "\0" + byte_start + "\0" + byte_len)`.
  Content-addressed, so two independent extractors agree on ids without coordinating.
- **`rule`** names the mechanical rule that produced the record. A record with no rule id is
  invalid — this is how "no model judgment" is made checkable rather than promised (§7).

**Rule EX-3 — one record per occurrence; the export never de-duplicates.** A term appearing in
nine files yields nine records. Address preservation is the entire point: when Rab decides
whether an unmatched term is tacit knowledge, a model-owned term, or a fabrication, he needs
**where**, not **how many**. Any de-duplication is the comparator's business, downstream and
visible.

---

## §6 The key law — where the diff would quietly stop being reproducible

**This is the clause the ADDITION forces, and I believe it is the one most likely to be wrong.**

A comparator matches AUTHORED terms against EXTRACTED terms. Matching requires normalization —
case, whitespace, punctuation. **If that normalization lives inside Codex's comparator, the diff
has a hidden input and no third party can re-derive it.** Reviewing the comparator's source is
not a substitute: the stranger would have to run it, which is the exact dependency the ADDITION
was written to remove.

**Rule EX-4. Normalization is published here, in the schema, and both sides compute it
independently.** The comparator does not own it.

`key` is derived from `surface` by exactly these steps, in this order:

1. Decode the blob slice as **UTF-8, strict**. On failure: no `key` is guessed — the record
   carries `"key": null, "key_error": "utf8"` and the region is also listed in `unread` (EX-2).
2. Unicode **NFKC**.
3. **`casefold`** (not lowercase — `casefold` handles the cases lowercase does not).
4. Every TAB, LF, CR and every character of Unicode category `Zs` becomes U+0020.
5. Runs of U+0020 collapse to one; leading/trailing stripped.
6. Characters of Unicode category `P*` or `S*` are stripped **from the ends only**.

**Internal punctuation is preserved. No stemming. No singularization. No synonym folding.**
Those are match *policy*, not normalization, and they are judgment. See EX-5.

**Rule EX-5.** The comparator MAY apply additional match policies, but each must be published,
named, versioned and pinned in the diff, and the diff must be re-derivable from the published
`key` values plus the published policies alone. **An unpublished match policy invalidates the
diff**, however good its results look.

### The hazard inside EX-4, named

**NFKC and `casefold` are Unicode-version dependent.** Two strangers on two Python builds can
compute two different keys from the same bytes and neither is wrong. This is why
`unicode_version` is a mandatory manifest pin (§3) and why a diff computed across two different
`unicode_version` values must be **refused, not reconciled**.

Measured here (`Observed`): `python 3.12.13`, `unicodedata.unidata_version = 15.0.0`. Worked
specimen, byte-addressed from a real blob: `byte_start=2 byte_len=52`, surface
`'The Disclosure Standard — what a lane OWES the bus'`, key
`'the disclosure standard — what a lane owes the bus'`, id `fe65cb4432005749`. The em dash is
`U+2014` and survives NFKC unchanged (`Verified` — I checked the codepoint, because my console
printed it as a replacement character and I was not willing to record that as data; see §10).

---

## §7 What "structural extraction, no model judgment" means mechanically

`MSG-FAB-0005` step 1 constrains the pass to *"enums, constants, schema keys, register table
rows, headings — regex/AST, no model judgment."*

**Rule EX-6.** Every rule in `fp-ex-rules/v1` must be **executable by a program with no model in
it**, and must be stated in the rule table as either a regex or a named AST traversal. Proposed
initial rule set, for Codex to amend:

| rule id | applies to | mechanism |
|---|---|---|
| `MD-HEADING` | `*.md` blobs | ATX headings, regex |
| `MD-TABLEROW` | the registers (`OPEN-TASKS.md`, `SYMPTOM-INDEX.md`, and any pipe table) | pipe-table row split; cell 1 as the term, remaining cells as evidence |
| `PY-CONST` | `*.py` | `ast` — module-level assignments with `UPPER_SNAKE` targets |
| `PY-DICTKEY` | `*.py` | `ast` — string-literal keys of dict literals |
| `PY-ENUM` | `*.py` | `ast` — members of `enum.Enum` subclasses |
| `RS-ITEM` | `*.rs` | regex — `enum`/`const`/`static` names and variants (**no Rust AST available; see §9**) |
| `CFG-KEY` | `*.toml`, `*.json` | full key paths, dotted |

**Rule EX-7 — the model-judgment ban is structural, not promised.** The export is invalid if any
record cannot be regenerated by re-running the pinned rule set at the pinned commit. A stranger
tests this by re-running the extractor and comparing `export_digest`. A record a model inserted
by hand does not survive that test. This is the same move `CR-CDX-0001` makes with ownership: put
the rule where it can be checked, not where it must be believed.

---

## §8 Serialization — canonical, or the digest means nothing

**Rule EX-8.** JSON Lines: one record per line, first line the manifest.

- UTF-8, **written with an explicit encoding, never the platform default.** (Real hazard, not
  hypothetical: on this machine Python's `sys.stdout.encoding` is `cp1252` — an export written to
  the default stream would mangle every non-ASCII surface it touched. `Observed`.)
- `\n` only. Never `\r\n`, whatever the host OS does — see §2.
- Object keys sorted byte-wise ascending; no insignificant whitespace.
- Non-ASCII emitted **literally**, not `\u`-escaped.
- Integers only. **No floats anywhere in this schema** — floats do not round-trip identically
  across languages and would break the digest for a stranger using a different one.
- Records sorted by `(path, blob, byte_start, byte_len, rule)`, byte-wise ascending.
- `export_digest` = `sha256` of all bytes after the manifest line, inclusive of its final `\n`.

Two conforming extractors, same commit, same rules, same `unicode_version`, must produce
**byte-identical** files. If they do not, the schema is defective and I want that reported as a
defect against this document.

---

## §9 The reproduction recipe — the acceptance test for this whole schema

A third party who trusts neither writer, holding both exports and this file, must be able to:

1. `git clone` File Portal, `git checkout <corpus_commit>`, confirm `corpus_tree` matches —
   **with any `core.autocrlf` setting**, because §2 never reads the working tree.
2. Recompute `corpus_paths_digest` from the pinned path set and confirm the input is the input.
3. For **every** record: `git cat-file blob <blob>`, slice `[byte_start : byte_start+byte_len]`,
   and confirm it equals `surface`. No sampling.
4. Recompute every `key` from `surface` by §6 under the manifest's `unicode_version`.
5. Recompute every `id`, re-sort by §8, recompute `export_digest`.
6. Do the same for the AUTHORED export at its pinned lab revision.
7. Compute the diff from the two `key` sets plus the published match policies (EX-5) — **without
   running Codex's comparator.**
8. Compare against the shipped diff. Any divergence is a finding against whichever side's
   published rules failed to produce it.

**Step 7 is the ADDITION.** Steps 1–5 are what this document buys it.

---

## §10 What cannot be verified until the other half exists

Stated plainly, because a schema published by one vendor is at its most dangerous where it sounds
finished.

**UNREAD — nothing here has been tested against a real EXTRACTED export**, because no extractor
and no export exist. Every count in §3 beyond the pins is UNREAD.

**UNREAD — sufficiency.** Whether these fields are *enough* for a comparator is unknown until
Codex writes one. That was the entire purpose of step 2, and step 2 has not happened. A schema
whose consumer has never seen it is a guess about someone else's needs.

**UNREAD — whether §6's normalization suits the AUTHORED vocabulary.** I designed EX-4 against
the shape of *this repo's* terms. The Concordance Lab's terms are external, I have not read them,
and they may be phrases, multi-word, or cased in ways that make step 6's end-punctuation strip
wrong. **This is the clause most likely to need amendment, and I cannot amend it alone.**

**UNREAD — `RS-ITEM`.** The Rust rules are regex, not AST, because no Rust parser is available in
this lane. Regex over Rust will mis-handle macros, `cfg`-gated items and raw strings. The rule is
declared **weaker than its neighbours on purpose** rather than quietly shipped as equal.

**UNREAD — the three dispositions.** Whether an unmatched term can actually be sorted into *tacit
knowledge to sign* / *model-owned term to retain* / *fabrication to delete* on the evidence a
record carries is untested. If `path + blob + bytes + surface` is insufficient, Rab is being asked
to decide on evidence that does not support the decision, and **neither model may decide for him**
(`CR-CDX-0001` clause 4).

**NOT VERIFIED — the schema against itself.** No conforming extractor has run, so §8's
"byte-identical output" claim is a *specification*, not an observation. It is `Inferred`.

**NOT VERIFIED — anything cross-vendor.** No second vendor has read a line of this. See the
banner.

### One thing I got wrong while writing this, recorded rather than buried

My first line-ending census was **instrument failure**. `grep -Uc $'\r$'` lost its carriage
return in shell transport, collapsing the pattern to bare `$`, which matches every line; the same
file returned `5` and `82` on two runs. The degraded run reported "162 pure-CRLF, 0 pure-LF" —
confident, plausible, and measuring nothing. I discarded it and re-measured in Python, which is
immune to that transport. **§2's numbers come from the Python census, not the grep one.**

It is worth saying why this belongs in a schema document: it is `docs/45` Family 1 exactly — *the
sentence describes the neighbour of the probe* — and it happened while writing the rules meant to
prevent it. If it can happen here, it can happen in the extractor, which is what §4 (EX-2) and §7
(EX-7) are actually for.

---

## §11 Review questions for Codex — the specific asks

Not "thoughts?" — these are the six places I expect to be wrong.

1. **EX-4 / §6:** Is the normalization right for the AUTHORED vocabulary's shape? Specifically
   step 6 — stripping end punctuation — and the refusal to stem. **Amend it; do not work around
   it in the comparator**, because that is EX-5's failure mode.
2. **EX-5:** Can your comparator run with *no* unpublished match policy? If not, name what it
   needs, and it gets published here instead.
3. **§5:** Does a record carry enough for the diff? Name the missing field now, not after the
   export is built.
4. **EX-3:** Does one-record-per-occurrence break your comparator's shape? If it needs a
   de-duplicated view, that is a comparator-side projection, and I want it stated.
5. **§3:** Does the AUTHORED export carry an equivalent pin block? The reproduction recipe needs
   **both** sides pinned; today only this side is specified.
6. **§7:** `RS-ITEM` is regex where its neighbours are AST. Does the lab's vocabulary depend on
   Rust identifiers? If yes, this rule needs to be fixed or dropped, not shipped weak.

---

## §12 Provenance of every claim in this document

| claim | tag | probe |
|---|---|---|
| 64 of 168 md files differ between the two checkouts; blob differs 0 of 168 | `Verified` | scratch clone at `-c core.autocrlf=false` of `d6599a7`, sha256 both sides in Python (§2) |
| all 168 md blobs pure-LF; worktree `LF 104 / CRLF 59 / MIXED 5` | `Verified` | Python census over `git ls-files` + `git show HEAD:<path>` |
| no `.gitattributes`; `core.autocrlf=true` on this machine | `Observed` | `cat .gitattributes` (absent), `git config core.autocrlf` |
| blob id = `sha1("blob "+len+"\0"+content)`, self-verifying | `Verified` | recomputed for `SYMPTOM-INDEX.md`, matched `564a9e2b…` |
| `SYMPTOM-INDEX.md` blob 62,813 B / worktree 62,818 B, 0 vs 5 CRLF | `Verified` | same probe |
| corpus pins `d6599a79…` / tree `3d9047b7…` / 397 tracked files | `Observed` | `git rev-parse`, `git ls-tree -r --name-only HEAD` |
| `unidata_version 15.0.0`, python 3.12.13, stdout `cp1252` | `Observed` | pinned interpreter |
| worked specimen surface/key/id | `Observed` | Python, on the real blob slice |
| §8 conforming extractors produce byte-identical output | **`Inferred`** | **no extractor exists** |
| this schema is sufficient for a comparator | **`UNREAD`** | **no comparator exists; Codex has not reviewed** |

Probes ran read-only against the repo and a scratch clone. **No pre-existing file under
`coordination/` was modified or deleted; this document is the only file this lane added there.
No bus message was written. `relay.md`, `ack-fable.json` and `ack-codex.json` were digest-pinned
before and after this lane ran and are byte-identical. `gate.py` was not run, and no escalation,
ticket or beat was created.**

**Corrections to this document are APPENDED and dated. Nothing above is rewritten.**

---

*Model trailer: `Claude Opus 5`, S109 · authorship claim only, never Rab's authority. Produced
single-lane by Claude agents with no cross-vendor check, because the Codex lane ran out of
budget. This document is unsigned and adopts nothing.*
