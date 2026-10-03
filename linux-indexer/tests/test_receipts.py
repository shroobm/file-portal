"""WHAT THIS FILE DOES: pytest tests for indexer.receipts.append_receipt: the byte shape of a
written line, healing of a torn last line, and the never-raises promise. Each test writes only
into pytest's tmp_path; no network, no store.

Mirror copy in linux-converter/tests/test_exporter.py (the torn-line seed test): the helper
is duplicated by design, so is its test. The byte shape of a line is what the widget's seam
test pins (windows-widget/src-tauri/src/receipts.rs)."""

import json

from indexer.receipts import append_receipt


# -- line shape --
def test_line_shape_matches_the_exporter_byte_for_byte(tmp_path):
    """One receipt gives one JSON line: key order ts, outcome, then fields; UTC timestamp."""
    append_receipt(tmp_path, "indexed", result="pass", tip="50896d15", bundles=6)

    line = (tmp_path / "receipts.jsonl").read_text()
    record = json.loads(line)
    assert list(record) == ["ts", "outcome", "result", "tip", "bundles"]
    assert line == json.dumps(record, ensure_ascii=False) + "\n", "default separators, one newline"
    assert record["ts"].endswith("+00:00") and len(record["ts"]) == 25


# -- failure handling --
def test_torn_last_line_is_healed_not_glued(tmp_path):
    """A file ending mid-line (no newline) gets a newline first, so the new record stands alone."""
    torn = json.dumps({"outcome": "skip", "bundle": "x"}) + "\n" + '{"outcome": "expo'
    (tmp_path / "receipts.jsonl").write_text(torn)

    append_receipt(tmp_path, "indexed", result="pass")

    lines = (tmp_path / "receipts.jsonl").read_text().splitlines()
    assert len(lines) == 3, "the torn line stays torn on its own line; ours is whole"
    assert json.loads(lines[2])["outcome"] == "indexed"


def test_never_raises_when_the_file_cannot_be_written(tmp_path):
    """When a directory sits where receipts.jsonl should be, append_receipt returns quietly."""
    blocker = tmp_path / "receipts.jsonl"
    blocker.mkdir()  # a directory where the file should be: open() fails
    append_receipt(tmp_path, "indexed", result="pass")  # must not raise
