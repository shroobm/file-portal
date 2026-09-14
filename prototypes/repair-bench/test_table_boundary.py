"""S149 — the insertion rule and the un-split, exercised on a temp bundle through the bench's own class (no server).
Run from the scratch bench directory with the marker-env interpreter (bench imports fitz)."""
import base64
import json
import os
import shutil
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
os.environ.setdefault("FP_PIPELINE", tempfile.mkdtemp(prefix="fp-test-pipe-"))
import bench  # noqa: E402


def png1x1() -> str:
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    raw = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)) \
        + chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff")) + chunk(b"IEND", b"")
    return base64.b64encode(raw).decode()


TABLE = ["| a | b | c |", "|---|---|---|", "| 1 | 2 | 3 |", "| 4 | 5 | 6 |"]
BODY = ["# T", "", "para one", "", *TABLE, "", "para two", "", "tail"]


class S149TableBoundary(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="fp-test-s149-"))
        (self.tmp / "book.md").write_text("---\ntitle: t\n---\n" + "\n".join(BODY), encoding="utf-8")
        (self.tmp / "manifest.json").write_text(json.dumps({"repairs": []}), encoding="utf-8")
        self.b = bench.Bench(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def body_lines(self):
        fm, body = bench.split_frontmatter((self.tmp / "book.md").read_text(encoding="utf-8"))
        return body.split("\n")

    def test_table_span(self):
        self.assertEqual(bench.Bench._table_span(BODY, 4), (4, 7))
        self.assertEqual(bench.Bench._table_span(BODY, 6), (4, 7))
        self.assertIsNone(bench.Bench._table_span(BODY, 2))
        self.assertIsNone(bench.Bench._table_span(BODY, 99))

    def test_a_paste_at_a_table_header_lands_after_the_table(self):
        # the header row is body line 5 (1-based): the S149 split case
        r = self.b.repair(zone_line=5, page=1, image_b64=png1x1())
        lines = self.body_lines()
        self.assertEqual(r["placed_after_table"], [5, 8])
        self.assertEqual(r["inserted_after_line"], 8)
        self.assertEqual(lines[4:8], TABLE, "the table run is intact")
        self.assertEqual(lines[8], "")
        self.assertTrue(lines[9].startswith("![[assets/"))
        self.assertTrue(lines[10].startswith("<!-- repair p1"))
        rec = self.b.manifest["repairs"][-1]
        self.assertEqual(rec["placed_after_table"], [5, 8])
        self.assertEqual(rec["at_line_orig"], 8)
        self.assertEqual(rec["zone_line"], 5)

    def test_negative_control_a_paste_in_a_paragraph_lands_right_after_it(self):
        r = self.b.repair(zone_line=3, page=1, image_b64=png1x1())   # "para one"
        lines = self.body_lines()
        self.assertIsNone(r["placed_after_table"])
        self.assertEqual(r["inserted_after_line"], 3)
        self.assertEqual(lines[2], "para one")
        self.assertEqual(lines[3], "")
        self.assertTrue(lines[4].startswith("![[assets/"))
        self.assertNotIn("placed_after_table", self.b.manifest["repairs"][-1])

    def test_a_paste_at_the_last_row_is_already_after_the_table(self):
        r = self.b.repair(zone_line=8, page=1, image_b64=png1x1())   # the last row
        self.assertIsNone(r["placed_after_table"])
        self.assertEqual(r["inserted_after_line"], 8)
        self.assertEqual(self.body_lines()[4:8], TABLE)

    def test_the_drift_ledger_uses_where_the_lines_went(self):
        self.b.repair(zone_line=5, page=1, image_b64=png1x1())        # placed after line 8
        # a zone on the table's third row (line 7) sits ABOVE the inserted lines: no shift
        self.assertEqual(self.b._adjusted_line(7), 7)
        # a zone below them shifts by the three lines
        self.assertEqual(self.b._adjusted_line(10), 13)

    def test_unsplit_moves_a_pair_out_of_a_table_and_is_idempotent(self):
        split = ["# T", "", "| a | b | c |", "", "![[assets/_repair_p1_1.png]]", "<!-- repair p1 · repair-bench -->",
                 "|---|---|---|", "| 1 | 2 | 3 |", "| 4 | 5 | 6 |", "", "tail"]
        (self.tmp / "book.md").write_text("---\ntitle: t\n---\n" + "\n".join(split), encoding="utf-8")
        (self.tmp / "manifest.json").write_text(json.dumps({"repairs": [
            {"id": "fpr-x", "zone_line": 3, "page": 1, "asset": "_repair_p1_1.png", "mode": "crop", "by": "repair-bench"}]}), encoding="utf-8")
        b = bench.Bench(self.tmp)
        r = b.unsplit_tables()
        self.assertEqual(len(r["moved"]), 1)
        lines = self.body_lines()
        self.assertEqual(lines[2:6], ["| a | b | c |", "|---|---|---|", "| 1 | 2 | 3 |", "| 4 | 5 | 6 |"], "the delimiter follows the header again")
        self.assertEqual(lines[6], "")
        self.assertTrue(lines[7].startswith("![[assets/_repair_p1_1.png"))
        self.assertTrue(lines[8].startswith("<!-- repair p1"))
        rec = b.manifest["repairs"][0]
        self.assertEqual(rec["placed_after_table"], [3, 6])
        self.assertEqual(rec["at_line_orig"], 6)
        self.assertIn("unsplit", rec)
        ev = b.ledger()
        self.assertEqual(ev[-1]["gesture"], "unsplit-table")
        # idempotent
        self.assertEqual(bench.Bench(self.tmp).unsplit_tables()["moved"], [])

    def test_unsplit_leaves_a_pair_outside_a_table_alone(self):
        ok = ["# T", "", "para", "", "![[assets/_repair_p1_1.png]]", "<!-- repair p1 · repair-bench -->", "", *TABLE]
        (self.tmp / "book.md").write_text("---\ntitle: t\n---\n" + "\n".join(ok), encoding="utf-8")
        b = bench.Bench(self.tmp)
        self.assertEqual(b.unsplit_tables()["moved"], [])
        self.assertEqual(self.body_lines(), ok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
