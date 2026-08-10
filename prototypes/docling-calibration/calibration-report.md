# Calibration Report — granite-docling-258M on DESKTOP-BNDIT (S71, 2026-08-10)

**Method:** the S28→S30 tradition — measured on the real corpus before any trust. 13 samples +
one live Bench proof, `results.jsonl` beside this file (fsync'd per row — which is why the data
survived the night's crash, below). Tags: [M] measured here · [I] inferred.

## Movement (bf16, RTX 3080 10 GB, dpi 144 page / 220 crop)

| scope | sample class | s/sample | torch peak | notes |
|---|---|---|---|---|
| page | sparse (dividers, low-text) | 3.5 | 963 MiB | output-bound: little text, instant |
| page | dense prose (claudecode p5) | 85.4 | 963 MiB | window survival **0.857** exact-floor, numeric J 0.5 |
| page | figure pages (cybernetics) | 28.7–61.1 | 748 MiB | survival 0.16–0.61 — figures aren't text |
| page | dense finance table (damodaran p100) | 149.4 | 963 MiB | **real `<otsl>` table emitted · numeric J 0.9688** |
| crop | sparse bands | 2.0–2.5 | 642–748 MiB | |
| crop | dense TABLE bands (damodaran p100/p400) | 84.5–182.1 † | 750 MiB | **numeric J = 1.0 on BOTH** · p400 emitted a table |
| crop | degraded-scan band (valentine p150) | 320.8 † | 852 MiB | 3,518 DocTags chars → **md 0 = unparseable ⇒ the refusal gate fires** (by design) |
| **crop** | **LIVE Bench zone (G5: real Damodaran zone 1 → p396)** | **90.6 (+4.5 load), uncontended** | 857 MiB | **parse ✓ · table ✓ · numeric J 0.95 · applied · undo byte-identical** |

† measured while TWO calibration processes contended for the GPU (see incidents) — treat as
upper bounds; the uncontended G5 figure (90.6 s) is the honest dense-crop anchor.

**Decode is output-bound (~10 tok/s effective):** the clock follows how much text the region
holds, not how big the image is. Model load: 2.5 s warm / ~10 s cold. fp16: **rejected live** —
the first fp16 page never terminated (no-EOS degeneration class), tree-killed; **bf16 pinned**.

## Verdicts

1. **Document scope: REFUSED on this card.** Dense pages at 85–149 s/pp ⇒ tens of hours per
   book (Marker: 1.4–8.1 s/pp measured). The docs/24 engine-lever question is answered: the
   document lane stays Marker's.
2. **Zone scope: BUILT (the Bench's ⌨ transcribe).** Sparse crops seconds; dense table crops
   ~90 s uncontended with the UI's live clock keeping the wait honest; on the SYM-003 wound the
   reader emits real table structure and conserved **95–100% of numeric tokens** in every
   measured table sample.
3. **Degraded scans refuse rather than lie** — the valentine crop's unparseable read exits
   through ok=false into the ✂ image-embed floor. Surya keeps the scan lane.
4. **Page scope (29–149 s per flagged page): open middle** — plausible for a future per-page
   remedy; not built, not signed.

## Incidents (all recorded in SYMPTOM-INDEX + the S71 closeout)

- **fp16 no-EOS hang** → tree-killed; dtype pinned bf16.
- **The chained-kill gap:** killing the running python of a `cmd1; cmd2` background chain does
  not cancel cmd2 — the orphaned second batch ran concurrently with the trimmed rerun.
- **VIDEO_SCHEDULER_INTERNAL_ERROR → reboot:** under two model processes + a lived-in desktop,
  the display driver faulted and Windows restarted. Zero data lost (fsync per row; all work
  files intact). Law extended: **one lab process on the card, ever** — the serialization law is
  a machine law, not just a pipeline law.

## Limitations

Middle-band synthetic crops (a human picks real zones — G5's live zone covers the gap); exact
window survival is a fuzzless floor (real audit adds anchored fuzzy); n is the factory's six
books, not a benchmark.
