# docs/28 — The repair ledger, and what a rescore may honestly claim

**Status: PROPOSAL — nothing ships unsigned.** Written S76 (2026-08-14) from Rab's design,
after his manual ✎ edit removed a 2,051-character loop from the S76 Beer and left **no trace
at all**: `repairs: 0`, `undo_depth: 0`, no marker in the text, and the zone's excerpt anchor
destroyed along with it.

> *"if every single change that happens in the markdown document also corresponds to some sort
> of ledger audit system that follows the established laws, it can correspond to capturing all
> state changes, and determines exactly what was removed, as it saves a chunk that comfortably
> covers the margin that has changed, and determines if it was either a removal, an addition or
> an edit, and this chunk corresponds to the identification of the change as an event as well,
> that is collected onto a final report once all zones and omissions are completed"*

## 1. The hole this closes

The bench has **five** body-write paths and they are not equally honest:

| path | `.bench-bak` | undo | manifest record | provenance in the text |
|---|---|---|---|---|
| `repair()` crop / paste | ✓ | ✗ | ✓ | ✓ embed + comment |
| `transcribe_apply()` | ✓ | ✓ | ✓ | ✓ comment |
| `collapse()` (S76) | ✓ | ✓ | ✓ | ✓ marker |
| `assist()` AI fix | ✓ | ✓ | ✗ | ✗ |
| **`/api/md` manual save** | ✓ | **✗** | **✗** | **✗** |

The last row is how 2,051 characters left a vault-bound document with nobody able to say what
they were. `.bench-bak` is a **single snapshot of the first write** — it is not a history, and
the second edit onward has no floor under it at all.

## 2. The design — one chokepoint, one append-only ledger

**The law: no body write may bypass the ledger.** Every path above funnels through a single
`_write_body(new_body, *, gesture, zone_line=None, note="")`, which diffs old→new, classifies
each changed region, appends an event, and only then writes. A write that cannot be recorded
is refused, exactly as the supersede marker refuses a re-queue whose intent cannot be filed
(docs/15 §14.7). One writer, one record — the same law the pipeline already runs on.

**Where it lives:** `<bundle>/repairs.jsonl`, append-only, one JSON object per line — the
`events.jsonl` idiom the factory already uses, and restart-safe by construction (the S71
lesson: in-memory ledgers forget, files do not). `manifest["repairs"]` stays as the summary
index; the jsonl is the full record.

**The event, per changed region** (a diff opcode, computed with `difflib.SequenceMatcher`):

```jsonc
{
  "ts": "2026-08-14T04:31:02+00:00",
  "seq": 7,                       // monotonic per bundle
  "gesture": "manual-edit",       // crop|paste|transcribe|collapse|assist|manual-edit
  "kind": "removal",              // removal | addition | edit
  "at": {"before": [1836, 1836], "after": [1836, 1835]},   // line ranges, 1-indexed
  "chars": {"removed": 2051, "added": 0},
  "margin": {                     // the chunk that "comfortably covers" the change
    "context_before": ["the sum of vertical variety disposed on the six…", ""],
    "removed": ["A. The state of the state of … th Ex S"],   // VERBATIM, capped
    "added": [],
    "context_after": ["", "![[assets/_page_118_Picture_0.jpeg]]"]
  },
  "zone_line": 1847,              // the damage this addresses, when known
  "sha_before": "…", "sha_after": "…"   // body hashes: the chain is verifiable
}
```

Two properties worth naming. **The removed text is stored verbatim** (capped, with a hash and
a `truncated` flag beyond the cap) — so the ledger is not merely a note that something went,
it is the archive of what went. That makes it a stronger recovery floor than `.bench-bak`.
And **the sha chain** makes the history checkable: if `sha_after` of event *n* does not equal
`sha_before` of event *n+1*, something wrote outside the chokepoint and the ledger says so.

**Undo becomes ledger-driven** rather than a 20-deep in-memory stack that dies with the
process — pop the last event, restore its `before` margin, mark the event `reverted`. Never
delete the event; a reverted change is history too.

## 3. The final report

When the operator declares the patient done, walk the ledger and emit a human-readable
`REPAIRS.md` beside the bundle (and a summary block into the manifest):

- every zone and every omission run, each with its outcome and the events that produced it;
- totals — characters removed, added, images embedded, lines transcribed;
- **what is still open**, stated plainly;
- the entropy figure Rab set as the operator-work measure: characters removed as a fraction of
  the document. The S76 Beer's loop was **0.970 %** — inside his 0.01–1.00 % target.

This is the artifact the vault note should carry. A reader a year from now can then ask "why
is there an image here and a gap there" and get an answer.

## 4. The rescore — what it may honestly claim

Rab's open question. The answer his own laws already imply: **there are two different
questions and they must never be merged into one number.**

**Question 1 — does the TEXT still match its source?** That is `doc_survival` and
`degeneration`, recomputed from the current body. Note the asymmetry, which is the whole
difficulty:

- **Degeneration genuinely clears.** A loop removed — by collapse, edit, or AI — is measurably
  gone. The rescore may say so without qualification.
- **An omission does NOT clear when an image is placed.** Cropping page 114 into the document
  restores the content *to a human reader* and changes nothing for a text comparison. The run
  is still open by the metric, and the metric is right.

**Question 2 — has a human addressed every located defect?** That is provenance, not
measurement. Answer it from the ledger, and report it beside the metric, never inside it:

| outcome | meaning | who decides |
|---|---|---|
| `text-restored` | a ⌨ transcription put real text there — the run genuinely re-measures better | the machine, on re-run |
| `image-restored` | a crop carries the content a reader needs; the text metric is unmoved | the operator asserts |
| `collapsed` | noise removed; content was never recovered and is not claimed to be | the machine |
| `dismissed-noise` | **the witness itself was garbage — nothing real was lost** | the operator judges |
| `open` | untouched | — |

**`dismissed-noise` is not a loophole; it is the scan lane's actual truth.** On the S76 Beer,
12 of the 18 omission runs have excerpts like `cl$ms£ct4 <xi)v/^fc-c4fe'v(-6-h^tr` — the
embedded OCR's own hallucination over handwriting. The converter did not lose text there; it
declined to reproduce nonsense. Counting those as damage would make the operator chase ghosts,
and docs/15 already says the quiet part out loud for this lane: two witnesses, *"we do not
pretend to measure truth."*

**So the rescore returns three things and blends none of them:**

1. the recomputed machine metrics (survival, degeneration, runs) — same meaning as always;
2. **coverage** — the ledger's tally of located damage by outcome;
3. a **vault-eligibility recommendation**, which is a statement about both:
   *degeneration clear* **AND** *every located omission is text-restored, image-restored,
   collapsed, or dismissed-with-a-reason* — nothing left `open`.

And eligibility stays a **recommendation**, because image-restored and dismissed-noise are
human assertions. The constitution already has the instrument for turning a human assertion
into a record: the **bless rail** (S56). A bundle whose omissions are image-restored is
exactly a bless case — the operator signs that the images carry what the text cannot, and the
signature is filed. The machine never credits an image as text; the human does, in writing.

This also fixes the number that misleads today: `doc_survival` can be a fabricated `1.0` when
nothing was measurable (docs/26 F4), while coverage would correctly read *0 of N addressed*.
Two honest numbers beat one flattering one.

## 5. Build order (each independently useful)

1. **The chokepoint + ledger** — `_write_body`, `repairs.jsonl`, all five paths funnelled,
   sha chain. Closes the manual-edit hole immediately.
2. **Ledger-driven undo** — replaces the in-memory stack; survives restarts.
3. **Outcome triage on the chips** — mark each zone/run `dismissed-noise` or leave open; this
   is the operator judgment the rescore needs, and it is one click per site.
4. **The rescore split** — metrics + coverage + recommendation, never merged.
5. **`REPAIRS.md`** — the final report, generated from the ledger.

## 6. Awaiting signature

- The chokepoint law (no write bypasses the ledger; a write that cannot be recorded is refused).
- Verbatim capture of removed text into the ledger, and its cap.
- The five outcomes in §4, especially `dismissed-noise`.
- Whether vault eligibility is a recommendation routed through the existing bless rail
  (recommended) or a hard gate.
