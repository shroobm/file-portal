"""Exporter tests against REAL git repositories on a temp root -- the assertions read the
bare repo's committed tree (`git cat-file`, `rev-list --count`), not log text, because the
L12 contract is about what the bare repo provably holds. No watcher: export()/sweep() are
called directly, same style as test_main."""

import json
import subprocess

import pytest

from converter.config import Paths
from converter.exporter import Exporter, slugify

SHA_A = "aa11" * 16
SHA_B = "bb22" * 16
IDENT = ["-c", "user.name=test", "-c", "user.email=test@test.invalid"]


def git(repo, *args, check=True):
    proc = subprocess.run(
        ["git", "-C", str(repo), "-c", "commit.gpgsign=false", *args],
        capture_output=True,
        text=True,
    )
    if check:
        assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


@pytest.fixture
def paths(tmp_path):
    p = Paths.from_root(tmp_path / "file-portal")
    p.ensure_exist()
    # Wire the vault pair the way Decision #4 did manually: bare repo + working clone,
    # seeded before any content.
    subprocess.run(
        ["git", "init", "--bare", "-b", "main", str(p.vault_bare)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "clone", str(p.vault_bare), str(p.vault_work)],
        check=True,
        capture_output=True,
    )
    (p.vault_work / ".gitattributes").write_text("* text=auto eol=lf\n")
    git(p.vault_work, "add", ".gitattributes")
    git(p.vault_work, *IDENT, "commit", "-m", "chore: seed")
    git(p.vault_work, "push", "-u", "origin", "main")
    return p


def make_bundle(paths, name, sha):
    bundle = paths.staging / name
    (bundle / "assets").mkdir(parents=True)
    (bundle / f"{name}.md").write_text(f"---\nsource_sha256: {sha}\n---\nbody\n")
    (bundle / "assets" / "page-1.png").write_bytes(b"\x89PNG fake")
    (bundle / "manifest.json").write_text(
        json.dumps({"source": f"{name}.pdf", "source_sha256": sha, "lane": "clean"})
    )
    return bundle


def bare_commits(paths):
    return int(git(paths.vault_bare, "rev-list", "--count", "main"))


def bare_has(paths, rel):
    return (
        subprocess.run(
            ["git", "-C", str(paths.vault_bare), "cat-file", "-e", f"main:{rel}"],
            capture_output=True,
        ).returncode
        == 0
    )


def test_slugify():
    assert slugify("My Paper (1)") == "my-paper-1"
    assert slugify("already-clean") == "already-clean"
    assert slugify("___") == "untitled"
    assert len(slugify("x" * 200)) <= 60


def test_export_happy_path(paths):
    bundle = make_bundle(paths, "My Paper (1)", SHA_A)
    Exporter(paths).export(bundle)

    # Repo-relative Inbox/ — the repo root IS the vault's Library folder (L14).
    dest = f"Inbox/my-paper-1--{SHA_A[:8]}"
    assert not bundle.exists(), "staging copy must be deleted after blob verification"
    assert bare_commits(paths) == 2
    for rel in ("My Paper (1).md", "manifest.json", "assets/page-1.png"):
        assert bare_has(paths, f"{dest}/{rel}"), rel
    # The ingest commit is machine-identified and clean in the worktree.
    assert "file-portal-converter" in git(paths.vault_work, "log", "-1", "--format=%an")
    assert git(paths.vault_work, "status", "--porcelain") == ""


def test_duplicate_sha_is_noop(paths):
    exp = Exporter(paths)
    exp.export(make_bundle(paths, "paper", SHA_A))
    dup = make_bundle(paths, "paper re-drop", SHA_A)  # same source, new conversion
    exp.export(dup)

    assert bare_commits(paths) == 2, "re-ingest must not create a duplicate bundle"
    assert not dup.exists(), "duplicate's staging copy must still be cleared"
    assert not bare_has(paths, f"Inbox/paper-re-drop--{SHA_A[:8]}/manifest.json")


def test_duplicate_detected_after_desktop_filed_it(paths):
    exp = Exporter(paths)
    exp.export(make_bundle(paths, "paper", SHA_A))
    # Desktop files the note out of Inbox/ and pushes -- manifest travels with it.
    src, dst = f"Inbox/paper--{SHA_A[:8]}", f"Filed/paper--{SHA_A[:8]}"
    (paths.vault_work / "Filed").mkdir()
    git(paths.vault_work, "mv", src, dst)
    git(paths.vault_work, *IDENT, "commit", "-m", "file it")
    git(paths.vault_work, "push")

    dup = make_bundle(paths, "paper", SHA_A)
    exp.export(dup)
    assert bare_commits(paths) == 3, "no new ingest commit"
    assert not dup.exists()


def test_git_failure_keeps_staging(paths):
    bundle = make_bundle(paths, "paper", SHA_A)
    paths.vault_bare.rename(paths.vault_bare.with_name("vault.gone"))
    Exporter(paths).export(bundle)
    assert bundle.exists(), "staging must survive any git failure"


def test_push_failure_then_resume(paths):
    bundle = make_bundle(paths, "paper", SHA_A)
    git(paths.vault_work, "remote", "set-url", "--push", "origin", str(paths.root / "nope"))
    Exporter(paths).export(bundle)
    assert bundle.exists(), "no blob in the bare repo yet -- deletion gate must hold"
    assert bare_commits(paths) == 1, "nothing pushed"
    local = int(git(paths.vault_work, "rev-list", "--count", "main"))
    assert local == 2, "the ingest commit itself exists locally"

    git(paths.vault_work, "remote", "set-url", "--push", "origin", str(paths.vault_bare))
    Exporter(paths).export(bundle)
    assert not bundle.exists()
    assert bare_commits(paths) == 2
    assert int(git(paths.vault_work, "rev-list", "--count", "main")) == 2, "resume, not re-commit"
    assert bare_has(paths, f"Inbox/paper--{SHA_A[:8]}/manifest.json")


def test_incomplete_bundle_kept(paths):
    bundle = paths.staging / "broken"
    bundle.mkdir()
    (bundle / "broken.md").write_text("no manifest")
    Exporter(paths).export(bundle)
    assert bundle.exists()
    assert bare_commits(paths) == 1


def test_sweep_exports_and_ignores_dot_dirs(paths):
    a = make_bundle(paths, "one", SHA_A)
    b = make_bundle(paths, "two", SHA_B)
    part = paths.staging / ".part-in-progress"
    part.mkdir()
    Exporter(paths).sweep()
    assert not a.exists() and not b.exists()
    assert part.exists(), "dot-prefixed assembly dirs are not bundles"
    assert bare_commits(paths) == 3
