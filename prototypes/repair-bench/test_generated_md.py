"""WHAT THIS FILE DOES: a unittest module that builds throwaway bundle folders in the temp directory and checks that
bench.Bench still opens a bundle when a generated REPAIRS.md sits beside the one real .md body, and still refuses
(SystemExit) when a second real .md exists or only the report exists. Writes only to temp folders it removes again.

S163 E4 — SYM-030's tripwire: a generated REPAIRS.md beside a bundle never makes the bundle un-benchable. The defect (S79):
`bench.Bench(dir)` demanded exactly one .md and the ledger's final report was the second, so declaring a patient done made it
permanently un-openable; the fix is `GENERATED_MD` (bench.py, the patient scan). Exercised on temp bundles through the bench's own
class (no server). Run from prototypes/repair-bench with the marker-env interpreter (bench imports fitz):
    C:/Users/Bndit/ml/marker-env/Scripts/python.exe test_generated_md.py
Each case has its negative control: a SECOND REAL .md still refuses (the scan discriminates — "ignore every extra .md" would pass
the fix's case and fail this one), and a bundle holding ONLY the report has no body and refuses too."""
import atexit
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
# -- environment setup: a throwaway pipeline folder, then import the bench module under test --
# setdefault evaluates its argument even when FP_PIPELINE is already set, so the throwaway is made either way - and is removed at exit either way
_PIPE_TMP = tempfile.mkdtemp(prefix="fp-test-pipe-")
atexit.register(shutil.rmtree, _PIPE_TMP, True)   # S215 round nine: it was never removed (one fp-test-pipe-* left per run)
os.environ.setdefault("FP_PIPELINE", _PIPE_TMP)
import bench  # noqa: E402

# -- fixture: the lines of the sample book body written by setUp --
BODY = ["# T", "", "para one", "", "para two"]


class S163GeneratedMd(unittest.TestCase):
    """The SYM-030 cases: a generated report beside the body is ignored; other extra .md files are not."""

    def setUp(self):
        """Create a fresh temp bundle holding book.md (front matter + BODY) and an empty-repairs manifest.json."""
        self.tmp = Path(tempfile.mkdtemp(prefix="fp-test-s163-"))
        (self.tmp / "book.md").write_text("---\ntitle: t\n---\n" + "\n".join(BODY), encoding="utf-8")
        (self.tmp / "manifest.json").write_text(json.dumps({"repairs": []}), encoding="utf-8")

    def tearDown(self):
        """Delete the temp bundle created by setUp."""
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_generated_report_beside_the_body_is_ignored(self):
        """SYM-030 (a): REPAIRS.md (the ledger's final report, docs/28 §3) sits beside book.md — the bundle opens, the body is book.md."""
        (self.tmp / "REPAIRS.md").write_text("# Repairs\n\nthe report\n", encoding="utf-8")
        b = bench.Bench(self.tmp)
        self.assertEqual(b.md_path, self.tmp / "book.md")
        self.assertFalse(b.pdf_only)

    def test_generated_md_set_names_the_report(self):
        """SYM-030 (b): the exclusion is by NAME — the set in the scan holds exactly the ledger's report file name."""
        src = (HERE / "bench.py").read_text(encoding="utf-8")
        self.assertIn('GENERATED_MD = {"REPAIRS.md"}', src)

    def test_second_real_md_still_refuses(self):
        """SYM-030 (c) NEGATIVE CONTROL: a second REAL .md (not a generated report) is still 'expected exactly one .md' — the scan discriminates."""
        (self.tmp / "other.md").write_text("# other\n", encoding="utf-8")
        with self.assertRaises(SystemExit) as cm:
            bench.Bench(self.tmp)
        self.assertIn("expected exactly one .md", str(cm.exception))
        self.assertIn("found 2", str(cm.exception))

    def test_report_only_bundle_has_no_body(self):
        """SYM-030 (d) NEGATIVE CONTROL: a folder holding ONLY the generated report has no body — refused as 'found 0', never opened on the report."""
        (self.tmp / "book.md").unlink()
        (self.tmp / "REPAIRS.md").write_text("# Repairs\n", encoding="utf-8")
        with self.assertRaises(SystemExit) as cm:
            bench.Bench(self.tmp)
        self.assertIn("found 0", str(cm.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
