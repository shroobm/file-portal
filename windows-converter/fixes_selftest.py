# -*- coding: utf-8 -*-
"""fixes_selftest.py — LANE B selftest for fixes.py. Run under marker-env (imports marker + pdftext,
same as fixes.py itself does — see fixes.py's own docstring for why one interpreter suffices):

  C:\\Users\\Bndit\\ml\\marker-env\\Scripts\\python.exe fixes_selftest.py

Every check is independent and prints one PASS/FAIL line; the last line is "N/N ok". No PDF is opened,
no model is loaded, no network call is made, and nothing under C:/Users/Bndit/ml/library is touched —
every path used here is a temp dir (HARD RULE 3) and every pdftext/marker object is a plain synthetic
stand-in, not a real document.

Per the orchestration law: every check that has a plausible "did nothing" failure mode carries a
NEGATIVE CONTROL alongside it (marked NEGATIVE CONTROL in the print line) — a case that must come out
the OTHER way, so a selftest that always prints PASS regardless of the code cannot hide in here.
"""
from __future__ import annotations

import os
import sys
import tempfile

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixes  # noqa: E402

PASS = 0
FAIL = 0
FAILED_NAMES = []


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("PASS  %s" % name)
    else:
        FAIL += 1
        FAILED_NAMES.append(name)
        print("FAIL  %s" % name)


# =====================================================================================================
# 1. read_lever
# =====================================================================================================
with tempfile.TemporaryDirectory(prefix="fp-fixes-selftest-") as tmp:
    p_missing = os.path.join(tmp, "does-not-exist.txt")
    check("read_lever: missing file -> []", fixes.read_lever(p_missing) == [])

    p_basic = os.path.join(tmp, "basic.txt")
    with open(p_basic, "w", encoding="utf-8") as fh:
        fh.write("# a comment\n\noverlap-fraction-gate\n\n# another\ncharbox-lift\noverlap-fraction-gate\n")
    got = fixes.read_lever(p_basic)
    check("read_lever: comments/blank ignored, order kept, duplicates dropped",
          got == ["overlap-fraction-gate", "charbox-lift"])

    p_for = os.path.join(tmp, "for.txt")
    with open(p_for, "w", encoding="utf-8") as fh:
        fh.write("for: some-drop-file.pdf\nlane-share-rule\ndegen-rule-line\n")
    got = fixes.read_lever(p_for)
    check("read_lever: 'for:' header line skipped like a comment (real FIXES_FILE shape)",
          got == ["lane-share-rule", "degen-rule-line"])

    p_bad = os.path.join(tmp, "bad.txt")
    with open(p_bad, "w", encoding="utf-8") as fh:
        fh.write("overlap-fraction-gate\nnot-a-real-fix\n")
    try:
        fixes.read_lever(p_bad)
        check("read_lever: unknown name raises ValueError naming it", False)
    except ValueError as e:
        check("read_lever: unknown name raises ValueError naming it", "not-a-real-fix" in str(e))

    # NEGATIVE CONTROL: a file with only comments/blanks must be [] too (not [] by accident of the
    # missing-file branch above -- a real, present, all-comment file must ALSO read empty)
    p_empty = os.path.join(tmp, "empty.txt")
    with open(p_empty, "w", encoding="utf-8") as fh:
        fh.write("# nothing here\n\n\n")
    check("read_lever NEGATIVE CONTROL: present all-comment file -> [] (not a missing-file fluke)",
          fixes.read_lever(p_empty) == [])


# =====================================================================================================
# 2. overlap-fraction-gate: FractionLineBuilder.check_line_overlaps vs the stock LineBuilder
# =====================================================================================================
from marker.builders.line import LineBuilder  # noqa: E402


class _Box:
    def __init__(self, bbox):
        self.bbox = list(bbox)


class _Polygon:
    def __init__(self, bbox):
        self._bbox = list(bbox)

    def expand(self, dx, dy):
        x0, y0, x1, y1 = self._bbox
        return _Box([x0 - dx, y0 - dy, x1 + dx, y1 + dy])


class _Line:
    def __init__(self, bbox):
        self.polygon = _Box(bbox)


class _ProviderLine:
    def __init__(self, bbox):
        self.line = _Line(bbox)


class _DocPage:
    def __init__(self, page_bbox):
        self.polygon = _Polygon(page_bbox)


PAGE = _DocPage([0, 0, 1000, 1000])

# Case A: B overlaps A and C, each pairwise absolute overlap area is large (5000 pt^2, well over the
# stock's literal 0.1 pt^2 threshold) but small as a FRACTION of B's own area (5000 / 50000 = 0.1, well
# under the fraction gate's 0.5) -- "more than one other" neighbour, the exact clause both classes share.
A = [0, 0, 500, 100]     # area 50000
B = [0, 90, 500, 190]    # area 50000; overlaps A in y[90,100] -> area 5000 (frac vs B: 0.1)
C = [0, 180, 500, 280]   # area 50000; overlaps B in y[180,190] -> area 5000 (frac vs B: 0.1); no overlap with A
lines_case_a = [_ProviderLine(A), _ProviderLine(B), _ProviderLine(C)]

fraction_result_a = fixes.FractionLineBuilder.check_line_overlaps(None, PAGE, lines_case_a)
check("FractionLineBuilder: large absolute overlap, small fraction, >1 neighbour -> True",
      fraction_result_a is True)

# NEGATIVE CONTROL for case A: the stock LineBuilder (absolute-area threshold 0.1 pt^2, same ">2"
# neighbour-count clause) must call the SAME input a failure -- proving the fraction gate is doing
# real, different work, not just echoing the stock test on this input.
stock_result_a = LineBuilder.check_line_overlaps(LineBuilder, PAGE, lines_case_a)
check("FractionLineBuilder NEGATIVE CONTROL: stock LineBuilder on the same input -> False",
      stock_result_a is False)

# Case B: a genuinely glued/tall line D spanning two real neighbours E and F, overlapping each by more
# than half of D's OWN area -- the fraction gate must still catch this (it is not simply "always True").
D = [0, 0, 500, 100]     # area 50000 (the glued line)
E = [0, 0, 500, 60]      # area 30000; overlap with D: y[0,60] -> 30000 (frac vs D: 0.6)
F = [0, 40, 500, 100]    # area 36000; overlap with D: y[40,100] -> 30000 (frac vs D: 0.6)
lines_case_b = [_ProviderLine(D), _ProviderLine(E), _ProviderLine(F)]
fraction_result_b = fixes.FractionLineBuilder.check_line_overlaps(None, PAGE, lines_case_b)
check("FractionLineBuilder: a tall glued line over two neighbours -> False", fraction_result_b is False)


# =====================================================================================================
# 3. offpage-clip: the pdftext.pdf.pages.get_chars wrapper drops wholly-off-page chars
# =====================================================================================================
import pdftext.pdf.pages as pp  # noqa: E402
from pdftext.schema import Bbox  # noqa: E402

PAGE_BBOX = (0.0, 0.0, 612.0, 792.0)  # x_start, y_start, x_end, y_end (a US-letter page, pdfium bbox shape)


def _char(bbox, char_idx=0, font_size=10.0, rotation=0, ch="x"):
    return {
        "bbox": Bbox(list(bbox)),
        "char": ch,
        "rotation": rotation,
        "font": {"name": "Test", "flags": 0, "size": font_size, "weight": 400},
        "char_idx": char_idx,
    }


class _FakeTextPage:
    """get_charbox(i, loose=False) -> (tx0, ty0, tx1, ty1) in pdfium's own (untransformed, y-up) page
    coordinates, exactly the signature _lift_charboxes calls (pdftext's real PdfTextPage.get_charbox)."""

    def __init__(self, boxes):
        self._boxes = boxes

    def get_charbox(self, i, loose=False):
        return self._boxes[i]


OFFPAGE_CHAR = _char([700.0, 100.0, 720.0, 120.0], char_idx=0)   # wholly right of width+1=613
ONPAGE_CHAR = _char([100.0, 100.0, 120.0, 120.0], char_idx=1)    # comfortably inside
STRADDLE_CHAR = _char([-5.0, 100.0, 10.0, 120.0], char_idx=2)    # crosses the -1 edge, not wholly outside

_FAKE_CHARS = [OFFPAGE_CHAR, ONPAGE_CHAR, STRADDLE_CHAR]


def _fake_orig_get_chars(textpage, page_bbox, page_rotation, quote_loosebox=True):
    return list(_FAKE_CHARS)


pp.get_chars = _fake_orig_get_chars  # install the fake BEFORE fixes.apply(), so apply() wraps it
f1 = fixes.apply(["offpage-clip"], log=lambda *a: None)
wrapped_after_first = pp.get_chars
result = pp.get_chars(object(), PAGE_BBOX, 0)
kept_ids = {c["char_idx"] for c in result}
check("offpage-clip: off-page char dropped", 0 not in kept_ids)
check("offpage-clip: on-page char kept", 1 in kept_ids)
check("offpage-clip: straddling char kept", 2 in kept_ids)
check("offpage-clip: stats counted the drop", fixes._STATE["stats"]["chars_dropped"] >= 1)

# =====================================================================================================
# 4. apply() idempotency: calling it again (now also turning charbox-lift on) must not add a second
# wrapper layer around pdftext.pdf.pages.get_chars.
# =====================================================================================================
f2 = fixes.apply(["offpage-clip", "charbox-lift"], log=lambda *a: None)
wrapped_after_second = pp.get_chars
check("apply(): a second call does not wrap the wrapper again (same function object)",
      wrapped_after_first is wrapped_after_second)

# The remaining chars after clip are char_idx 1 (on-page) and 2 (straddle); give the now-active lift
# stage a textpage whose ink is already contained by both loose boxes, so this check isolates "still
# one wrapper layer, both stages ran" from "did the lift math trigger" (that math is checked in §5).
idempotency_textpage = _FakeTextPage({
    1: (100.0, 682.0, 108.0, 697.0),   # ink t_top=95, t_bot=110: inside loose box [100,120] -> no lift
    2: (-5.0, 682.0, 2.0, 697.0),      # same, for the straddling char's loose box [100,120]
})
seen_before = fixes._STATE["stats"]["chars_seen"]
result2 = pp.get_chars(idempotency_textpage, PAGE_BBOX, 0)
kept_ids2 = {c["char_idx"] for c in result2}
check("apply(): one wrapper layer -> straddling char still kept after a second apply()",
      2 in kept_ids2)
check("apply(): one wrapper layer -> chars_seen advanced by exactly one pass's worth (not doubled)",
      fixes._STATE["stats"]["chars_seen"] - seen_before == len(_FAKE_CHARS))


# =====================================================================================================
# 5. charbox-lift: a fake textpage.get_charbox reveals ink above the loose box's recorded top
# =====================================================================================================
# page_height = 792 (PAGE_BBOX above). Char 0: loose box top b[1]=60, size=max(10, 75-60)=15, so the
# lift threshold is t_top < 60 - 4.5 = 55.5. Ink's tight box: max(ty0,ty1)=742 -> t_top = 792-742 = 50
# (< 55.5: lift). Char 1: same loose box shape but ink already contained (t_top = 792-734 = 58 >= 55.5:
# untouched -- the negative control).
LIFT_CHAR = _char([100.0, 60.0, 110.0, 75.0], char_idx=0, font_size=10.0)
CONTAINED_CHAR = _char([200.0, 60.0, 210.0, 75.0], char_idx=1, font_size=10.0)
lift_textpage = _FakeTextPage({
    0: (100.0, 728.0, 108.0, 742.0),   # ink: t_top=50, t_bot=64 -> lifts LIFT_CHAR
    1: (200.0, 722.0, 208.0, 734.0),   # ink: t_top=58, t_bot=70 -> already contained, no lift
})

lift_stats = {"chars_seen": 0, "chars_dropped": 0, "chars_lifted": 0}
lifted = fixes._lift_charboxes(lift_textpage, [LIFT_CHAR, CONTAINED_CHAR], PAGE_BBOX, 0, lift_stats)
lift_b = lifted[0]["bbox"].bbox
contained_b = lifted[1]["bbox"].bbox
check("charbox-lift: a loose box whose top sits below its ink is lifted",
      lift_b[1] < 60.0 and lift_stats["chars_lifted"] == 1)
check("charbox-lift NEGATIVE CONTROL: a box already containing its ink is untouched",
      contained_b == [200.0, 60.0, 210.0, 75.0])


# =====================================================================================================
# 6. lane_rule
# =====================================================================================================
check("lane_rule: one OCR-font span in 25,152 stays clean (Scotia Q3)",
      fixes.lane_rule(0.0, 1, 25152) is False)
check("lane_rule: 1,300 of 25,152 OCR-font spans (share 0.0517 >= 0.05) -> scan",
      fixes.lane_rule(0.0, 1300, 25152) is True)
check("lane_rule: invisible_ratio 0.6 alone (> 0.5) -> scan regardless of share",
      fixes.lane_rule(0.6, 0, 100) is True)
# NEGATIVE CONTROL: right at the ratio boundary, NOT over it, and share under SHARE -> clean
check("lane_rule NEGATIVE CONTROL: ratio exactly 0.5 (not > 0.5), share under SHARE -> clean",
      fixes.lane_rule(0.5, 0, 100) is False)


# =====================================================================================================
# 7. is_rule_line
# =====================================================================================================
check("is_rule_line: 43 underscores -> True (a leader)", fixes.is_rule_line("____" * 43) is True)
check("is_rule_line: real prose -> False", fixes.is_rule_line("real words here") is False)
check("is_rule_line: a table row of pipes and digits -> False (digits are distinct glyphs)",
      fixes.is_rule_line("| 12,345.67 | 89 |") is False)
# NEGATIVE CONTROL: exactly 3 distinct glyphs is still <= 3 (boundary True); 4 distinct tips it False
check("is_rule_line: boundary, exactly 3 distinct glyphs -> True", fixes.is_rule_line("ababcbcbc") is True)
check("is_rule_line NEGATIVE CONTROL: 4 distinct glyphs -> False", fixes.is_rule_line("abcdabcdabcd") is False)


# =====================================================================================================
# 8. batch_sizes
# =====================================================================================================
check("batch_sizes(None) -> {} (an unmeasured card gets no override)", fixes.batch_sizes(None) == {})
_total = fixes._card_total_mib()
_small = int(0.05 * _total)     # well under the 0.15 threshold
_large = int(0.90 * _total)     # well over it
check("batch_sizes(small free) -> lowered", fixes.batch_sizes(_small) == {"detection_batch_size": 4, "table_rec_batch_size": 4})
check("batch_sizes NEGATIVE CONTROL: plenty of free memory -> {} (does nothing where it must not)",
      fixes.batch_sizes(_large) == {})


# =====================================================================================================
# 9. manifest_record
# =====================================================================================================
mr = fixes.manifest_record(["offpage-clip", "charbox-lift"], {"chars_seen": 10, "chars_dropped": 1, "chars_lifted": 2})
check("manifest_record: literal keys 'fixes' and 'fixes_stats'",
      set(mr.keys()) == {"fixes", "fixes_stats"} and mr["fixes"] == ["offpage-clip", "charbox-lift"]
      and mr["fixes_stats"] == {"chars_seen": 10, "chars_dropped": 1, "chars_lifted": 2})


# =====================================================================================================
# 10. FIXES tuple contract: every member round-trips through read_lever and apply() refuses the rest
# =====================================================================================================
with tempfile.TemporaryDirectory(prefix="fp-fixes-selftest2-") as tmp:
    p_all = os.path.join(tmp, "all.txt")
    with open(p_all, "w", encoding="utf-8") as fh:
        fh.write("\n".join(fixes.FIXES) + "\n")
    check("read_lever: every literal FIXES name round-trips", fixes.read_lever(p_all) == list(fixes.FIXES))

try:
    fixes.apply(["overlap-fraction-gate", "totally-invalid"], log=lambda *a: None)
    check("apply(): unknown fix name raises ValueError", False)
except ValueError as e:
    check("apply(): unknown fix name raises ValueError", "totally-invalid" in str(e))


# S211 CORRECTIONS row 5: a get_chars fix keeps pdftext in-process — over ten pages pdftext spawns workers that import it
# fresh and unpatched (Bill C-30 re-OCR'd its 2,066 lines under offpage-clip; C-288's five pages, in-process, kept every page)
check("config_overrides(): offpage-clip → pdftext_workers 1", fixes.config_overrides(["offpage-clip"]) == {"pdftext_workers": 1})
check("config_overrides(): charbox-lift → pdftext_workers 1", fixes.config_overrides(["charbox-lift"]) == {"pdftext_workers": 1})
check("config_overrides(): NEGATIVE CONTROL — the overlap gate alone (a Marker class swap, in-process) overrides nothing",
      fixes.config_overrides(["overlap-fraction-gate", "lane-share-rule"]) == {})
check("config_overrides(): nothing applied → {}", fixes.config_overrides([]) == {})

print("\n%d/%d ok" % (PASS, PASS + FAIL))
if FAIL:
    print("FAILED: %s" % ", ".join(FAILED_NAMES))
sys.exit(0 if FAIL == 0 else 1)
