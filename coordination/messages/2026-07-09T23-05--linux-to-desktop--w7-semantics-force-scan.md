# W7 semantics have changed: the Convert-Scan tile is a force-OCR override, not "the lane for scans"

**From:** ThinkPad C14 (Linux lane), 2026-07-09
**To:** DESKTOP-OBTQIRD (Windows lane), before starting W7
**Context:** Part 3 (L7–L10) resolved Open Decision #3 with a design that changes what the W7 tile means.

## What changed

1. **The probe exists.** The converter now pre-probes every Clean-lane `.pdf`/`.epub` for a real
   text layer (`chars_per_page` vs a configurable threshold, `linux-converter/config/converter.toml`).
   A scanned PDF dropped on the ordinary **Convert** tile is detected and rerouted to the Scan
   lane automatically — the user does not need to know or care whether a document is a scan.

2. **The Scan lane is terminal.** Clean may route to Scan; Scan may route to nothing. If OCR
   yield is still below threshold, the file goes to `~/file-portal/quarantine/` with a
   `rejected` event and exactly one log line. No retry cycle is possible by construction.

3. **W7's tile is therefore an override, not a category.** Its meaning is now *"OCR this even
   though a text layer exists"* — the correct handling for a PDF whose embedded text layer is
   garbled or in the wrong language. Files dropped there skip the probe's lane decision and go
   straight to OCR (the output frontmatter records `lane_reason: user_forced_scan` when a real
   text layer was present).

4. **Suggested label: `Force OCR → Vault`**, not `Scan → Vault`. "Scan → Vault" would teach the
   user to sort their own documents, which the pipeline now does better than they can.
   Category and icon unchanged: `category = "convert-scan"`, `icon = "🔍"`.

5. **No new status event type was added — `main.js` needs no change.** A probe reroute emits a
   normal `allocated` event with `dest: pipeline/convert-scan-inbox/…` (green ✓, same as W6's
   hop display); failures emit `rejected` (red ✗) as decided 2026-07-08.

## Also relevant

- The `rules.toml` rule for `convert-scan` matches `*.pdf` and `*.epub` only — no `.docx`
  (Pandoc has no OCR mode). A `.docx` dropped on the W7 tile will fall through to
  `sorted/misc/` as an ordinary unmatched allocation.
- Destination `pipeline/convert-scan-inbox/` is live on the ThinkPad as of L9 (2026-07-09).
