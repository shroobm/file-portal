"""P-1 — figure coverage: did the figures on each source page reach the output?

docs/41 §2 P-1, signed by Rab 2026-08-20 ("lets do items 6-9" / "lets do P-1"). Built S102.

WHAT THIS ANSWERS, precisely
    For every page of the source PDF that bears at least one figure-like region, does the
    converted bundle contain at least one figure asset attributed to that page?
    Numerator: source pages bearing >=1 figure region that have 0 output assets on that page.
    Denominator: source pages bearing >=1 figure region.
    Conditions: named per run in the report (pymupdf version, thresholds, bundle, lane).

WHAT IT DOES NOT ANSWER, and why
    docs/41 specified coverage by BBOX OVERLAP — "does each source figure region have some
    output image whose bbox overlaps it". That is not computable on this stack, measured S102:
    a shipped bundle is `<name>.md` + `assets/` + `manifest.json`, and marker's markdown-mode
    `_meta.json` carries only `table_of_contents` + `page_stats` (renderers/__init__.py:117)
    — no block bboxes anywhere. Output bboxes exist only under a different output format or
    the Python API, i.e. a converter rewrite. So coverage here is PER PAGE, which is the
    honest buildable unit, and a page with three source figures and one output asset counts
    as COVERED. That is a real ceiling on sensitivity and is printed in every report.

WHY COUNTS ARE NOT COVERAGE (the trap this instrument exists to avoid)
    The existing `asset_delta` compares two different KINDS of object: files marker wrote by
    cropping the rendered page, versus image XObjects in the source. A 465-page scan reads
    -416 because OCR worked; a vector-figure book reads +92 against ZERO XObjects. Neither is
    figure loss. This module never compares counts: it asks a per-page presence question, and
    it treats vector drawings as first-class figures because on this corpus they are the
    common case (Cybernetics: 0 raster XObjects, 92 figures).

REPORT-ONLY BY DOCTRINE
    docs/15 §6: all thresholds ship report-only until calibrated; §9 step 3: the tool must show
    its false alarms verbatim before it may pulse terracotta. This module returns a report and
    NOTHING ELSE. It writes no manifest key, sets no verdict, and is deliberately not wired
    into convert_and_ship.py — placement is Rab's open decision (docs/41 §2 P-1, variable 4).

KNOWN LIMITATIONS, measured rather than guessed (S104)
    · **Zero-area paths are dropped before clustering** (`:300`, `if _rect_area(r) <= 0`). A pure
      horizontal or vertical connector line has no area, so it never joins the boxes it connects.
      A flow diagram whose boxes sit further apart than VECTOR_CLUSTER_GAP_PT can therefore
      fragment into several sub-threshold regions and be MISSED entirely. **S105: no longer
      theoretical — two MEASURED specimens, SYM-049.** Cyb p34 (54 drawings, 27 of them zero-area,
      12 fragments, largest 541 pt² vs MIN_AREA_PT2 4900) and Cyb p78 (2 clusters of 2 paths vs
      VECTOR_MIN_PATHS 4). Neither shipped an asset; P-1 is silent on both. Control that proves
      the mechanism: p35's visually-similar diagram DOES flag, because it contains one curved
      path with non-zero area. Not fixed: the fix is clustering that follows stroke geometry.
      **S157 E25 (2026-09-15): FIXED by the smaller move — a zero-area path is clustered when it
      is ANCHORED (within the gap of a positive-area path or a perpendicular line; see
      `_anchored_lines`), so a connector joins what it connects and a stack of bare rules still
      does not. Measured on every anchor (private `sittings/S157/e25/anchors_diff.json`): the
      Book of Models gains exactly p.34 and p.78 as uncovered (1 -> 3) and nothing else moves on
      any book (IV: 0 zero-area paths; DDIA: 572 clustered, all on raster pages already flagged).**
      **CORRECTED S157 E39 (a verifier lane, V1-06): the E25 residue said Cyb p.40 (a rectilinear
      thermostat chart) "still reads as a table". It does not: under the shipped code its 46 anchored
      lines bring the axis arrows into one 54-path cluster with 6 non-rectilinear items, the table veto
      is disqualified, and p.40 is REPORTED — the book's vetoed-table count after the change is 0, as
      the anchors diff said all along; the residue had read the PRE-change probe. No rectilinear-chart
      residue is known on the measured corpus.**
    · **A regular grid of labelled boxes reads as a table** to `find_tables()` and is vetoed.
      ~~Org charts and matrix diagrams are the risk class.~~ **S105 CORRECTION: this class was
      called "not measured on a real specimen" and it had in fact already fired 15 times in the
      S104 corpus run. On Cybernetics the table veto is 0-for-11 — it removed a Watt steam-engine
      illustration (p26), a time-series line chart (p44) and a Pask conversation diagram (p74),
      each reported by find_tables() at 99.5-100 % table coverage. ZERO real tables among them.
      The class is broader than "grids of boxes": any axis-tick chart or shaded technical drawing
      can trip it. No loss resulted (all 11 shipped anyway) — this costs SENSITIVITY, and it is
      the same page-class as the p34/p78 losses above.**
      **S157 E25: the veto is DISQUALIFIED for a non-rectilinear cluster (`_nonrect_items` >=
      VETO_TABLE_MAX_NONRECT sizable curves + diagonals). Measured over every (cluster, vetoing
      table) pair on the vector anchors: Book of Models 14 of 15 pairs non-rectilinear (every one
      a diagram: the engine, the time series, the room), Investment Valuation 0 of 144 (every one
      a ruled table; p.944's 112 bullet glyphs are 2 pt circles, under the span). After: the Book
      of Models' vetoed-table count 15 -> 0 and its figure pages 57 -> 71, all fourteen covered.**
    · **Damodaran's "ILLUSTRATION N.N" frames still survive all three vetoes** (p63, p73): the
      frame is clustered as one region, the table inside covers ~21 % of it and the prose ~32 %,
      totalling 0.53 against a 0.60 threshold. Catching them needs 0.50 — which would be
      tuning to a sample of two with no held-out set — or the real fix, which is clustering
      that does not let a frame border swallow its contents.
      **S157 E35 (2026-09-15): CALIBRATED, not tuned.** The veto's own number, accounted =
      min(1, text_coverage + covered_frac(tables)), measured on 104 uncovered vector regions
      that two Sonnet readers had adjudicated NOT figures (every uncovered vector page of the
      two Investment Valuation bundles — all ILLUSTRATION boxes) against 203 surviving vector
      regions on the diagram books (Book of Models 90, Ashby 8, DDIA 105 — figures or figure
      frames, every one covered by its asset): boxes min/median/max 0.025 / 0.448–0.449 (the two middle values of 104) / 0.595,
      figures 0.0 / 0.0 / 0.269. A lever line `accounted_for=0.35` would veto 63 of the 104
      boxes and hide 0 of the 203 figures, with 0.08 of margin over the figures' maximum;
      0.30 vetoes 80 and hides 0 with 0.03 of margin; 0.25 hides two (Cyb p.81, Ashby p.126).
      The default stays 0.60 — the value is the operator's line (private
      `sittings/S157/e35/frame_probe.json`). The 41 boxes under 0.35 are mostly-empty frames
      (a heading and a paragraph over blank space, e.g. IV UE p.805/940/945): no text-density
      threshold reaches them; the region kind does — see `uncovered_by_kind`.
    · **On the adjudicated Damodaran corpus the region KIND is the verdict (S157 E24/E30):**
      every uncovered page whose regions were raster was a lost figure (21 of 21 across both
      bundles — absent or flattened into a table/prose) and every vector-only uncovered page was
      an ILLUSTRATION box, not a figure (104 of 104). The report's `uncovered_by_kind` counts
      them; read a vector-only uncovered page on this typesetting as a box until a reader says
      otherwise. Not a rule for diagram books, where vector IS the figure.
    · **THE VERDICT IS ONLY AS GOOD AS THE BUNDLE'S PAGE MAP (S105, SYM-050).** On a pre-S60
      doubled-offset bundle every per-page verdict is noise: the figures ARE in the bundle,
      filed under doubled ids. Measured on Investment Valuation — **19 of 20 adjudicated
      "uncovered" verdicts FALSE**. `assets_out_of_range` catches the gross case and is NOT
      sufficient: IV p191's asset id 189 is in range and still misattributed by one.
      **Refuse to quote a per-page number from any bundle that trips that flag.**
      **S108 (A18): the S106 map repair is now WIRED.** When the FULL doubled-offset signature
      matches (`sym050_signature` — not bare out-of-range), the map is repaired IN MEMORY
      (`true_page = id + 1 - 200*(id//400)`, confirmed four independent ways at S106) and the
      report leads with the repaired numbers, the unrepaired numbers printed beside for
      continuity. Bundle files are never modified. Bare out-of-range without the signature
      still only warns — in the JSON payload too, which S104's harvest never saw.
    So: this instrument's DETECTION is good — 13.3 % false alarms at the region level (2/15
    sampled on IV, S105) — and its per-page VERDICT is only as trustworthy as the bundle. It is
    NOT "trustworthy on small born-digital books": Cybernetics is exactly that and it is missing
    at least two figures P-1 cannot see. It is BLIND on the scan lane by construction — and that
    blindness renders as `with source figures 0 · UNCOVERED 0`, indistinguishable from a clean
    bill of health, on a book whose bundle carries 63 assets across 62 pages.

COST, per docs/34 (numerator: wall seconds; denominator: pages_total; conditions named)
    Measured S105 on the SHIPPED build, PyMuPDF 1.28.0, warm FS, CPU-only, one process per book:
    Investment Valuation 1356 pp -> **37 ms/page** · Cybernetics 91 pp -> **72 ms/page** ·
    BRAIN OF THE FIRM (scan) 439 pp -> 4.6 ms/page. `find_tables()` is 7-10x of that total.
    **S104's "5.6 ms/page" was the PRE-TABLE-VETO build** (ablation: 5.21 ms/page on IV with
    `_table_rects` stubbed) — i.e. the cost of the configuration that was NOT shipped.

CPU-only. Never touches the GPU; safe to run beside a conversion.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pymupdf

# ── thresholds, all in POINTS (72/inch), all named in the report ───────────────
# A "figure region" must be big enough to be a figure a reader would miss. These are first
# guesses, deliberately conservative, and CALIBRATION (docs/15 §9) is what earns them.
MIN_AREA_PT2 = 4900.0  # 70x70pt ~= 1x1 inch. Smaller marks are bullets, glyph art, rules.
MIN_SIDE_PT = 40.0  # a figure is not 3pt tall; kills rules, underlines, table borders
MAX_PAGE_FRACTION = 0.92  # a region covering ~the whole page is the SCAN ITSELF, not a figure
VECTOR_MIN_PATHS = 4  # a cluster needs real drawing activity, not one stray line
VECTOR_CLUSTER_GAP_PT = 18.0  # paths closer than this merge into one figure region
# S157 E25 (SYM-049): a zero-area path — a connector line, an arrow shaft, an axis — is CLUSTERED, not dropped, when it
# is ANCHORED: within the gap of a positive-area path or of a zero-area line of the other orientation. A stack of
# parallel rules (underlines, a ruled form) touches neither and stays out, so the min-side/min-area filters keep their
# S104 meaning. Measured before the change on the Book of Models: p.34 (27 arrow shafts each touching only its own
# 5x10 pt arrowhead — 12 fragments, largest 541 pt²) and p.78 (two boxes joined by two lines — 2 clusters of 2 paths)
# were invisible; with anchored lines both cluster past every size filter (E25's probe, `sittings/S157/e25_lines_probe.py`).
ZERO_AREA_MIN_LEN_PT = 1.0  # a zero-area path shorter than this is a dot, not a line. lever-waiver: none owed — this is the DEFAULT of the lever `zero_area_min_len_pt` in LEVER_SPEC (the operator's line moves it; its ceiling restores S104's drop — selftest case 38)
# S157 E25: the table veto is DISQUALIFIED for a cluster that is not rectilinear — a ruled table is lines and rects; a
# diagram has curves and diagonals. Counted over the drawings inside the cluster: curve items whose control points span
# >= NONRECT_MIN_SPAN_PT (a bullet glyph is a 2 pt circle — IV p.944 draws 112 of them inside a real table) and line
# items with both dx and dy >= 0.5 pt and length >= NONRECT_MIN_SPAN_PT. Measured on every (cluster, vetoing table)
# pair of the vector anchors (`sittings/S157/e25_curves_probe.py`): the Book of Models 14 of 15 pairs non-rectilinear
# (S105's 0-for-11 class: a Watt engine, a time series, a room in perspective — every one a diagram), Investment
# Valuation 0 of 144 (every one a ruled table). The threshold sits between 2 (Cyb p.40's two diagonals) and 8 (the
# smallest diagram, Cyb p.74/75/77: 4 curves + 4 diagonals).
VETO_TABLE_MAX_NONRECT = 3  # a cluster with this many sizable curves+diagonals is a drawing; no table may veto it. lever-waiver: none owed — the DEFAULT of the lever `table_max_nonrect` in LEVER_SPEC; set S157 E25 between 2 (Cyb p.40's two diagonals) and 8 (the smallest diagram); moves on a re-measured (cluster, table) census
NONRECT_MIN_SPAN_PT = 4.0  # lever-waiver: none owed — the DEFAULT of the lever `nonrect_min_span_pt` in LEVER_SPEC; set S157 E25 above a bullet glyph's 2 pt circle (IV p.944 draws 112) and under the smallest diagram stroke measured; moves on a re-measured census

# ── the text-density veto (S104) ──────────────────────────────────────────────
# A shaded callout box and a flow diagram both cluster into a big vector region. The box is
# PROSE in a frame; the diagram is a picture with sparse labels. Thresholds were chosen AFTER
# measuring the two known specimens, not before:
#
#   Investment Valuation p45 (sidebar, FALSE positive): coverage 0.731 · 9.25 words/line
#   Cybernetics p84 (Du Pont diagram, TRUE positive)  : coverage 0.050 · 3.38 words/line
#
# Note what does NOT discriminate: line count (32 vs 29). The obvious metric is useless here.
# Both conditions must hold to veto, which biases toward KEEPING regions — a missed veto costs
# one false alarm, a wrong veto hides a real lost figure, and those are not symmetrical.
VETO_TEXT_COVERAGE = 0.35   # sidebar 0.731 (2.1x above) · diagram 0.050 (7x below)
VETO_WORDS_PER_LINE = 6.0   # sidebar 9.25 · diagram 3.38

# The prose veto alone was not enough, measured S104: it cut Investment Valuation's flagged
# pages 706 -> 477, and the survivors were dominated by TABLES ("ILLUSTRATION 2.1" boxes
# wrapping shaded tables). A table is not prose and not a figure — on both prose metrics it
# looks exactly like a diagram (p63: 4.76 words/line, coverage 0.319; the Du Pont diagram:
# 3.38 and 0.050). So the discriminator cannot be text shape at all; it has to be structure.
# MuPDF's own table finder separates them cleanly and cheaply:
#   IV p63 -> 1 table · IV p73 -> 1 table · Cybernetics p84 (the diagram) -> 0 tables
# It costs ~0.1 s/page and is therefore computed ONCE per page and only when a vector region
# has already survived every cheaper filter.
VETO_TABLE_OVERLAP = 0.5    # a region at least half-covered by a detected table is a table
# And the case both of the above still missed, measured S104: Damodaran's "ILLUSTRATION N.N"
# boxes. The clustering merges the outer FRAME with everything inside it into one region, so
# the table sits at ~40 % of that region and never trips VETO_TABLE_OVERLAP, while the prose
# test sees short table cells (4.5 words/line) and lets it through. Neither veto is wrong; the
# REGION is wrong — it is a frame, not an object. Rather than re-tune either threshold, ask
# the question that actually decides it: is this region's area ACCOUNTED FOR by text and
# tables? If almost all of it is, there is no picture in there.
# CORRECTED S105 2026-08-21 (re-measured; the line below previously read ".40 = .72" / ".38 = .72",
# which contradicted this file's own KNOWN LIMITATIONS block and overstated the table fraction by
# ~0.19. Anyone tuning this constant off the old numbers would conclude 0.60 already catches the
# frame class. It does not — that is why p63/p73 survive):
#   IV p63: text .319 + table .209 = .528   IV p73: .336 + .186 = .522   Cyb p84: .050 + 0 = .050
VETO_ACCOUNTED_FOR = 0.60

# ---------- the levers (signed Rab, S106, 2026-08-21; docs/18 §2 modularity law) ----------
#
# His words: "determine if it's a feature deep work, or it should have the capability to be
# modular, and change in numbers from an operator."
#
# Every number above decides what a human is shown, so by docs/18 §2 every one of them is a
# LEVER, not a constant. They keep their values as DEFAULTS; the operator's file overrides.
# Same contract as `convert_and_ship.chunk_batch()`: anything unparseable or out of range
# falls back to the default rather than running on a number nobody chose — and the EFFECTIVE
# values are reported in the report's `conditions`, so a number never travels without its
# configuration attached (docs/34, and S105's Family-1 finding: the sentence must name the probe).
#
# The TRIAGE lever is the one Rab signed by name. Measured S106 on Investment Valuation with a
# repaired page map: unfiltered precision 2/12 sampled = 16.7 %; restricted to pages carrying a
# FIGURE N.N caption, 5/6 adjudicated = 83 %. It changes what is REPORTED FIRST, never what is
# detected — the full list is always present, so triage can never hide a page.
LEVER_FILE = Path(r"C:\Users\Bndit\ml\library\figure-triage.txt")
TRIAGE_ALLOWED = ("caption", "off")
LEVER_SPEC: dict[str, tuple[type, object, object]] = {
    #  key                  type    default                 admissible range (inclusive)
    "mode":               (str,   "caption",              TRIAGE_ALLOWED),
    "min_area_pt2":       (float, MIN_AREA_PT2,           (100.0, 100_000.0)),
    # S157 E18 (B14): the two filters that could silently null a min_area_pt2 change are levers too, at their old constants
    "min_side_pt":        (float, MIN_SIDE_PT,            (1.0, 400.0)),
    "max_page_fraction":  (float, MAX_PAGE_FRACTION,      (0.10, 1.0)),
    "vector_min_paths":   (int,   VECTOR_MIN_PATHS,       (1, 200)),
    "cluster_gap_pt":     (float, VECTOR_CLUSTER_GAP_PT,  (0.0, 200.0)),
    # S157 E25: the two mechanisms measured that episode, each with the lever that turns it back into the S104 behaviour
    # (zero_area_min_len_pt above any page height = no line is ever clustered; table_max_nonrect at its ceiling = every
    # table vetoes as before)
    "zero_area_min_len_pt": (float, ZERO_AREA_MIN_LEN_PT, (0.0, 100_000.0)),
    "table_max_nonrect":  (int,   VETO_TABLE_MAX_NONRECT, (1, 1_000_000)),
    "nonrect_min_span_pt": (float, NONRECT_MIN_SPAN_PT,   (0.0, 1000.0)),
    "text_coverage":      (float, VETO_TEXT_COVERAGE,     (0.0, 1.0)),
    "words_per_line":     (float, VETO_WORDS_PER_LINE,    (0.0, 100.0)),
    "table_overlap":      (float, VETO_TABLE_OVERLAP,     (0.0, 1.0)),
    "accounted_for":      (float, VETO_ACCOUNTED_FOR,     (0.0, 1.0)),
}
_FIG_CAPTION_RE = re.compile(r"\bFIGURE\s+\d+\.\d+", re.I)
# ...but NOT when the page opens as an "ILLUSTRATION N.N" worked example. Those pages routinely
# cross-REFERENCE a figure in their prose while containing none, and they are the dominant false
# alarm on this corpus (30 of 49 uncovered pages, S106). The precedence is load-bearing and was
# measured: with it the triage promotes 8 pages of 49 and 5 of the 6 adjudicated are real losses;
# without it, 16 of 49, and pages already adjudicated as figure-less frames (p682, p1111) are
# promoted. CORRECTED S106 — the first build shipped the rule WITHOUT this precedence while the
# 83 % was measured WITH it: the claim described the neighbour of the probe (docs/45 §1 Family 1),
# caught by re-measuring the shipped code against the ad-hoc classifier rather than assuming.
_ILLUSTRATION_RE = re.compile(r"\bILLUSTRATION\s+\d+\.\d+", re.I)
_CAPTION_HEAD_CHARS = 900  # lever-waiver: Fable/Rab at the bench only. This is a text-shape
# constant, not a policy: 900 chars is "the top of the page" for this page geometry, and it was
# fixed by reproducing the S106 classifier exactly. It becomes a lever the moment a second
# publisher's layout disagrees with it — that is the evidence that would move it. Recorded
# because the gate's first run MISSED it (the regex skipped leading underscores, now fixed):
# the feature that prompted the framework also found the framework's first blind spot.


def levers(path: Path | None = None, text: str | None = None) -> dict:
    """Read the operator's lever file. Returns EFFECTIVE values plus, per key, why.

    Never raises and never returns a value nobody chose: a missing file, an unparseable line,
    an unknown key or an out-of-range number all fall back to the default and are NAMED in
    `rejected` so the report can say what was ignored rather than silently ignoring it.
    """
    eff = {k: spec[1] for k, spec in LEVER_SPEC.items()}
    rejected: list[str] = []
    if text is None:
        p = path or LEVER_FILE
        try:
            raw = p.read_bytes()
        except OSError:
            return {"values": eff, "rejected": [], "source": "defaults (no lever file)"}
        # Decode defensively. UnicodeDecodeError is a ValueError, NOT an OSError, so
        # `except OSError` was a promise this docstring could not keep: the shipped lever file
        # carries an em-dash, and one Notepad "Save As -> ANSI" or a PowerShell 5.1 `>`
        # redirect (which writes UTF-16 on this machine) turned the next run into a traceback
        # instead of the documented fallback. Caught by S106's own Circle, Lane C.
        source = str(p)
        text = None
        # Order matters, and it is BOM-first on purpose: a cp1252 file can decode as UTF-16 by
        # accident (measured — it did, and only produced the right values by luck of the
        # content), so UTF-16 is accepted ONLY on its byte-order mark. Everything else is
        # tried widest-last, and any non-UTF-8 read is named in `rejected`.
        order = (("utf-16", True),) if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else ()
        for enc, _bom in order + (("utf-8-sig", False), ("utf-8", False), ("cp1252", False)):
            try:
                text = raw.decode(enc)
                if enc not in ("utf-8", "utf-8-sig"):
                    rejected.append(f"lever file was not UTF-8 — read as {enc}")
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        if text is None:
            return {"values": eff,
                    "rejected": ["lever file is not readable as text — signed defaults used"],
                    "source": f"defaults (undecodable {p})"}
    else:
        source = "explicit"
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if "=" not in line:
            rejected.append(f"line {lineno}: not key=value")
            continue
        key, _, val = line.partition("=")
        key, val = key.strip().lower(), val.strip()
        if key not in LEVER_SPEC:
            rejected.append(f"line {lineno}: unknown key {key!r}")
            continue
        typ, default, rng = LEVER_SPEC[key]
        if typ is str:
            if val.lower() not in rng:
                rejected.append(f"{key}={val!r} not in {rng}")
                continue
            eff[key] = val.lower()
        else:
            try:
                num = typ(val)
            except ValueError:
                rejected.append(f"{key}={val!r} not a {typ.__name__}")
                continue
            if not (rng[0] <= num <= rng[1]):
                rejected.append(f"{key}={num} outside {rng}")
                continue
            eff[key] = num
    return {"values": eff, "rejected": rejected, "source": source}


_ASSET_RE = re.compile(r"_page_(\d+)_(Figure|Picture)_(\d+)\.(?:jpe?g|png)$", re.I)

# ── SYM-050: the pre-S60 doubled-offset map, its signature, and the S106 repair ───────────────
# Pre-S60 chunked conversions added the slice offset to asset ids that were ALREADY absolute
# (convert_and_ship.py's asset-naming comment): with slice_size 200, chunk k's assets landed in
# the even 200-band [400k, 400k+199] — ids to _page_2553_ on a 1,356-page book (docs/41:475).
# The figures are IN the bundle; only the ATTRIBUTION lies. S106 derived the inverse from the
# manifest (`slice_size: 200`) and SYM-002:
#     true_page = id + 1 - 200 * (id // 400)
# and confirmed it FOUR independent ways before use: 13/13 against a text-correlation table
# built with no formula · 23 repaired / 0 naive / 2 tied on a fresh seed and different method ·
# an offset sweep peaking sharply at 0 · assets-beyond-page-count 116 -> 0. Wired S108 (A18).
SYM050_SLICE = 200  # lever-waiver: not operator-tunable - the 200-page slice is the MEASURED structural property of pre-S60 chunked bundles (true_page = id + 1 - 200*(id//400), confirmed 4 independent ways at S106; sessions/S106 §7). A knob here would let an operator un-measure a fact.
# generic: the only recorded poisoned population (S106 census: n=1, Investment Valuation) was
# converted at slice_size 200, and the formula was confirmed only on that shape.


def sym050_true_page(p: int) -> int:
    """The S106 repair on a NAIVE 1-based page (asset id + 1). In-memory arithmetic only."""
    i = p - 1  # back to marker's 0-based asset id
    return i + 1 - SYM050_SLICE * (i // (2 * SYM050_SLICE))


def sym050_signature(per_page: dict, page_count: int, slice_size: int | None = None) -> bool:
    """Does the asset-id distribution carry the pre-S60 doubled-offset signature?

    Deliberately NARROWER than the out-of-range tripwire. Bare out-of-range says "this map is
    not trustworthy"; the signature says "and the S106 formula is the repair". All three must
    hold — (a) at least one asset attributed beyond the page count, (b) at least one id in a
    doubled band (>= 400), (c) EVERY id in an even 200-band — because the formula was confirmed
    only on that shape. A bundle that is out-of-range without (b)+(c) is still warned about,
    never "repaired" with arithmetic that would be noise on it. A manifest slice_size other
    than 200 also refuses: the formula's 200 is measured, not generic. And a book of <= 200
    pages is single-slice — its doubled offset is zero, so there is nothing to repair.
    """
    if slice_size is not None and slice_size != SYM050_SLICE:
        return False
    if page_count <= SYM050_SLICE:
        return False
    ids = [p - 1 for p in per_page]
    if not ids:
        return False
    return (any(i + 1 > page_count for i in ids)
            and any(i >= 2 * SYM050_SLICE for i in ids)
            and all((i // SYM050_SLICE) % 2 == 0 for i in ids))


def _manifest_slice_size(bundle_dir: Path) -> int | None:
    """`chunking.slice_size` from the bundle manifest, READ-ONLY; None when absent/unreadable.
    Never fatal: a bundle without a readable manifest is judged on the id distribution alone."""
    try:
        man = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    chunking = man.get("chunking") if isinstance(man, dict) else None
    v = chunking.get("slice_size") if isinstance(chunking, dict) else None
    return v if isinstance(v, int) and v > 0 else None


def _rect_area(r) -> float:
    return max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])


def _merge(a, b):
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def _touches(a, b, gap: float) -> bool:
    return not (
        a[2] + gap < b[0] or b[2] + gap < a[0] or a[3] + gap < b[1] or b[3] + gap < a[1]
    )


def _cluster(rects, gap: float):
    """Greedy transitive merge — order-independent because it repeats to a fixed point."""
    boxes = [(r, 1) for r in rects]
    changed = True
    while changed:
        changed = False
        out = []
        for box, n in boxes:
            for i, (other, m) in enumerate(out):
                if _touches(box, other, gap):
                    out[i] = (_merge(box, other), m + n)
                    changed = True
                    break
            else:
                out.append((box, n))
        boxes = out
    return boxes


def _anchored_lines(rects, lines, gap: float) -> list:
    """S157 E25 (SYM-049): the zero-area paths admitted to the clustering — each as a thin rect (its zero side padded by
    0.5 pt so the merge arithmetic has a box) — when it lies within `gap` of a positive-area path or of a zero-area line of
    the OTHER orientation. Parallel rules with nothing else near them are excluded on purpose: they are the false-positive
    class the S104 min-side filter exists for, and clustering them would hand it a 4-path region taller than 40 pt."""
    out = []
    horiz = [r for r in lines if r[3] == r[1]]
    vert = [r for r in lines if r[2] == r[0]]
    for r in lines:
        others = vert if r[3] == r[1] else horiz
        if any(_touches(r, o, gap) for o in rects) or any(_touches(r, o, gap) for o in others if o is not r):
            out.append((r[0], r[1], r[2] + (0.5 if r[2] == r[0] else 0.0), r[3] + (0.5 if r[3] == r[1] else 0.0)))
    return out


def _nonrect_items(drawings, bbox, min_span: float) -> int:
    """S157 E25: how many sizable CURVES and DIAGONAL line items the drawings inside `bbox` carry — zero for a ruled table,
    dozens for a diagram. A drawing counts as inside when at least half its rect lies in the box (a zero-area path: its
    first corner does). Curve span = the extent of its four control points; a diagonal needs both dx and dy >= 0.5 pt."""
    r = pymupdf.Rect(bbox)
    n = 0
    for d in drawings:
        dr = pymupdf.Rect(d.get("rect") or (0, 0, 0, 0))
        if dr.get_area() > 0:
            inter = r & dr
            if inter.is_empty or inter.get_area() < 0.5 * dr.get_area():
                continue
        elif not r.contains(pymupdf.Point(dr.x0, dr.y0)):
            continue
        for it in d.get("items", []):
            if it[0] == "c":
                pts = it[1:5]
                if max(max(p.x for p in pts) - min(p.x for p in pts), max(p.y for p in pts) - min(p.y for p in pts)) >= min_span:
                    n += 1
            elif it[0] == "l":
                p, q = it[1], it[2]
                if abs(p.x - q.x) >= 0.5 and abs(p.y - q.y) >= 0.5 and max(abs(p.x - q.x), abs(p.y - q.y)) >= min_span:
                    n += 1
    return n


def region_text_stats(page, bbox) -> dict:
    """Is the text inside this region PROSE, or scattered labels?

    Counts only lines whose bbox lies mostly INSIDE the region (>= half their area), so a
    paragraph beside a figure does not get charged to it. Returns the two measures that
    separated the specimens, plus the line count that did NOT.
    """
    r = pymupdf.Rect(bbox)
    area = r.get_area()
    if not area:
        return {"lines": 0, "mean_words_per_line": 0.0, "text_coverage": 0.0}
    lines, wpl, text_area = 0, [], 0.0
    for blk in page.get_text("dict")["blocks"]:
        if blk.get("type") != 0:          # 0 = text block; 1 = image
            continue
        for ln in blk.get("lines", []):
            lr = pymupdf.Rect(ln["bbox"])
            inter = lr & r
            if inter.is_empty or inter.get_area() < 0.5 * lr.get_area():
                continue
            txt = "".join(s.get("text", "") for s in ln.get("spans", [])).strip()
            if not txt:
                continue
            lines += 1
            wpl.append(len(txt.split()))
            text_area += lr.get_area()
    return {"lines": lines,
            "mean_words_per_line": round(sum(wpl) / len(wpl), 2) if wpl else 0.0,
            "text_coverage": round(text_area / area, 3)}


def _table_rects(page, cache: dict):
    """Detected table bboxes for this page, computed at most once. Never fatal: a page whose
    table finder raises is treated as having no tables, which biases toward reporting."""
    if "t" not in cache:
        try:
            cache["t"] = [tuple(tb.bbox) for tb in page.find_tables().tables]
        except Exception:
            cache["t"] = []
    return cache["t"]


def _covered_frac(bbox, others) -> float:
    """Fraction of bbox covered by `others`, summed. Overlapping others can over-count, which
    is acceptable here: the number is only ever compared against a veto threshold, and
    over-counting biases toward vetoing a frame, never toward hiding a figure... except that it
    could. Hence it is summed with text coverage and capped at 1.0 by the caller, and the
    threshold sits far from both specimens rather than tuned to the margin."""
    r = pymupdf.Rect(bbox)
    a = r.get_area()
    if not a:
        return 0.0
    tot = 0.0
    for o in others:
        inter = r & pymupdf.Rect(o)
        if not inter.is_empty:
            tot += inter.get_area() / a
    return tot


def _covered_by(bbox, others, frac: float) -> bool:
    r = pymupdf.Rect(bbox)
    a = r.get_area()
    if not a:
        return False
    for o in others:
        inter = r & pymupdf.Rect(o)
        if not inter.is_empty and inter.get_area() / a >= frac:
            return True
    return False


def is_prose_block(stats: dict, lv: dict | None = None) -> bool:
    """True = this region is a text container (sidebar, callout, table), not a figure.

    `lv` is a lever VALUES dict; omitted, the signed defaults apply. Callers that already
    hold levers pass them so one run cannot mix two configurations.
    """
    lv = lv or {k: s[1] for k, s in LEVER_SPEC.items()}
    return (stats["text_coverage"] >= lv["text_coverage"]
            and stats["mean_words_per_line"] >= lv["words_per_line"])


def source_figure_regions(pdf_path: Path, use_hashes: bool = True, lv: dict | None = None) -> dict:
    """Per 1-based page: the figure-like regions, raster and vector, with why each qualified.

    Rasters come from `get_image_info(hashes=...)` — DISPLAYED images including inline ones,
    with a bbox and an md5 digest. The digest collapses the repeated-header-logo case that a
    bare count gets wrong. `xrefs=True` is deliberately NOT requested (see the timing note in
    the loop: it costs 34.6 s/page on a large scan).
    Vectors come from `get_drawings()` clustered by proximity: a chart drawn with path
    operators has no image object at all and is invisible to every raster enumerator.
    """
    lv = lv or levers()["values"]
    doc = pymupdf.open(pdf_path)
    pages: dict[int, list] = {}
    digest_pages: dict[str, set] = {}
    captioned: set[int] = set()      # pages carrying a FIGURE N.N caption — the triage key
    vetoed = 0
    # S157 E18 (B14): what each size filter KILLED after the filter before it admitted the region — the number that says
    # whether a lever change reached the report or died at the next filter
    killed = {"raster": {"min_area_pt2": 0, "min_side_pt": 0, "max_page_fraction": 0},
              "vector": {"min_paths_or_area": 0, "min_side_pt": 0, "max_page_fraction": 0}}
    vetoed_tables = 0
    vetoed_frames = 0
    lines_clustered = 0            # S157 E25: zero-area paths admitted to the clustering (anchored)
    table_veto_disqualified = 0    # S157 E25: clusters a table would have vetoed but for their curves/diagonals
    try:
        for pno in range(doc.page_count):
            page = doc[pno]
            parea = _rect_area(tuple(page.rect))
            regions = []

            # `xrefs=True` IS OMITTED, and that one flag is the whole performance story.
            # Measured S102 on DIAGNOSING (184pp scan, 12.5-megapixel pages), fresh document
            # per case so no warm cache could lie:
            #     plain          0.00 s/page
            #     hashes=True    0.16 s/page
            #     xrefs=True    34.60 s/page   <-- ~104 min for this one book
            #     both          34.96 s/page
            # MuPDF resolves each displayed image back through the xref table, and on a large
            # scanned PDF that search dominates everything else by four orders of magnitude.
            # It burned 28 CPU-minutes before Rab noticed the machine was busy.
            # RECORDED HONESTLY: the first diagnosis blamed `hashes=True` and was WRONG -- the
            # measurement that produced it timed the flags in one process, where the earlier
            # call had already warmed MuPDF's cache and made hashing look free. Fresh-document
            # timing reversed the verdict. We keep hashes (md5 is the correct furniture-dedup
            # identity and costs 0.16 s/page) and drop xrefs, which nothing here needed.
            # Two-pass, cheapest-first. The PLAIN call is free (0.00 s/page) and gives the
            # bboxes; hashing is only worth paying for if some image actually SURVIVES the
            # size filters and could therefore need furniture-dedup. On a scan every image is
            # full-page and is dropped as "the scan itself", so the hash was computed and
            # thrown away 184 times -- that is the 191 ms/page this avoids.
            probe = page.get_image_info()
            candidate = any(
                _rect_area(tuple(i.get("bbox") or (0, 0, 0, 0))) >= lv["min_area_pt2"]
                and min(
                    (i.get("bbox") or (0, 0, 0, 0))[2] - (i.get("bbox") or (0, 0, 0, 0))[0],
                    (i.get("bbox") or (0, 0, 0, 0))[3] - (i.get("bbox") or (0, 0, 0, 0))[1],
                ) >= lv["min_side_pt"]
                and not (parea and _rect_area(tuple(i.get("bbox") or (0, 0, 0, 0))) / parea > lv["max_page_fraction"])
                for i in probe
            )
            infos = page.get_image_info(hashes=True) if (use_hashes and candidate) else probe
            for info in infos:
                bbox = tuple(info.get("bbox") or (0, 0, 0, 0))
                area = _rect_area(bbox)
                if area < lv["min_area_pt2"]:
                    killed["raster"]["min_area_pt2"] += 1
                    continue
                if min(bbox[2] - bbox[0], bbox[3] - bbox[1]) < lv["min_side_pt"]:
                    killed["raster"]["min_side_pt"] += 1   # B14: admitted by area, killed by the side — counted, not silent
                    continue
                if parea and area / parea > lv["max_page_fraction"]:
                    killed["raster"]["max_page_fraction"] += 1
                    continue  # full-page image = the scan itself
                digest = (info.get("digest") or b"").hex() if info.get("digest") else ""
                # Identity key for furniture-dedup: the md5 when hashing was paid for,
                # otherwise the xref. Both answer "is this the SAME image again?".
                ident = digest or (f"xref:{info.get('xref')}" if info.get("xref") else "")
                regions.append({"kind": "raster", "bbox": [round(v, 1) for v in bbox],
                                "area": round(area, 1), "digest": digest,
                                "ident": ident, "xref": info.get("xref")})
                if ident:
                    digest_pages.setdefault(ident, set()).add(pno + 1)

            tcache: dict = {}
            rects = []
            lines = []
            drawings = page.get_drawings()
            for d in drawings:
                r = tuple(d.get("rect") or (0, 0, 0, 0))
                if _rect_area(r) <= 0:
                    # S157 E25 (SYM-049): a zero-area path is a LINE, kept for the anchoring test below, not dropped
                    if (r[2] - r[0]) + (r[3] - r[1]) >= lv["zero_area_min_len_pt"]:
                        lines.append(r)
                    continue
                rects.append(r)
            anchored = _anchored_lines(rects, lines, lv["cluster_gap_pt"]) if lines else []
            lines_clustered += len(anchored)
            for bbox, npaths in _cluster(rects + anchored, lv["cluster_gap_pt"]):
                area = _rect_area(bbox)
                if npaths < lv["vector_min_paths"] or area < lv["min_area_pt2"]:
                    killed["vector"]["min_paths_or_area"] += 1
                    continue
                if min(bbox[2] - bbox[0], bbox[3] - bbox[1]) < lv["min_side_pt"]:
                    killed["vector"]["min_side_pt"] += 1   # B14: the case the ticket measured — 18 Cybernetics clusters at min_area_pt2=100
                    continue
                if parea and area / parea > lv["max_page_fraction"]:
                    killed["vector"]["max_page_fraction"] += 1
                    continue
                # THE VETO, vector-only and deliberately so: a raster region is a real embedded
                # image object, and vetoing one because prose overlaps it could hide an actual
                # lost figure. The false-positive class this exists for — shaded callouts and
                # table grids — is entirely vector.
                stats = region_text_stats(page, bbox)
                if is_prose_block(stats, lv):
                    vetoed += 1
                    continue
                # Second veto: structure, not text shape. A table survives the prose test
                # because its cells are short — see the note on VETO_TABLE_OVERLAP.
                # S157 E25: and no table may veto a cluster that is not rectilinear — find_tables() calls a Watt engine
                # a 16x18 table (Cyb p.26) and a room in perspective a 3x3 one (p.42); their curves and diagonals say
                # otherwise. The disqualified table also leaves the frame sum below: a drawing is not "accounted for".
                tabs = _table_rects(page, tcache)
                if tabs and _nonrect_items(drawings, bbox, lv["nonrect_min_span_pt"]) >= lv["table_max_nonrect"]:
                    tabs = []
                    table_veto_disqualified += 1
                if _covered_by(bbox, tabs, lv["table_overlap"]):
                    vetoed_tables += 1
                    continue
                # The frame case: nothing here is a picture if text + tables account for it.
                if min(1.0, stats["text_coverage"] + _covered_frac(bbox, tabs)) >= lv["accounted_for"]:
                    vetoed_frames += 1
                    continue
                regions.append({"kind": "vector", "bbox": [round(v, 1) for v in bbox],
                                "area": round(area, 1), "paths": npaths,
                                "text": stats})

            if regions:
                pages[pno + 1] = regions
                # The triage key, computed only for pages that already qualify so it costs
                # nothing on the other 1,087. A page whose own text names "FIGURE N.N" is
                # asserting a figure belongs here; measured S106, that assertion is right
                # 5 times in 6 adjudicated, against 2-in-12 for the unrestricted list.
                # An ILLUSTRATION worked example is excluded even when it names a figure —
                # see the note on _ILLUSTRATION_RE; that precedence IS the measured rule.
                txt = page.get_text()
                if (_FIG_CAPTION_RE.search(txt)
                        and not _ILLUSTRATION_RE.search(txt[:_CAPTION_HEAD_CHARS])):
                    captioned.add(pno + 1)
        n_pages = doc.page_count
    finally:
        doc.close()

    # A raster repeated on many pages is furniture (a header logo), not a figure per page.
    # Drop any digest appearing on more than a quarter of the pages that carry figures.
    if pages:
        limit = max(3, int(0.25 * n_pages))
        furniture = {d for d, ps in digest_pages.items() if len(ps) > limit}
        if furniture:
            for pno in list(pages):
                kept = [r for r in pages[pno] if r.get("ident") not in furniture]
                if kept:
                    pages[pno] = kept
                else:
                    del pages[pno]
    return {"pages": pages, "page_count": n_pages, "vetoed_prose_regions": vetoed, "filters_killed": killed,
            "captioned_pages": sorted(captioned & set(pages)),
            "vetoed_table_regions": vetoed_tables,
            "vetoed_framed_text_regions": vetoed_frames,
            "zero_area_paths_clustered": lines_clustered,
            "table_vetoes_disqualified": table_veto_disqualified,
            "furniture_digests": len(
                {d for d, ps in digest_pages.items() if len(ps) > max(3, int(0.25 * n_pages))}
            )}


def output_asset_pages(bundle_dir: Path) -> dict:
    """Per 1-based page: how many figure assets the bundle attributes to it.

    Marker names assets `_page_{page_id}_{BlockType}_{block_id}.jpeg` and `page_id` is
    ZERO-INDEXED, while audit pages and chunk seams are 1-based — three namespaces coexist in
    one manifest, so the +1 here is load-bearing, not cosmetic (docs/41 Appendix A §A5).
    """
    assets = bundle_dir / "assets"
    per_page: dict[int, int] = {}
    unparsed = []
    if assets.is_dir():
        for f in sorted(assets.iterdir()):
            m = _ASSET_RE.search(f.name)
            if not m:
                unparsed.append(f.name)
                continue
            per_page[int(m.group(1)) + 1] = per_page.get(int(m.group(1)) + 1, 0) + 1
    return {"per_page": per_page, "unparsed": unparsed}


def coverage(pdf_path: Path, bundle_dir: Path, use_hashes: bool = True,
             lv: dict | None = None) -> dict:
    lever = levers() if lv is None else {"values": lv, "rejected": [], "source": "explicit"}
    lv = lever["values"]
    src = source_figure_regions(pdf_path, use_hashes=use_hashes, lv=lv)
    out = output_asset_pages(bundle_dir)
    naive_per_page = out["per_page"]

    # Assets attributed to a page beyond the source's page count are the gross tripwire for
    # pre-S60 doubled-offset bundles. Computed on the NAIVE map always — this key is the
    # DETECTOR and keeps its shipped meaning regardless of any repair below.
    out_of_range = sorted(p for p in naive_per_page if p > src["page_count"])

    # THE REPAIR (S106, wired S108 A18). When the FULL doubled-offset signature matches — not
    # on bare out-of-range — the naive map is repaired IN MEMORY and coverage is computed on
    # the repaired map. The unrepaired numbers stay in the report beside it for continuity.
    # Nothing on disk is ever read for writing or touched: the bundle is never modified.
    map_repaired = sym050_signature(naive_per_page, src["page_count"],
                                    _manifest_slice_size(bundle_dir))
    if map_repaired:
        per_page: dict[int, int] = {}
        for p, n in naive_per_page.items():
            tp = sym050_true_page(p)
            per_page[tp] = per_page.get(tp, 0) + n
    else:
        per_page = naive_per_page

    figure_pages = sorted(src["pages"])
    uncovered = [p for p in figure_pages if per_page.get(p, 0) == 0]

    # THE TRIAGE (signed Rab, S106). It partitions the SAME uncovered list; it never shortens
    # it. `uncovered_captioned` is the list a human should read first: measured on Investment
    # Valuation with a repaired page map, 5 of 6 adjudicated captioned pages were real losses,
    # against 2 of 12 unrestricted. `mode=off` reports the partition as empty and changes
    # nothing, so turning triage off can never surface fewer pages than leaving it on.
    captioned = set(src.get("captioned_pages", ()))
    triage_on = lv["mode"] == "caption"
    unc_capt = [p for p in uncovered if p in captioned] if triage_on else []
    unc_rest = [p for p in uncovered if p not in captioned] if triage_on else list(uncovered)
    # S189 E1 (SYM-095): the triage keys on the literal `FIGURE N.N` — an input-shape assumption the instrument never
    # stated. A book that captions figures any other way (Cybernetics) put every uncovered page in `uncovered_other`
    # and the READ-FIRST list read empty as if coverage were fine. The instrument now DECLARES the convention's state:
    # "off" (mode=off), "met" (at least one page carries the convention), "unmet" (figure pages exist and none carries
    # it — the triage is inert by convention, not by coverage). A report field, never a verdict; the partition is unchanged.
    if not triage_on:
        triage_convention = "off"
    elif not figure_pages or captioned:
        triage_convention = "met"
    else:
        triage_convention = "unmet"
    # S157 E35: the uncovered pages by region kind — on the adjudicated Damodaran corpus raster <=> a lost figure (21/21) and
    # vector-only <=> an ILLUSTRATION box (104/104); a count, never a verdict (a diagram book's figures are vector)
    by_kind: dict[str, int] = {}
    for p in uncovered:
        k = "+".join(sorted({r["kind"] for r in src["pages"].get(p, [])})) or "none"
        by_kind[k] = by_kind.get(k, 0) + 1

    # The SYM-050 block travels in BOTH output forms. S104 harvested its poisoned headline in
    # `--json`, where the human branch's warning never appeared — carrying the map's state into
    # the payload is the fix candidate SYM-050 named. It is a condition, not a verdict.
    if map_repaired:
        naive_uncovered = [p for p in figure_pages if naive_per_page.get(p, 0) == 0]
        sym050 = {
            "detected": True,
            "formula": "true_page = id + 1 - 200*(id//400) (S106, confirmed 4 independent ways)",
            "repair_scope": "in-memory only — bundle files are never modified",
            "assets_out_of_range_after_repair":
                sorted(p for p in per_page if p > src["page_count"]),
            "unrepaired": {
                "pages_uncovered": len(naive_uncovered),
                "coverage": (round(1 - len(naive_uncovered) / len(figure_pages), 4)
                             if figure_pages else None),
                "output_asset_pages": len(naive_per_page),
            },
        }
    else:
        sym050 = {"detected": False}
        if out_of_range:
            sym050["note"] = ("assets sit beyond the page count but the doubled-offset "
                              "signature does not match — page map untrustworthy (SYM-050) "
                              "and the S106 formula does NOT apply")

    detail = []
    for p in uncovered:
        regions = src["pages"][p]
        detail.append({
            "page": p,
            "regions": len(regions),
            "kinds": sorted({r["kind"] for r in regions}),
            "largest_area_pt2": round(max(r["area"] for r in regions), 1),
            "bboxes": [r["bbox"] for r in regions[:4]],
        })
    return {
        "bundle": bundle_dir.name,
        "source": pdf_path.name,
        "pages_total": src["page_count"],
        "pages_with_source_figures": len(figure_pages),
        "pages_uncovered": len(uncovered),
        "coverage": (
            round(1 - len(uncovered) / len(figure_pages), 4) if figure_pages else None
        ),
        "page_map": ("REPAIRED (SYM-050 doubled-offset)" if map_repaired else "as-shipped"),
        "sym050_doubled_offset": sym050,
        "triage_mode": lv["mode"],
        "triage_convention": triage_convention,   # S189 E1 (SYM-095): off / met / unmet — declared, never inferred
        "triage_captioned_pages": len(captioned),  # how many pages of the book carry the FIGURE N.N convention at all
        "uncovered_captioned": unc_capt,
        "uncovered_other": unc_rest,
        "uncovered_by_kind": by_kind,
        "output_asset_pages": len(per_page),
        "output_assets_total": sum(per_page.values()),
        "assets_out_of_range": out_of_range,
        "unparsed_asset_names": out["unparsed"][:5],
        "furniture_digests_dropped": src["furniture_digests"],
        "vetoed_prose_regions": src.get("vetoed_prose_regions", 0),
        "vetoed_table_regions": src.get("vetoed_table_regions", 0),
        "vetoed_framed_text_regions": src.get("vetoed_framed_text_regions", 0),
        # S157 E25 (SYM-049): the two counts that say the mechanisms fired — zero-area paths clustered (anchored lines), and
        # table vetoes disqualified by a cluster's curves and diagonals
        "zero_area_paths_clustered": src.get("zero_area_paths_clustered", 0),
        "table_vetoes_disqualified": src.get("table_vetoes_disqualified", 0),
        "uncovered_detail": detail,
        "conditions": {
            "unit": "PER PAGE — a page with N source figures and >=1 output asset counts as "
                    "covered; bbox-overlap is not computable from a bundle (see module head)",
            "pymupdf": pymupdf.__doc__.strip() if pymupdf.__doc__ else pymupdf.version[0],
            # EFFECTIVE values, not the defaults — a number never travels without the
            # configuration that produced it (docs/34; docs/18 §2 modularity law).
            "levers_source": lever["source"],
            "levers_rejected": lever["rejected"],
            "min_area_pt2": lv["min_area_pt2"],
            "min_side_pt": lv["min_side_pt"],
            "max_page_fraction": lv["max_page_fraction"],
            # B14 (S157 E18): the regions each size filter killed after the one before admitted them — a lever change that
            # buys nothing reads here as a count on the next filter, never as a byte-identical report and silence
            "filters_killed": src.get("filters_killed"),
            "vector_min_paths": lv["vector_min_paths"],
            "vector_cluster_gap_pt": lv["cluster_gap_pt"],
            "veto_text_coverage": lv["text_coverage"],
            "veto_words_per_line": lv["words_per_line"],
            "veto_table_overlap": lv["table_overlap"],
            "veto_accounted_for": lv["accounted_for"],
            "zero_area_min_len_pt": lv["zero_area_min_len_pt"],
            "veto_table_max_nonrect": lv["table_max_nonrect"],
            "nonrect_min_span_pt": lv["nonrect_min_span_pt"],
            "image_identity": "md5" if use_hashes else "none (furniture-dedup disabled)",
            "verdict_effect": "NONE — report-only by docs/15 §6; writes nothing",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="P-1 figure coverage (report-only, CPU-only)")
    ap.add_argument("--pdf", required=True, type=Path)
    ap.add_argument("--bundle", required=True, type=Path)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-hashes", action="store_true",
                    help="skip md5 furniture-dedup (saves ~0.16 s/page; the expensive flag was "
                         "never hashing -- see the module comment on xrefs)")
    a = ap.parse_args()
    if not a.pdf.exists():
        print(f"no such pdf: {a.pdf}", file=sys.stderr)
        return 2
    if not a.bundle.is_dir():
        print(f"no such bundle dir: {a.bundle}", file=sys.stderr)
        return 2
    rep = coverage(a.pdf, a.bundle, use_hashes=not a.no_hashes)
    if a.json:
        print(json.dumps(rep, indent=1))
    else:
        print(f"{rep['bundle']}")
        print(f"  pages {rep['pages_total']} · with source figures "
              f"{rep['pages_with_source_figures']} · UNCOVERED {rep['pages_uncovered']} "
              f"· coverage {rep['coverage']}")
        if rep["assets_out_of_range"]:
            print(f"  ! assets attributed beyond page count: {rep['assets_out_of_range'][:6]}"
                  " — pre-S60 doubled-offset bundle, report not trustworthy (SYM-050)")
        c = rep["conditions"]
        print(f"  levers: mode={rep['triage_mode']} · from {c['levers_source']}"
              + (f" · IGNORED {c['levers_rejected']}" if c["levers_rejected"] else ""))
        det = {d["page"]: d for d in rep["uncovered_detail"]}
        if rep["triage_mode"] == "caption":
            # S189 E1 (SYM-095): say when the convention is unmet — an empty READ-FIRST list must never read as
            # "nothing to read first" on a book that captions its figures some other way.
            if rep.get("triage_convention") == "unmet":
                print("  TRIAGE INERT: no page of this book captions a figure as FIGURE N.N — READ FIRST is empty "
                      "by convention, not by coverage; every uncovered page is below, unranked.")
            # READ THESE FIRST: the page's own text names a FIGURE, so it asserts one belongs
            # here. Both lists are always printed — triage orders, it never hides.
            print(f"  READ FIRST — uncovered pages whose text names a FIGURE "
                  f"({len(rep['uncovered_captioned'])} of {rep['pages_uncovered']}):")
            for p in rep["uncovered_captioned"][:12] or ["(none)"]:
                d = det.get(p)
                print(f"    p{p:>4}  {d['regions']} region(s) {','.join(d['kinds'])}"
                      f"  largest {d['largest_area_pt2']}pt²" if d else f"    {p}")
            print(f"  the rest ({len(rep['uncovered_other'])}), unranked:")
            rest = rep["uncovered_other"][:8]
        else:
            rest = rep["uncovered_other"][:12]
            # MARK the cut. "Triage orders, it never hides" was true of the JSON payload and
            # FALSE here: mode=off printed 12 of 239 with no count and no ellipsis — SYM-052's
            # own defect class, on the surface an operator reads, shipped by the session that
            # filed SYM-052. Caught by S106's Circle, Lane C.
            if len(rep["uncovered_other"]) > len(rest):
                print(f"  {len(rep['uncovered_other'])} uncovered pages · showing the first "
                      f"{len(rest)} — --json lists them all:")
        for p in rest:
            d = det.get(p)
            if d:
                print(f"    p{p:>4}  {d['regions']} region(s) {','.join(d['kinds'])}"
                      f"  largest {d['largest_area_pt2']}pt²")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
