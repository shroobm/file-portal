"""S157 E54 (B32 U01 + U05, Codex's 2026-08-27 completion audit, verified at the source S157 E51):

U01 — a restart with pre-existing inbox files must allocate each exactly once (run() used to arm the watch and never
look, so a file that arrived while the service was down waited for a touch that never came).
U05 — a failed allocation must leave a durable terminal outcome in status.json (the exception used to be logged and
nothing written, so the widget waited forever on a job that had already died).

The handler is exercised directly, as in test_allocator.py; `sweep_inbox` is the startup half of run()."""

import json
import logging
from pathlib import Path

from allocator.config import Paths
from allocator.main import InboxHandler, sweep_inbox
from allocator.status import StatusWriter

RULES = """
[defaults]
unmatched_destination = "sorted/misc"
on_collision = "rename"
max_file_size_mb = 1

[[rule]]
category = "documents"
match = ["*.txt"]
destination = "sorted/documents"
"""


def make(tmp_path: Path) -> tuple[InboxHandler, Paths, Path]:
    paths = Paths.from_root(tmp_path / "file-portal")
    paths.ensure_exist()
    (paths.inbox / "documents").mkdir()
    (paths.inbox / "misc").mkdir()
    rules_path = tmp_path / "rules.toml"
    rules_path.write_text(RULES)
    return (
        InboxHandler(paths, rules_path, StatusWriter(paths.logs / "status.json")),
        paths,
        rules_path,
    )


def events(paths: Paths) -> list[dict]:
    p = paths.logs / "status.json"
    return json.loads(p.read_text())["events"] if p.exists() else []


# ---------------------------------------------------------------- U01: the startup sweep


def test_startup_sweep_allocates_preexisting_files_exactly_once(tmp_path):
    handler, paths, _ = make(tmp_path)
    (paths.inbox / "documents" / "a.txt").write_bytes(b"one")
    (paths.inbox / "documents" / "b.txt").write_bytes(b"two")
    (paths.inbox / "misc" / "c.bin").write_bytes(b"three")

    assert sweep_inbox(handler, paths) == 3
    assert (paths.root / "sorted" / "documents" / "a.txt").exists()
    assert (paths.root / "sorted" / "documents" / "b.txt").exists()
    assert (paths.root / "sorted" / "misc" / "c.bin").exists()
    assert not any((paths.inbox / "documents").iterdir())
    allocated = [e for e in events(paths) if e["action"] == "allocated"]
    assert sorted(e["file"] for e in allocated) == ["a.txt", "b.txt", "c.bin"]

    # exactly once: a second sweep finds nothing and records nothing
    assert sweep_inbox(handler, paths) == 0
    assert len(events(paths)) == 3


def test_startup_sweep_skips_in_progress_dotfiles_and_empty_inbox(tmp_path):
    handler, paths, _ = make(tmp_path)
    assert sweep_inbox(handler, paths) == 0  # an empty inbox is a clean zero, not an error
    (paths.inbox / "documents" / ".part-still-arriving.txt").write_bytes(b"partial")
    assert sweep_inbox(handler, paths) == 0
    assert (paths.inbox / "documents" / ".part-still-arriving.txt").exists()
    assert events(paths) == []


def test_negative_control_without_the_sweep_a_preexisting_file_is_never_allocated(tmp_path):
    """The defect as it was: arm nothing, sweep nothing — the file sits. (Proves the sweep is what moves it.)"""
    handler, paths, _ = make(tmp_path)
    (paths.inbox / "documents" / "stuck.txt").write_bytes(b"x")
    assert (paths.inbox / "documents" / "stuck.txt").exists()
    assert events(paths) == []


# ---------------------------------------------------------------- U05: a terminal outcome on failure


def test_failed_allocation_records_a_terminal_rejected_outcome_and_leaves_the_file(
    tmp_path, caplog
):
    handler, paths, rules_path = make(tmp_path)
    rules_path.write_text("this is not valid toml [[[")
    f = paths.inbox / "documents" / "a.txt"
    f.write_bytes(b"hello")

    handler._handle(f)  # must not raise (the observer thread lives) …

    assert "failed to allocate" in caplog.text
    assert f.exists(), "a failed allocation does not move the file (unlike a quarantine)"
    ev = events(paths)
    assert len(ev) == 1
    assert (
        ev[0]["action"] == "rejected"
    )  # … and the outcome reaches status.json, where the widget reads it
    assert ev[0]["file"] == "a.txt" and ev[0]["category"] == "documents"
    assert ev[0]["reason"].startswith("allocation failed: ")
    assert "file left in inbox/documents" in ev[0]["reason"]
    assert "dest" not in ev[0]


def test_negative_control_a_file_that_vanished_under_the_handler_records_nothing(tmp_path, caplog):
    """The exactly-once seam: the sweep and the observer can both see one file; whichever loses finds it gone.
    That is not a failure and must not write a second (false) outcome."""
    caplog.set_level(logging.INFO, logger="file-portal-allocator")
    handler, paths, _ = make(tmp_path)
    f = paths.inbox / "documents" / "a.txt"
    f.write_bytes(b"hello")
    original = handler._allocate

    def allocate_then_lose_the_race(path):
        path.unlink()  # the other path moved it first
        raise FileNotFoundError(str(path))

    handler._allocate = allocate_then_lose_the_race
    try:
        handler._handle(f)
    finally:
        handler._allocate = original
    assert "allocated by another path" in caplog.text
    assert events(paths) == []


def test_control_a_successful_allocation_still_records_allocated_only(tmp_path):
    handler, paths, _ = make(tmp_path)
    f = paths.inbox / "documents" / "ok.txt"
    f.write_bytes(b"fine")
    handler._handle(f)
    ev = events(paths)
    assert [e["action"] for e in ev] == ["allocated"]
