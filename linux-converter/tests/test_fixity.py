"""WHAT THIS FILE DOES: pytest tests for converter/fixity.py. A fixture builds a real bare vault
repo (plus a work clone) under tmp_path with the git command line; the tests then run check() and
read the receipts.jsonl it wrote and its exit code. Covers a healthy vault, a corrupted object and
a missing vault.

Fixity-check tests against a REAL bare repo on a temp root, same doctrine as
test_exporter: assertions read what the check provably wrote (receipts, exit codes),
corruption is real bytes in a real loose object, not a mock."""

import json
import subprocess

import pytest

from converter.config import Paths
from converter.fixity import check

# -- fixtures and helpers --
IDENT = ["-c", "user.name=test", "-c", "user.email=test@test.invalid"]


@pytest.fixture
def paths(tmp_path):
    """Create a bare vault and a work clone with one committed, pushed note; return the Paths."""
    p = Paths.from_root(tmp_path / "file-portal")
    p.ensure_exist()
    subprocess.run(
        ["git", "init", "--bare", "-b", "main", str(p.vault_bare)], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "clone", str(p.vault_bare), str(p.vault_work)], check=True, capture_output=True
    )
    (p.vault_work / "note.md").write_text("a vaulted note\n")
    for args in (["add", "note.md"], [*IDENT, "commit", "-m", "seed"], ["push", "origin", "main"]):
        subprocess.run(
            ["git", "-C", str(p.vault_work), "-c", "commit.gpgsign=false", *args],
            check=True,
            capture_output=True,
        )
    return p


def receipts(paths):
    """Return the parsed lines of receipts.jsonl under the root as a list of dicts."""
    return [json.loads(ln) for ln in (paths.root / "receipts.jsonl").read_text().splitlines() if ln]


# -- tests --
def test_healthy_vault_passes(paths):
    """A healthy vault returns 0 and writes one pass receipt carrying an 8-character tip."""
    assert check(paths.root) == 0
    (record,) = receipts(paths)
    assert record["outcome"] == "fixity-check"
    assert record["result"] == "pass"
    assert len(record["tip"]) == 8


def test_corrupt_object_fails(paths):
    """A garbled loose object makes check() return 1 and write a fail receipt with an error."""
    # Real corruption: garble the bytes of a loose object in the BARE repo.
    victim = next(
        f
        for f in (paths.vault_bare / "objects").rglob("*")
        if f.is_file() and len(f.parent.name) == 2
    )
    victim.chmod(0o644)  # git stores loose objects read-only
    victim.write_bytes(b"garbage, not zlib")
    assert check(paths.root) == 1
    (record,) = receipts(paths)
    assert record["result"] == "fail"
    assert record["error"]


def test_missing_vault_fails_loudly(paths):
    """A deleted bare repo makes check() return 2 and write a fail receipt saying it is missing."""
    import shutil

    shutil.rmtree(paths.vault_bare)
    assert check(paths.root) == 2
    (record,) = receipts(paths)
    assert record["result"] == "fail"
    assert "missing" in record["error"]
