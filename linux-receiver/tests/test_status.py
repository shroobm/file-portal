"""S108 writer identity on the allocator's status feed.

Two services append to the same logs/status.json (this allocator and the converter), so every
NEW record must name its writer via ``source_component``. Pre-S108 records without the field
are history: they must be carried forward byte-identical, never rewritten to claim an identity
(the widget renders them as "unknown").
"""

import json
from pathlib import Path

from allocator.status import SOURCE_COMPONENT, StatusWriter


def read_events(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["events"]


def test_every_new_record_names_its_writer(tmp_path):
    assert SOURCE_COMPONENT == "allocator"
    path = tmp_path / "status.json"
    writer = StatusWriter(path)
    writer.record("allocated", "a.txt", "documents", dest="sorted/documents/a.txt")
    writer.record("rejected", "b.bin", "documents", reason="no rule matched")

    events = read_events(path)
    assert [e["source_component"] for e in events] == ["allocator", "allocator"]


def test_pre_s108_records_are_never_rewritten(tmp_path):
    path = tmp_path / "status.json"
    legacy = {
        "ts": "2026-01-01T00:00:00+00:00",
        "action": "allocated",
        "file": "old.txt",
        "category": "documents",
    }
    path.write_text(json.dumps({"updated": legacy["ts"], "events": [legacy]}), encoding="utf-8")

    StatusWriter(path).record("skipped", "new.txt", "documents", reason="duplicate")

    events = read_events(path)
    assert events[0] == legacy, "history must not be rewritten to claim an identity"
    assert "source_component" not in events[0]
    assert events[1]["source_component"] == "allocator"
