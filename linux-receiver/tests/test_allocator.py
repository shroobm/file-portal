"""Unit tests for the InboxHandler: allocation, collision policies, quarantine, guards,
and the status feed. The handler is exercised directly (no observer thread needed)."""

import json
from pathlib import Path

import pytest

from allocator.config import Paths
from allocator.main import InboxHandler
from allocator.status import StatusWriter

RULES = """
[defaults]
unmatched_destination = "sorted/misc"
on_collision = "{policy}"
max_file_size_mb = 1

[[rule]]
category = "documents"
match = ["*.txt"]
destination = "sorted/documents"
"""


def make_handler(tmp_path: Path, policy: str = "rename") -> tuple[InboxHandler, Paths]:
    paths = Paths.from_root(tmp_path / "file-portal")
    paths.ensure_exist()
    (paths.inbox / "documents").mkdir()
    rules_path = tmp_path / "rules.toml"
    rules_path.write_text(RULES.format(policy=policy))
    status = StatusWriter(paths.logs / "status.json")
    return InboxHandler(paths, rules_path, status), paths


def drop(paths: Paths, name: str, content: bytes = b"hello") -> Path:
    file_path = paths.inbox / "documents" / name
    file_path.write_bytes(content)
    return file_path


def read_status(paths: Paths) -> list[dict]:
    return json.loads((paths.logs / "status.json").read_text())["events"]


def test_matching_file_is_allocated(tmp_path):
    handler, paths = make_handler(tmp_path)
    dropped = drop(paths, "a.txt")
    handler._handle(dropped)

    assert not dropped.exists()
    assert (paths.root / "sorted/documents/a.txt").read_bytes() == b"hello"
    (event,) = read_status(paths)
    assert event["action"] == "allocated"
    assert event["file"] == "a.txt"
    assert event["dest"] == "sorted/documents/a.txt"


def test_unmatched_file_goes_to_misc(tmp_path):
    handler, paths = make_handler(tmp_path)
    handler._handle(drop(paths, "a.bin"))
    assert (paths.root / "sorted/misc/a.bin").exists()


def test_collision_rename_appends_suffix(tmp_path):
    handler, paths = make_handler(tmp_path, policy="rename")
    handler._handle(drop(paths, "a.txt", b"first"))
    handler._handle(drop(paths, "a.txt", b"second"))

    assert (paths.root / "sorted/documents/a.txt").read_bytes() == b"first"
    assert (paths.root / "sorted/documents/a (1).txt").read_bytes() == b"second"


def test_collision_overwrite_replaces(tmp_path):
    handler, paths = make_handler(tmp_path, policy="overwrite")
    handler._handle(drop(paths, "a.txt", b"first"))
    handler._handle(drop(paths, "a.txt", b"second"))

    assert (paths.root / "sorted/documents/a.txt").read_bytes() == b"second"
    assert not (paths.root / "sorted/documents/a (1).txt").exists()


def test_collision_skip_leaves_file_in_inbox(tmp_path):
    handler, paths = make_handler(tmp_path, policy="skip")
    handler._handle(drop(paths, "a.txt", b"first"))
    second = drop(paths, "a.txt", b"second")
    handler._handle(second)

    assert (paths.root / "sorted/documents/a.txt").read_bytes() == b"first"
    assert second.exists(), "skipped file must stay in the inbox"
    assert read_status(paths)[-1]["action"] == "skipped"


def test_oversized_file_is_quarantined(tmp_path):
    handler, paths = make_handler(tmp_path)  # max_file_size_mb = 1
    big = drop(paths, "big.txt", b"x" * (2 * 1024 * 1024))
    handler._handle(big)

    assert not big.exists()
    assert (paths.quarantine / "big.txt").exists()
    (event,) = read_status(paths)
    assert event["action"] == "rejected"
    assert "max_file_size_mb" in event["reason"]


def test_quarantine_collision_renames_not_overwrites(tmp_path):
    handler, paths = make_handler(tmp_path)
    handler._handle(drop(paths, "big.txt", b"x" * (2 * 1024 * 1024)))
    handler._handle(drop(paths, "big.txt", b"y" * (2 * 1024 * 1024)))

    assert (paths.quarantine / "big.txt").exists()
    assert (paths.quarantine / "big (1).txt").exists()


def test_files_inside_quarantine_are_ignored(tmp_path):
    handler, paths = make_handler(tmp_path)
    quarantined = paths.quarantine / "stuck.txt"
    quarantined.write_bytes(b"x")
    handler._handle(quarantined)

    assert quarantined.exists(), "quarantined files must never be re-processed"
    assert not (paths.logs / "status.json").exists()


def test_dotfiles_are_ignored_as_in_progress_temp_files(tmp_path):
    handler, paths = make_handler(tmp_path)
    temp = drop(paths, ".a.txt.3xY9Zq")
    handler._handle(temp)

    assert temp.exists(), "rsync-style temp files must be left for the completing rename"


def test_missing_file_is_a_noop(tmp_path):
    handler, paths = make_handler(tmp_path)
    handler._handle(paths.inbox / "documents" / "ghost.txt")
    assert not (paths.logs / "status.json").exists()


def test_allocation_errors_do_not_propagate(tmp_path, caplog):
    handler, paths = make_handler(tmp_path)
    bad_rules = tmp_path / "rules.toml"
    bad_rules.write_text("this is not valid toml [[[")

    handler._handle(drop(paths, "a.txt"))  # must not raise and kill the observer thread
    assert "failed to allocate" in caplog.text


def test_status_feed_is_bounded_and_survives_corruption(tmp_path):
    paths = Paths.from_root(tmp_path / "file-portal")
    paths.ensure_exist()
    status = StatusWriter(paths.logs / "status.json", max_events=3)

    (paths.logs / "status.json").write_text("{corrupt")
    for i in range(5):
        status.record("allocated", f"f{i}.txt", "documents", dest=f"sorted/documents/f{i}.txt")

    events = read_status(paths)
    assert [e["file"] for e in events] == ["f2.txt", "f3.txt", "f4.txt"]


def test_wait_until_stable_returns_when_size_stops_changing(tmp_path):
    file_path = tmp_path / "f.bin"
    file_path.write_bytes(b"x" * 10)
    InboxHandler._wait_until_stable(file_path, interval=0.01, timeout=1.0)


def test_wait_until_stable_handles_vanishing_file(tmp_path):
    InboxHandler._wait_until_stable(tmp_path / "gone.bin", interval=0.01, timeout=1.0)


@pytest.mark.parametrize(
    ("existing", "policy", "expected"),
    [
        (False, "rename", "a.txt"),
        (True, "rename", "a (1).txt"),
        (True, "overwrite", "a.txt"),
        (True, "skip", None),
    ],
)
def test_resolve_collision_matrix(tmp_path, existing, policy, expected):
    dest = tmp_path / "a.txt"
    if existing:
        dest.write_bytes(b"x")
    resolved = InboxHandler._resolve_collision(dest, policy)
    assert (resolved.name if resolved else None) == expected
