"""S149 — the insertion rule, the un-split and the three refuters' cases, exercised on temp bundles through the bench's
own class (no server). Run from prototypes/repair-bench with the marker-env interpreter (bench imports fitz):
    C:/Users/Bndit/ml/marker-env/Scripts/python.exe test_table_boundary.py
The page-side twin is test_table_health.js (node)."""
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


class S149Refuted(unittest.TestCase):
    """The three refuters' findings, each a tripwire now."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="fp-test-s149r-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def bundle(self, body_lines, repairs=None):
        (self.tmp / "book.md").write_text("---\ntitle: t\n---\n" + "\n".join(body_lines), encoding="utf-8")
        (self.tmp / "manifest.json").write_text(json.dumps({"repairs": repairs or []}), encoding="utf-8")
        return bench.Bench(self.tmp)

    def body(self):
        fm, body = bench.split_frontmatter((self.tmp / "book.md").read_text(encoding="utf-8"))
        return body.split("\n")

    def test_two_blocks_trapped_in_one_table_both_leave_in_one_pass(self):
        split = ["# T", "", "| a | b |", "|---|---|", "| 1 | 2 |", "", "![[assets/_repair_p1_1.png]]", "<!-- repair p1 · repair-bench -->",
                 "| 3 | 4 |", "", "![[assets/_repair_p1_2.png]]", "<!-- repair p1 · repair-bench -->", "| 5 | 6 |", "| 7 | 8 |", "", "tail"]
        b = self.bundle(split, [{"id": "fpr-1", "zone_line": 3, "page": 1, "asset": "_repair_p1_1.png", "mode": "crop"},
                                {"id": "fpr-2", "zone_line": 4, "page": 1, "asset": "_repair_p1_2.png", "mode": "crop"}])
        r = b.unsplit_tables()
        self.assertEqual(len(r["moved"]), 2)
        lines = self.body()
        self.assertEqual(lines[2:8], ["| a | b |", "|---|---|", "| 1 | 2 |", "| 3 | 4 |", "| 5 | 6 |", "| 7 | 8 |"], "one unbroken run")
        self.assertEqual(lines[8], "")
        self.assertTrue(lines[9].startswith("![[assets/_repair_p1_1.png"))
        self.assertTrue(lines[12].startswith("![[assets/_repair_p1_2.png"))
        self.assertEqual(bench.Bench(self.tmp).unsplit_tables()["moved"], [], "converged: the second pass moves nothing")
        self.assertEqual(bench.Bench._table_blocks(self.body()), [(2, 3, 7)])

    def test_pipes_inside_a_code_fence_are_not_a_table(self):
        body = ["# T", "", "```", "| not | a | table |", "| still | code |", "```", "", "para", "", "| a | b |", "|---|---|", "| 1 | 2 |"]
        b = self.bundle(body)
        self.assertIsNone(bench.Bench._table_span(body, 3))
        self.assertEqual(bench.Bench._table_span(body, 10), (9, 11))
        r = b.repair(zone_line=4, page=1, image_b64=png1x1())   # a zone on a fence line: no redirect
        self.assertIsNone(r["placed_after_table"])
        self.assertEqual(r["inserted_after_line"], 4)
        # and the un-split leaves a block inside a fence alone
        split = ["```", "| x |", "", "![[assets/_repair_p1_1.png]]", "<!-- repair p1 · repair-bench -->", "| y |", "```"]
        b2 = self.bundle(split, [{"id": "fpr-1", "zone_line": 2, "page": 1, "asset": "_repair_p1_1.png", "mode": "crop"}])
        self.assertEqual(b2.unsplit_tables()["moved"], [])
        self.assertEqual(self.body(), split)

    def test_a_table_without_leading_pipes_is_a_table(self):
        body = ["a | b", "--- | ---", "1 | 2", "3 | 4", "", "tail"]
        b = self.bundle(body)
        self.assertEqual(bench.Bench._table_blocks(body), [(0, 1, 3)])
        r = b.repair(zone_line=1, page=1, image_b64=png1x1())
        self.assertEqual(r["placed_after_table"], [1, 4])
        self.assertEqual(self.body()[0:4], body[0:4])

    def test_a_transcription_record_carries_its_anchor(self):
        body = ["# T", "", "para", "", "| a | b |", "|---|---|", "| 1 | 2 |", "| 3 | 4 |", "", "tail"]
        b = self.bundle(body)
        r = b.transcribe_apply(zone_line=5, page=1, markdown="read text")
        rec = r["record"]
        self.assertEqual(rec["at_line_orig"], 8)
        self.assertEqual(rec["placed_after_table"], [5, 8])
        self.assertEqual(b._adjusted_line(7), 7, "a row above the moved block does not shift")
        self.assertEqual(b._adjusted_line(9), 9 + rec["lines"])

    def test_a_duplicate_asset_name_is_reported_not_stomped(self):
        split = ["| a | b |", "|---|---|", "", "![[assets/_repair_p1_1.png]]", "<!-- repair p1 · repair-bench -->", "| 1 | 2 |", "", "tail"]
        b = self.bundle(split, [{"id": "fpr-OLD", "zone_line": 1, "page": 1, "asset": "_repair_p1_1.png", "mode": "crop", "at_line_orig": 1},
                                {"id": "fpr-REAL", "zone_line": 1, "page": 1, "asset": "_repair_p1_1.png", "mode": "crop"}])
        r = b.unsplit_tables()
        self.assertEqual(r["moved"][0]["record"], "ambiguous")
        self.assertEqual(b.manifest["repairs"][0]["at_line_orig"], 1, "the old record untouched")
        self.assertNotIn("at_line_orig", b.manifest["repairs"][1])
        self.assertEqual(self.body()[0:3], ["| a | b |", "|---|---|", "| 1 | 2 |"], "the table still healed")

    def test_a_moved_block_always_gets_its_blank_line(self):
        split = ["| a | b |", "|---|---|", "![[assets/_repair_p1_1.png]]", "<!-- repair p1 · repair-bench -->", "| 1 | 2 |", "", "tail"]
        b = self.bundle(split, [{"id": "fpr-1", "zone_line": 1, "page": 1, "asset": "_repair_p1_1.png", "mode": "crop"}])
        b.unsplit_tables()
        lines = self.body()
        self.assertEqual(lines[0:3], ["| a | b |", "|---|---|", "| 1 | 2 |"])
        self.assertEqual(lines[3], "", "a blank before the block: a line touching the last row would become a row")
        self.assertTrue(lines[4].startswith("![[assets/"))

    def test_a_transcription_block_trapped_in_a_table_is_moved(self):
        split = ["| a | b |", "|---|---|", "", "read line one", "read line two", "<!-- transcribed p1 · granite-docling-258M · repair-bench -->",
                 "| 1 | 2 |", "", "tail"]
        b = self.bundle(split, [{"id": "fpr-T", "zone_line": 1, "page": 1, "asset": None, "mode": "transcribe", "lines": 4}])
        r = b.unsplit_tables()
        self.assertEqual(len(r["moved"]), 1)
        self.assertEqual(r["moved"][0]["kind"], "transcribe")
        lines = self.body()
        self.assertEqual(lines[0:3], ["| a | b |", "|---|---|", "| 1 | 2 |"])
        self.assertEqual(lines[3], "")
        self.assertEqual(lines[4:7], ["read line one", "read line two", "<!-- transcribed p1 · granite-docling-258M · repair-bench -->"])
        self.assertEqual(b.manifest["repairs"][0]["at_line_orig"], 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
