# -*- coding: utf-8 -*-
"""test_textlayer_restore.py — S220 E7: the tripwire for `Bench.restore_textlayer` (Rab's word "Build it", 2026-10-04 20:37Z).

The gesture inserts the page's OWN words (the PDF text layer inside a rectangle) at a zone as text, provenance mode
"textlayer", through the ledgered chokepoint. Each case violates one property the gesture stands for, on a SANDBOX copy
of the nucl-ex held bundle (E6's patient: the title page's e-mail footnote the converter looped on) beside its PDF:
preview writes nothing; the insert is exactly the words, one ledger event, one record; the undo is exact and pops the
record; an empty rectangle refuses with no write, no event, no record; a bad rect and a page past the count raise; the
derived outcome reads `text-restored` and reverts; the fidelity block never moves. Skips (never passes) when the bundle
or the PDF is not on this machine. Run under the converter's interpreter (pymupdf):
    C:\\Users\\Bndit\\ml\\marker-env\\Scripts\\python.exe test_textlayer_restore.py
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
HELD = LIB / "held" / "af4aebf6f85049f0"
PDF = LIB / "drop" / "done" / "arXiv (nucl-ex) _ Thick-target Yield of 65Cu(alpha,n)68Ga Near Threshold and Imp.pdf"
ZONE, PAGE = 55, 4
RECT = [0.0822, 0.8575, 0.4809, 0.8853]          # E6's fourth, measured rectangle: the footnote band
EMPTY_RECT = [0.0, 0.0, 0.04, 0.015]              # the page's top-left corner: margin, no words


def _fid_sha(b):
    return hashlib.sha256(json.dumps(b.manifest.get("fidelity"), sort_keys=True).encode()).hexdigest()[:16]


class TextlayerRestore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (HELD / "manifest.json").exists() or not PDF.exists():
            raise unittest.SkipTest("the nucl-ex held bundle or its PDF is not on this machine — UNREAD, not a pass")
        cls.tmp = Path(tempfile.mkdtemp(prefix="fp-textlayer-"))
        cls.bundle = cls.tmp / "af4aebf6f85049f0"
        shutil.copytree(HELD, cls.bundle)
        # E7-fix (the blind verifier, 21:03Z): the sandbox starts from the PRE-restoration state whatever the live
        # bundle holds - every trailing textlayer record is undone through the bench's own undo, so the test is not
        # one-shot (its first run passed, the act on the real bundle then made every later run fail: two textlayer
        # records on one page and `_repair_blocks` sees neither). The first-write backup is removed from the copy so a
        # preview that backed up would show (the verifier's mutant M6 survived because the copy carried one).
        b = B.Bench(cls.bundle, pdf=PDF, sandbox=False)
        while (b.manifest.get("repairs") or []) and b.manifest["repairs"][-1].get("mode") == "textlayer":
            b.undo_ledger()
        cls.bak = b.md_path.with_suffix(".md.bench-bak")
        if cls.bak.exists():
            cls.bak.unlink()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        self.b = B.Bench(self.bundle, pdf=PDF, sandbox=False)
        self.sha0 = self.b._sha(self.b.body())
        self.events0 = len(self.b.ledger())
        self.reps0 = len(self.b.manifest.get("repairs", []))
        self.fid0 = _fid_sha(self.b)

    def _unchanged(self):
        b = B.Bench(self.bundle, pdf=PDF, sandbox=False)
        self.assertEqual(b._sha(b.body()), self.sha0, "the body moved")
        self.assertEqual(len(b.ledger()), self.events0, "a ledger event was written")
        self.assertEqual(len(b.manifest.get("repairs", [])), self.reps0, "a provenance record was written")
        self.assertEqual(_fid_sha(b), self.fid0, "the fidelity block moved")

    def test_1_preview_writes_nothing(self):
        pv = self.b.restore_textlayer(ZONE, PAGE, RECT, preview=True)
        self.assertTrue(pv["preview"])
        self.assertEqual(pv["words"], 6)
        self.assertEqual(pv["lines"], 2)
        # the exact text, in reading order (E7-fix: the verifier's mutant M2 - words sorted right to left - survived
        # a containment check)
        self.assertEqual(pv["text"], "zachary.meisel@us.af.mil (Z. Meisel); XSN3YC@uvahealth.org (G.\nHamad)")
        self.assertFalse(self.bak.exists(), "a preview made the first-write backup - it wrote")
        self._unchanged()

    def test_2_insert_undo_exact(self):
        r = self.b.restore_textlayer(ZONE, PAGE, RECT, note="the e-mail footnote, from the page's own text layer")
        self.assertEqual(r["words"], 6)
        self.assertEqual(r["lines"], 4, "a blank, two text lines, one comment")
        self.assertEqual(r["record"]["mode"], "textlayer")
        self.assertEqual(r["record"]["source"], "pdf-textlayer")
        self.assertIsNone(r["record"]["model"])
        b = B.Bench(self.bundle, pdf=PDF, sandbox=False)
        lines = b.body().split("\n")
        at = r["inserted_after_line"]
        self.assertEqual(lines[at], "")
        self.assertEqual(lines[at + 1] + "\n" + lines[at + 2], r["text"])
        self.assertEqual(r["text"], "zachary.meisel@us.af.mil (Z. Meisel); XSN3YC@uvahealth.org (G.\nHamad)")
        self.assertTrue(self.bak.exists(), "the first real write makes the backup")
        self.assertTrue(lines[at + 3].startswith("<!-- restored p4 · pdf-textlayer · 6 words"))
        self.assertEqual(len(b.ledger()), self.events0 + 1, "exactly one event")
        ev = b.ledger()[-1]
        self.assertEqual((ev["gesture"], ev["kind"], ev["sha_before"]), ("textlayer", "addition", self.sha0))
        self.assertEqual(len(b.manifest["repairs"]), self.reps0 + 1)
        self.assertEqual(_fid_sha(b), self.fid0)
        # the derived outcome: real text beats the crop that was already there
        zone = [s for s in b.coverage()["sites"] if s["kind"] == "zone" and s["at"] == ZONE]
        self.assertEqual(zone[0]["outcome"], "text-restored")
        # the scanner sees the block (so unsplit_tables and the readers can move it)
        kinds = [k for _, _, k, _ in b._repair_blocks(lines)]
        self.assertIn("textlayer", kinds)
        # the undo: exact bytes back, the record popped, the undo itself recorded
        u = b.undo_ledger()
        self.assertEqual(u["gesture"], "textlayer")
        b2 = B.Bench(self.bundle, pdf=PDF, sandbox=False)
        self.assertEqual(b2._sha(b2.body()), self.sha0)
        self.assertEqual(len(b2.manifest["repairs"]), self.reps0, "the provenance record outlived its body")
        self.assertEqual(len(b2.ledger()), self.events0 + 2)
        self.assertEqual(b2.ledger()[-1]["reverts"], ev["sha_after"])
        zone = [s for s in b2.coverage()["sites"] if s["kind"] == "zone" and s["at"] == ZONE]
        self.assertEqual(zone[0]["outcome"], "image-restored", "E6's crop is the outcome again")
        self.assertEqual(_fid_sha(b2), self.fid0)

    def test_2b_redo_after_undo_is_undoable(self):
        # E7-fix (the verifier's residue, CORRECTIONS 95): gesture -> undo -> the same gesture -> undo. The redo's
        # sha_after equals the reverted write's, so an undo that identified writes by sha read the redo as already
        # reverted and refused; the ledger now names the reverted write by its seq.
        b = self.b
        d0 = b.undo_depth()
        b.restore_textlayer(ZONE, PAGE, RECT)
        b.undo_ledger()
        r = b.restore_textlayer(ZONE, PAGE, RECT)
        self.assertEqual(b.undo_depth(), d0 + 1, "the redo counts as one more change to walk back")
        u = b.undo_ledger()
        self.assertEqual(u["gesture"], "textlayer")
        self.assertEqual(u["remaining"], d0)
        b2 = B.Bench(self.bundle, pdf=PDF, sandbox=False)
        self.assertEqual(b2._sha(b2.body()), self.sha0)
        self.assertEqual(len(b2.manifest.get("repairs", [])), self.reps0)
        self.assertEqual(b2.ledger()[-1].get("reverts_seq"), r and b2.ledger()[-2]["seq"])
        self.assertEqual(_fid_sha(b2), self.fid0)

    def test_3_empty_rect_refuses(self):
        with self.assertRaises(ValueError):
            self.b.restore_textlayer(ZONE, PAGE, EMPTY_RECT)
        self._unchanged()

    def test_4_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            self.b.restore_textlayer(ZONE, PAGE, [0.5, 0.5, 0.4, 0.6])
        with self.assertRaises(ValueError):
            self.b.restore_textlayer(ZONE, PAGE, [0.1, 0.1, 1.2, 0.2])
        with self.assertRaises(ValueError):
            self.b.restore_textlayer(ZONE, 999, RECT)
        with self.assertRaises(ValueError):
            self.b.restore_textlayer(ZONE, PAGE, "not a rect")
        self._unchanged()


if __name__ == "__main__":
    unittest.main(verbosity=2)
