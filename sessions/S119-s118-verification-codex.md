# S119 — independent Codex verification of S118

⟨claimed: Codex lane · occupant: OpenAI Codex (GPT-5.6) · S119 · 2026-09-09 UTC⟩

**Ticket:** `S118-VERIFY-CDX`  
**Relay basis:** `MSG-FAB-0077`; accepted in `MSG-CDX-0046`  
**Boundary:** read-only reconstruction of S118's quantitative claims. No gate, model,
pipeline, held bundle, vault, or widget state was changed.

## Verdict

**PASS WITH TWO CORRECTIONS AND ONE PRESERVED RISK.** The 0.80-lever result, J41
row evidence, SYM-076 unit behavior, and both S118 offline scores reproduce with an
independent implementation. S118's phrase "3.04% of windows" uses the wrong
denominator, and the commit named for the threshold transition is imprecise. The
ligature-blind rung remains a counterfactual measurement, not a safe change.

| Claim | Status | Independent result |
|---|---|---|
| Shipped rerun | **Verified** | `20,008 / 20,589` windows survive = `0.9718`; 581 fail in 49 runs |
| Prior run | **Verified from retained bodies** | `19,936 / 20,589` = `0.9683`; 653 fail in 61 runs |
| Lever effect | **Verified** | 72 fewer failed windows, `+0.0035`, and 12 fewer failure runs |
| New analyst disposition | **Verified** | 472 passed / 20 rejected / 0 failed; rejection reasons: fence 8, survival 12, think 0, inflation 0 |
| Old analyst disposition | **Observed, corroborated** | Manifest/frontmatter/events agree on 481 passed / 11 rejected / 0 failed; fence 8 and survival 3. The deleted old journal makes a reason-by-reason replay **UNREAD** |
| J41 completeness | **Verified** | 492 unique contiguous rows (`i=1..492`); `s` on 484, `r` on 472; 8 fence and 12 survival rows; all survival rejects are below 0.80 and all passed rows are at least 0.80 |
| J41 size | **Verified** | 17,507 bytes using the stored/default JSON encoding (14,572 compact bytes) |
| Escape-first rung | **Verified** | `0.9756`, 503 failures, 46 runs |
| Escape-first + ligature-blind | **Verified as counterfactual** | `0.9808`, 396 failures, 33 runs |

## Ground and binding

- **Verified:** both measurements use the same 20,665,337-byte source PDF, SHA-256
  `fc1f068c3a8eeb6344a37c3406df64ef46013f474a45fcfc66dbdc919e0d9a35`.
- **Verified:** the old and new Marker bodies are byte-identical: 1,991,297 bytes,
  SHA-256 `3a14d17d13c30c8b4c683e9edc7abfc5701749fdd12894e7af87aa52115c3950`.
- **Verified:** the current held body is 1,974,215 bytes, SHA-256
  `726bbcf63f6d5087d4814849007d2409e3efc6e9ebc711a800bb0ed70567bb49`;
  its manifest binds that body and the Marker body. The new anchor `(1)` copies are
  byte-identical to the held copies.
- **Verified:** the independent meter used 20,589 non-overlapping twelve-word
  reference windows. It did not import File Portal's audit implementation.

## Correction 1 — the 3.04% label

`Σ(1-s_i) = 14.3259` across 472 passed chunks, and `14.3259 / 472 = 3.0351%`.
That is an **unweighted mean per-chunk loss**, expressed in chunk-equivalents. It is
not a percentage of windows.

The actual window-weighted quantities are:

- passed chunks: `580 / 19,835 = 2.9241%` loss;
- body chunks 41–440: `517 / 16,938 = 3.0523%` loss;
- whole document: `581 / 20,589 = 2.8219%` loss.

**Disposition:** retain `3.04%` only when labelled “mean loss per passed chunk.” Use
`2.9241%` for “percentage of passed-chunk windows lost.” The concentration claim
survives: 517 of the 580 passed-chunk misses are in the body.

## Correction 2 — threshold commit provenance

**Verified:** the 0.50 → 0.80 source transition is in
`aa9381839c3991469db85a095b96738b457fb89a`; its parent contains 0.50 and the commit
contains 0.80. `c5709d7` is titled as the lever move but carries no `analyst.py`
delta. Because `aa93818` precedes the rerun, the live behavior was correctly 0.80;
this is a provenance correction, not a behavioral failure.

## Preserved risk — ligature blindness

The intended probes reproduce:

- `within\\_recursive` → `within_recursive`: shipped `0.0`, escape-first `1.0`;
- `\\rm` → `rm`: escape-first remains `0.0`;
- identity control: `1.0`; real deletion control: `0.0`.

But the named adversarial probe `fine` → `ne` scores `0.0` under escape-first and
**falsely scores `1.0` under ligature-blind normalization**. Therefore `0.9808 / 33`
sizes a counterfactual; it does not establish semantic safety. J44 adoption remains
**UNREAD** pending a signed design and controls for this collision class.

## Controls and residue

- **Verified:** J41's row validator accepts the real 492 rows, rejects a removed row
  (491 rows plus sequence error), and rejects a passed row with `s` removed.
- **Verified:** the real marker-environment analyst audit selftest passes 8/8
  tripwires. The uv-Python attempt could not import `pymupdf` and is **UNREAD**, not
  a failed gate.
- **Observed:** current `text_norm.py` remains the shipped v2 implementation; this
  ticket made no implementation change.
- **Residue:** the old successful-run journal no longer exists, so the old
  per-chunk rejection replay cannot be recovered from this machine.

## Handoff

S118's main quantitative story stands after relabelling the loss denominator and
correcting the threshold commit attribution. Do not present the ligature-blind rung
as safe or shipped. No signature is consumed by this verification.
