# -*- coding: utf-8 -*-
"""test_collapse_embedded.py — S220 E8: the tripwire for the collapse's coverage-aware gate (`loop_gate`).

The collapse refused a decoder loop EMBEDDED in prose: the cond-mat.mtrl-sci paragraph carries "Equiporal" 198 times
inside 900 characters of real sentences, so the whole-paragraph type-token ratio read 0.27 (over the 0.10 line) and the
gesture said "still reads as language". The cycle's coverage now decides first. Cases: the gate's own math on strings
(a loop covering most of a paragraph passes whatever the ratio; prose with a short repeat still refuses; a short text
refuses); then, on a SANDBOX copy of the mtrl-sci held bundle beside its PDF (skips, never passes, when absent): the
preview reads the loop (period 1, ~198 repeats) at the audit's recorded line through the excerpt anchor, the real
collapse keeps the head and the tail byte for byte and removes exactly the loop, one ledger event, one record carrying
ttr and cover, and the undo is exact. Run under the converter's interpreter:
    C:\\Users\\Bndit\\ml\\marker-env\\Scripts\\python.exe test_collapse_embedded.py
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench as B  # noqa: E402

LIB = Path(r"C:\Users\Bndit\ml\library")
HELD = LIB / "held" / "14c2c3b281c61d7f"
PDF = next((p for p in (LIB / "drop" / "done").glob("*mtrl-sci*.pdf")), None) if (LIB / "drop" / "done").exists() else None
ZONE_LINE = 302          # the audit's recorded line (the .marker.txt's); the body's paragraph is 301 (SYM-025 anchors it)

PROSE = ("Every finite-difference probe fixes its step from the model's declared working precision: the step is bounded "
         "below by the smallest spacing at which the model's own round-off does not dominate the difference. Where a "
         "probe's nominal grid would fall below that bound, the grid is thinned rather than the range shrunk, the scan "
         "range is a physical choice, and the run is marked as resolution-limited. For a float32 model, force differences "
         "are taken with a step of 0.0106 Angstrom rather than 0.0010, and the collinear conservativeness scan is reduced "
         "from 31 points to 9 points. A residual reported for a float32 model is therefore an upper bound, part of it is "
         "truncation at the coarser step. On the analytic control, where the entire residual is discretisation error by "
         "construction, that floor is small for silicon against a smaller one at float64.")


def _fid(b):
    return hashlib.sha256(json.dumps(b.manifest.get("fidelity"), sort_keys=True).encode()).hexdigest()[:16]


class LoopGateMath(unittest.TestCase):
    def test_embedded_loop_passes_on_coverage(self):
        text = PROSE[:400] + " " + ("Equiporal " * 150) + PROSE[400:800]
        g = B.loop_gate(text)
        self.assertTrue(g["ok"], g["reason"])
        self.assertGreaterEqual(g["ttr"], B.TTR_LOOP_MAX, "the ratio alone would refuse this one")
        self.assertGreaterEqual(g["cover"], B.COLLAPSE_COVER_MIN)
        self.assertEqual(g["found"][0], 1)

    def test_prose_with_a_short_repeat_still_refuses(self):
        text = PROSE + " " + ("the state of " * 8) + PROSE
        g = B.loop_gate(text)
        self.assertFalse(g["ok"])
        self.assertIn("still reads as language", g["reason"])
        self.assertLess(g["cover"], B.COLLAPSE_COVER_MIN)

    def test_pure_loop_passes_as_before(self):
        g = B.loop_gate("x y " * 60)
        self.assertTrue(g["ok"])
        self.assertLess(g["ttr"], B.TTR_LOOP_MAX)

    def test_short_text_refuses(self):
        g = B.loop_gate("a b a b a b")
        self.assertFalse(g["ok"])


class CollapseOnTheBundle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (HELD / "manifest.json").exists() or not PDF or not PDF.exists():
            raise unittest.SkipTest("the mtrl-sci held bundle or its PDF is not on this machine — UNREAD, not a pass")
        cls.tmp = Path(tempfile.mkdtemp(prefix="fp-collapse-"))
        cls.bundle = cls.tmp / "14c2c3b281c61d7f"
        shutil.copytree(HELD, cls.bundle)
        b = B.Bench(cls.bundle, pdf=PDF, sandbox=False)
        while (b.manifest.get("repairs") or []) and b.manifest["repairs"][-1].get("mode") in ("collapse", "textlayer"):
            b.undo_ledger()          # the pre-act state whatever the live bundle holds (E7-fix's rule)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_preview_then_collapse_then_undo(self):
        b = B.Bench(self.bundle, pdf=PDF, sandbox=False)
        sha0, ev0, reps0, fid0 = b._sha(b.body()), len(b.ledger()), len(b.manifest.get("repairs", [])), _fid(b)
        pv = b.collapse(ZONE_LINE, preview=True)
        self.assertEqual(pv["at"], 301)
        self.assertEqual(pv["anchor"], "excerpt")
        self.assertEqual(pv["period_tokens"], 1)
        self.assertGreaterEqual(pv["repeats"], 150)
        self.assertGreaterEqual(pv["ttr"], B.TTR_LOOP_MAX, "the embedded case: the ratio reads as language")
        self.assertGreaterEqual(pv["cover"], B.COLLAPSE_COVER_MIN)
        # the head runs to "...many-body expansion (the " - the loop replaced ONE word, "EQUIFORMERV2," (the operator's
        # first reading from a 260-character head said four lines were lost; this assertion is what corrected it)
        self.assertIn("expansion (the", pv["head_kept"])
        self.assertEqual(b._sha(b.body()), sha0, "a preview wrote")
        first, last, para = b._zone_paragraph(301)
        r = b.collapse(ZONE_LINE)
        self.assertEqual(r["record"]["mode"], "collapse")
        self.assertAlmostEqual(r["record"]["cover"], round(pv["cover"], 3))
        b2 = B.Bench(self.bundle, pdf=PDF, sandbox=False)
        new_first, new_last, new_para = b2._zone_paragraph(301)
        self.assertTrue(new_para.startswith(pv["head_kept"][-40:]) or pv["head_kept"][-40:] in new_para)
        self.assertTrue(para.startswith(new_para[:len(pv["head_kept"])]), "the head is not byte-identical")
        self.assertEqual(len(para) - r["chars_removed"], len(new_para) - len(new_para.split("\n")[-1]) - 1,
                         "the paragraph shrank by exactly the loop, plus the marker line")
        self.assertEqual(len(b2.ledger()), ev0 + 1)
        self.assertEqual(len(b2.manifest["repairs"]), reps0 + 1)
        self.assertEqual(_fid(b2), fid0)
        b2.undo_ledger()
        b3 = B.Bench(self.bundle, pdf=PDF, sandbox=False)
        self.assertEqual(b3._sha(b3.body()), sha0)
        self.assertEqual(len(b3.manifest.get("repairs", [])), reps0)
        self.assertEqual(_fid(b3), fid0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
