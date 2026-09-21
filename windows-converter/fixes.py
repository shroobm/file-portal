# -*- coding: utf-8 -*-
"""fixes.py — LANE B, S211: THE FIXES AS LEVERS. Six mechanisms proved on copies in S210 (never on the

line), installed here as named, reversible patches a job can turn on by naming them in a lever file.
Nothing in this module runs unless `apply()` is called with the names to turn on — importing it alone
changes nothing.

Read first, copied faithfully (deviations noted inline where a deviation exists), from
C:/Users/Bndit/Projects/file-portal-private/sittings/S210/:
  - overlap_fix_proof.py      class FractionLineBuilder.check_line_overlaps, install_metric_patch()
  - lane_rule_census.py       the proposed lane rule (ratio > 0.5 OR OCR-font share >= 0.05)
  - degen_clause_proof.py     clause_blocks (<= 3 distinct non-space glyphs is a rule/leader, not a loop)
  - e5_notes.md ## 3, bill_glue_probe.py   SYM-160: the off-page duplicate pdftext keeps and dedup glues

GROUND for the pdftext internals (read, not assumed):
  C:/Users/Bndit/ml/marker-env/Lib/site-packages/pdftext/pdf/pages.py   get_pages, get_chars call site
  C:/Users/Bndit/ml/marker-env/Lib/site-packages/pdftext/pdf/chars.py   get_chars signature, char bbox convention
  C:/Users/Bndit/ml/marker-env/Lib/site-packages/marker/builders/line.py   LineBuilder.check_line_overlaps,
      get_detection_batch_size (CUDA 10 / else 4)
  C:/Users/Bndit/ml/marker-env/Lib/site-packages/marker/processors/table.py   get_table_rec_batch_size
      (CUDA 14 / mps 6 / else 6) — the task text's placeholder default of "8" for table_rec does NOT match
      what the installed marker ships; this module states the real defaults (see batch_sizes' docstring)
      and leaves the override values (4, 4) as Rab's proposed ceiling, not a claim about today's default.

Two already-committed integration points this module must interoperate with, found by reading (not
written by this lane, not edited by it — HARD RULE 1):
  - convert_and_ship.py lines 384-389 and roots.json "fixes" (S211, committed 9a5fab3): the lever file
    FIXES_FILE ("fixes.txt" under the pipeline root) is documented there as `for: <drop file name>` on
    its first line, then one fix name per line. read_lever() below tolerates that header line (skips it,
    like a comment) so the file the rest of the system already writes parses without error; it does NOT
    itself decide whether the file belongs to the current job — that job-name match is the integrator's
    job, done before it hands this path to read_lever (see the report for where).

Persisted keys used by this module (LITERAL strings only, per HARD RULE 4):
  manifest keys   "fixes", "fixes_stats"
  config keys     "detection_batch_size", "table_rec_batch_size"
  env var         FP_FIXES (see apply())
"""
from __future__ import annotations

import io
import math
import os
import re

# ---------------------------------------------------------------------------------------------------
# FIXES — the literal, closed set of lever names. Nothing outside this tuple is a valid name anywhere
# in this module (read_lever and apply both refuse an unknown name against exactly this tuple).
# ---------------------------------------------------------------------------------------------------
FIXES = (
    "overlap-fraction-gate",
    "charbox-lift",
    "offpage-clip",
    "lane-share-rule",
    "degen-rule-line",
    "table-batch-ceiling",
    "ligature-repair",   # S211 Lane C: SYM-148's repair pass (ligature_repair.py), run by convert() before the audit
)

_FOR_LINE = re.compile(r"^for\s*:", re.IGNORECASE)


def read_lever(path) -> list:
    """Read a lever file: one fix name per line, order kept, duplicates dropped.

    Ignored, not names: blank lines; lines starting with '#'; a line starting with 'for:' (the
    FIXES_FILE job-scoping header already committed in convert_and_ship.py/roots.json — see the module
    docstring; this function skips it exactly like a comment and does not itself check which job it
    names). A missing file returns []. Any other line that is not one of FIXES raises ValueError naming
    the offending line.
    """
    path = os.fspath(path)
    if not os.path.isfile(path):
        return []
    names = []
    seen = set()
    with io.open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or _FOR_LINE.match(line):
                continue
            if line not in FIXES:
                raise ValueError("fixes.read_lever: unknown fix name %r in %s" % (line, path))
            if line not in seen:
                seen.add(line)
                names.append(line)
    return names


# ---------------------------------------------------------------------------------------------------
# overlap-fraction-gate — copied faithfully from overlap_fix_proof.py's FractionLineBuilder.
# check_line_overlaps is unchanged line-for-line from the S210 proof (it touches no `self` attribute,
# so it is safe to call unbound in the selftest, the same way the proof's `--control` path calls the
# stock LineBuilder unbound for comparison).
#
# Imported eagerly (not deferred): fixes.py is only ever imported from marker_blocks.py, which is only
# ever imported from convert_and_ship.py, which the repo's own docstring runs exclusively under
# marker-env ("Run with the marker-env interpreter", convert_and_ship.py line 8) — so there is no real
# call path where fixes.py must import without marker/torch on the path. Kept as one real class (not a
# lazy proxy) so `fixes.FractionLineBuilder` is exactly what
# `marker.converters.pdf.LineBuilder = fixes.FractionLineBuilder` needs, and what the selftest
# subclasses/calls unbound, with a single copy of check_line_overlaps.
# ---------------------------------------------------------------------------------------------------
FRACTION = 0.5

import numpy as np  # noqa: E402
from marker.builders.line import LineBuilder  # noqa: E402
from marker.util import matrix_intersection_area  # noqa: E402


class FractionLineBuilder(LineBuilder):
    """check_line_overlaps as a FRACTION of the line's own box (the stock test compares an absolute
    area in pt² to 0.1) — copied from overlap_fix_proof.py verbatim."""

    def check_line_overlaps(self, document_page, provider_lines) -> bool:
        boxes = [ln.line.polygon.bbox for ln in provider_lines]
        page_bbox = document_page.polygon.expand(5, 5).bbox
        for b in boxes:
            if b[0] < page_bbox[0] or b[1] < page_bbox[1] or b[2] > page_bbox[2] or b[3] > page_bbox[3]:
                return False
        if not boxes:
            return True
        m = matrix_intersection_area(boxes, boxes)
        areas = np.array([max(1e-6, (b[2] - b[0]) * (b[3] - b[1])) for b in boxes])
        frac = m / areas[:, None]
        for i in range(len(boxes)):
            if int(np.sum(frac[i] > FRACTION)) > 2:
                return False
        return True


def _install_overlap_gate(log):
    import marker.converters.pdf as mcp

    if getattr(mcp, "LineBuilder", None) is FractionLineBuilder:
        return
    mcp.LineBuilder = FractionLineBuilder
    log("fixes: overlap-fraction-gate installed (marker.converters.pdf.LineBuilder -> FractionLineBuilder, fraction %.2f)" % FRACTION)


# ---------------------------------------------------------------------------------------------------
# charbox-lift / offpage-clip — both wrap pdftext.pdf.pages.get_chars (the name pdftext's own get_pages
# calls unqualified, so patching it here is patching the call site — same pattern as
# overlap_fix_proof.py's install_metric_patch(), which patches this exact name). Composed in ONE
# wrapper chain, clip first then lift, installed at most once (idempotent — see _STATE).
# ---------------------------------------------------------------------------------------------------
_STATE = {
    "get_chars_installed": False,
    "clip_on": False,
    "lift_on": False,
    "overlap_on": False,
    "stats": {"chars_seen": 0, "chars_dropped": 0, "chars_lifted": 0},
}


def _clip_offpage_chars(chars, page_bbox, stats):
    """SYM-160's fix (e5_notes.md ## 3 / bill_glue_probe.py): drop chars whose bbox lies WHOLLY outside
    [-1, -1, width+1, height+1] before dedup — the off-page duplicate column pdfium keeps and MuPDF
    would have clipped. `ch["bbox"]` here is already the page-local, y-flipped box pdftext's own
    get_chars produced (pages.py get_chars: cx -= x_start, ty = page_height - cy), so width/height are
    computed the same way pages.py computes them from page_bbox."""
    x_start, y_start, x_end, y_end = page_bbox
    width = math.ceil(abs(x_end - x_start))
    height = math.ceil(abs(y_end - y_start))
    lo_x, lo_y = -1.0, -1.0
    hi_x, hi_y = width + 1.0, height + 1.0
    kept = []
    for ch in chars:
        b = ch["bbox"].bbox
        if b[2] < lo_x or b[0] > hi_x or b[3] < lo_y or b[1] > hi_y:
            stats["chars_dropped"] += 1
            continue
        kept.append(ch)
    return kept


def _lift_charboxes(textpage, chars, page_bbox, page_rotation, stats):
    """install_metric_patch()'s get_chars_metric, copied faithfully (pdftext.schema.Bbox import moved
    to module scope below; variable names otherwise unchanged): a char's LOOSE box (the font's
    ascent/descent, what pdftext keeps) is lifted to clear its own tight ink box when the loose box's
    top sits more than 0.3 × size below the ink — no font name, general rule."""
    from pdftext.schema import Bbox

    if page_rotation != 0:
        return chars
    x_start, y_start, x_end, y_end = page_bbox
    page_height = math.ceil(abs(y_end - y_start))
    for ch in chars:
        if ch.get("rotation", 0) != 0:
            continue
        i = ch["char_idx"]
        tx0, ty0, tx1, ty1 = textpage.get_charbox(i, loose=False)
        t_top = page_height - (max(ty0, ty1) - y_start)
        t_bot = page_height - (min(ty0, ty1) - y_start)
        if t_bot - t_top <= 0.1:  # a space or an empty glyph: no ink to trust
            continue
        b = list(ch["bbox"].bbox)
        size = max(float(ch["font"].get("size") or 0), b[3] - b[1])
        if t_top < b[1] - 0.3 * size:  # the ink's top is well ABOVE the loose box's top
            d = (b[1] - t_top) + 0.15 * size
            ch["bbox"] = Bbox([b[0], b[1] - d, b[2], b[3] - d])
            stats["chars_lifted"] += 1
    return chars


def _install_get_chars(log):
    import pdftext.pdf.pages as pp

    if _STATE["get_chars_installed"] and getattr(pp.get_chars, "_fp_fixes_wrapper", False):
        return
    orig = pp.get_chars
    stats = _STATE["stats"]

    def _wrapped_get_chars(textpage, page_bbox, page_rotation, quote_loosebox=True):
        chars = orig(textpage, page_bbox, page_rotation, quote_loosebox)
        stats["chars_seen"] += len(chars)
        if _STATE["clip_on"]:
            chars = _clip_offpage_chars(chars, page_bbox, stats)
        if _STATE["lift_on"]:
            chars = _lift_charboxes(textpage, chars, page_bbox, page_rotation, stats)
        return chars

    _wrapped_get_chars._fp_fixes_wrapper = True
    pp.get_chars = _wrapped_get_chars
    _STATE["get_chars_installed"] = True
    log("fixes: pdftext.pdf.pages.get_chars wrapped (clip=%s, lift=%s)" % (_STATE["clip_on"], _STATE["lift_on"]))


# ---------------------------------------------------------------------------------------------------
# lane-share-rule — lane_rule_census.py's proposed rule, copied faithfully as a pure function.
# ---------------------------------------------------------------------------------------------------
SHARE = 0.05


def lane_rule(invisible_ratio: float, ocr_font_spans: int, total_spans: int) -> bool:
    """True = scan lane. `share = ocr_font_spans / total_spans if total_spans else 0.0`; scan when
    invisible_ratio > 0.5 OR share >= SHARE (0.05) — lane_rule_census.py's `proposed` column."""
    share = (ocr_font_spans / total_spans) if total_spans else 0.0
    return invisible_ratio > 0.5 or share >= SHARE


# ---------------------------------------------------------------------------------------------------
# degen-rule-line — degen_clause_proof.py's clause_blocks() skip test, copied faithfully as a pure
# function (the trigram/zlib pass around it stays fidelity_audit's; this is only the ONE clause).
# ---------------------------------------------------------------------------------------------------
_WS = re.compile(r"\s")


def is_rule_line(paragraph: str) -> bool:
    """True when the paragraph (after strip()) has <= 3 distinct non-space glyphs: a rule or a
    leader, not a decoder loop — degen_clause_proof.py: `len(set(re.sub(r"\\s", "", p))) <= 3`."""
    p = (paragraph or "").strip()
    return len(set(_WS.sub("", p))) <= 3


# ---------------------------------------------------------------------------------------------------
# table-batch-ceiling — a PROPOSAL (Rab's signature on the threshold and the lowered numbers), not a
# proof-on-copy like the other five. Marker's real defaults, read (not assumed) from the installed
# package:
#   marker/builders/line.py    LineBuilder.get_detection_batch_size(): None -> 10 if TORCH_DEVICE_MODEL
#                               == "cuda" else 4
#   marker/processors/table.py TableProcessor.get_table_rec_batch_size(): None -> 6 if "mps", 14 if
#                               "cuda", else 6
# This machine's only card is an RTX 3080, 10 GB (desktop-machine.md, S46 measurement) — CUDA is the
# real default path here, so the un-overridden run sits at detection=10, table_rec=14. The lowered
# ceiling below (4, 4) is Rab's proposed floor under memory pressure, not a claim about what Marker
# ships by default.
# ---------------------------------------------------------------------------------------------------
_DEFAULT_TOTAL_MIB = 10240  # fallback only, used when nvidia-smi cannot be queried (Observed: RTX 3080
# 10 GB is this machine's only card, desktop-machine.md S46 measurement — not re-measured by this module)
_LOW_FREE_FRACTION = 0.15
_LOWERED_BATCH = {"detection_batch_size": 4, "table_rec_batch_size": 4}


def _card_total_mib():
    try:
        import subprocess

        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0 and out.stdout.strip():
            return int(out.stdout.strip().splitlines()[0].strip())
    except Exception:  # noqa: BLE001 - no card, no driver, no nvidia-smi on PATH: fall back
        pass
    return _DEFAULT_TOTAL_MIB


def batch_sizes(free_mib) -> dict:
    """Marker config overrides, lowered only when the card's free memory is under 0.15 of its total;
    {} otherwise (including when free_mib is None: an unmeasured card gets no override, never a guess)."""
    if free_mib is None:
        return {}
    total = _card_total_mib()
    if not total:
        return {}
    if free_mib < _LOW_FREE_FRACTION * total:
        return dict(_LOWERED_BATCH)
    return {}


# ---------------------------------------------------------------------------------------------------
# apply() / manifest_record() — the module's two entry points for the integrator.
# ---------------------------------------------------------------------------------------------------

def apply(names, log=print) -> dict:
    """Install the named fixes, idempotently. Returns {"applied": [...], "stats": {...}}.

    "overlap-fraction-gate" sets marker.converters.pdf.LineBuilder = FractionLineBuilder.
    "charbox-lift" and "offpage-clip" both wrap pdftext.pdf.pages.get_chars in ONE chain (clip, then
    lift) — calling apply() again (with the same or a different subset) never adds a second wrapper
    layer, it only flips which stage(s) the existing wrapper runs.
    "lane-share-rule", "degen-rule-line" and "table-batch-ceiling" are pure functions the integrator
    calls directly (probe(), fidelity_audit._degenerate_blocks, and the converter's config build,
    respectively) — apply() records them as active and, for fidelity_audit's process boundary, exposes
    the FP_FIXES env var (comma-joined literal fix names) as the proposed signal it reads (see the
    report's fidelity_audit diff for why an env var and not a function argument).
    """
    names = list(names)
    for n in names:
        if n not in FIXES:
            raise ValueError("fixes.apply: unknown fix name %r" % (n,))

    applied = []
    for n in names:
        if n == "overlap-fraction-gate":
            _install_overlap_gate(log)
            _STATE["overlap_on"] = True
            applied.append(n)
        elif n == "charbox-lift":
            _STATE["lift_on"] = True
            _install_get_chars(log)
            applied.append(n)
        elif n == "offpage-clip":
            _STATE["clip_on"] = True
            _install_get_chars(log)
            applied.append(n)
        elif n in ("lane-share-rule", "degen-rule-line", "table-batch-ceiling", "ligature-repair"):
            applied.append(n)   # pure functions / passes the integrator calls where they apply; recorded as active

    if applied:
        prior = os.environ.get("FP_FIXES", "")
        merged = sorted(set(prior.split(",")) | set(applied)) if prior else sorted(set(applied))
        try:
            os.environ["FP_FIXES"] = ",".join(n for n in merged if n)
        except Exception:  # noqa: BLE001 - a frozen/locked env must never fail the job over this
            pass

    log("fixes: applied %s" % (applied,))
    return {"applied": applied, "stats": dict(_STATE["stats"])}


GET_CHARS_FIXES = ("charbox-lift", "offpage-clip")


def config_overrides(applied) -> dict:
    """Marker config overrides a set of applied fixes requires. S211 CORRECTIONS row 5: the get_chars wrapper is installed in
    THIS process, and pdftext reads a book over WORKER_PAGE_THRESHOLD (10) pages in spawned workers that import pdftext fresh
    and unpatched — so any get_chars fix keeps the provider in-process with pdftext_workers 1 (the proofs' own setting).
    Nothing applied, or none of the get_chars fixes → {} (the stock worker count)."""
    if any(n in GET_CHARS_FIXES for n in applied):
        return {"pdftext_workers": 1}
    return {}


def stats() -> dict:
    """The wrapper chain's LIVE counters (chars_seen, chars_dropped, chars_lifted) — apply() returns a snapshot at
    install time (zeros); the record wants the count after the document was read. A copy, never the dict itself."""
    return dict(_STATE["stats"])


def manifest_record(names, stats) -> dict:
    """{"fixes": [...], "fixes_stats": {...}} for the bundle manifest — the literal list of names
    actually applied and the wrapper's own counters, exactly as apply() returned them."""
    return {"fixes": list(names), "fixes_stats": dict(stats)}
