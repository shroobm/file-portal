# ThinkPad → Desktop: S78's research digest + new receipt fields to render

**From:** ThinkPad S78, 2026-08-16. **Read when:** next Desktop session opens.

## 1. New machine-readable surface you should render (docs/29 discipline)

The seam receipts (`receipts.jsonl`, the file you already tail) gained three things in S78,
all report-mode, all currently rendered by NOBODY on your side — which is SYM-027's shape
unless they get glass or a signed disposition:

- `exported` receipts may now carry **`spot_check: true`** — every 10th accepted export,
  flagged for Rab's eyes even though verdicts passed (FADGI 10-or-10% floor). Suggested
  surface: a distinct chip in the Room/Wall vault feed; the Bench's ◆ picker could offer it.
- `exported` receipts may carry **`degeneration_flagged: true`** — the linux lanes now run
  your calibrated zlib+trigram detector (ported byte-faithful from `fidelity_audit.py`,
  docs/15 §9.1 thresholds; if you recalibrate, tell this side — one calibration, two lanes).
  Full detail is in the bundle's `manifest.json` under `degeneration` (same shape as your
  `degeneration_detail`, so Bench zone code can read it unchanged).
- New outcome **`fixity-check`** `{result, tip, error?}` — weekly `git fsck` over the bare
  vault (NDSA level 3). A `fail` here outranks everything else in the file.

## 2. Research digest — Desktop-lane imports worth their own sessions

Three agent sweeps over US/CA/JP/CN/RU/LatAm pools; primary links inline. Filed here because
each lands in YOUR lane:

- **MinerU2.5 (Shanghai AI Lab)** conditions repetition penalties on detected layout — strict
  on prose, loose on tables — the decoding-side twin of your §9.2 AND-rule. Prevention to
  pair with your detection: https://arxiv.org/abs/2509.22186
- **ABBYY's verification model**: per-character/word confidence thresholds route only
  low-confidence spans to the human. The Bench triages whole zones today; span-level triage is
  the mature endpoint: https://www.abbyy.com/ocr-sdk/features/ocr/
- **Smart Engines / RAS (Bulatov)**: ROVER-style voting across recognition passes with
  expected-Levenshtein stopping — a rigorous "run both lanes and vote" for held books:
  https://arxiv.org/pdf/1910.04107
- **HathiTrust** runs a *post-publication* reopen loop (user reports → fix → re-ingest;
  6,499 volumes reported, >80% resolved). The vault has no path to reopen a blessed note;
  the repair ledger (docs/28) is the natural chokepoint to hang one on.
- **PP-OCRv6 (Baidu)** documents VLMs silently "correcting" the page (plausible text, wrong
  bytes) where small OCR models stay faithful — published support for the survival audit's
  whole premise, citable in docs/15: https://arxiv.org/abs/2606.13108
- **NDL Japan** accepted a 223M-page conversion via stratified per-category thresholds
  (median F ≥ 0.86 in ≥30/33 era×subject categories) — the grown-up version of per-lane
  thresholds if calibration ever stratifies further: https://lab.ndl.go.jp/data_set/ocr/r3_text/
- Vocabulary alignment, zero code: receipts ≅ PREMIS events (`ingestion`, `validation`,
  `fixity check`: https://id.loc.gov/vocabulary/preservation/eventType.html); bundles ≅ BagIt
  bags, whose **complete vs valid** two-tier verdict is a ready-made naming for staging-check
  vs bless (RFC 8493).

## 3. One number for Rab

`SPOT_CHECK_EVERY = 10` (module constant, `converter/exporter.py`). At ~7 ingests in six
weeks, the 10th accept is months out — FADGI's "whichever is LARGER" logic argues 3–5 at this
volume. His call; promote to converter.toml when he tunes it.
