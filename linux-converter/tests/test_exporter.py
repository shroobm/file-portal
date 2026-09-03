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


def bare_show(paths, rel):
    return git(paths.vault_bare, "show", f"main:{rel}")


def make_supersede_bundle(
    paths, name, sha, *, verdict="pass", body="remedied body", from_verdict="fail", asset=b"REMEDY"
):
    """A remedy bundle: same source_sha as a vaulted note, plus the opt-in supersede block the
    widget's re-convert authors, and (unless verdict is None) a fidelity verdict."""
    bundle = paths.staging / name
    (bundle / "assets").mkdir(parents=True)
    (bundle / f"{name}.md").write_text(f"---\nsource_sha256: {sha}\n---\n{body}\n")
    (bundle / "assets" / "fig.png").write_bytes(asset)
    manifest = {
        "source": f"{name}.pdf",
        "source_sha256": sha,
        "lane": "scan",
        "supersede": {"reason": "audit-remedy", "from_verdict": from_verdict},
    }
    if verdict is not None:
        manifest["fidelity"] = {"verdict": verdict}
    (bundle / "manifest.json").write_text(json.dumps(manifest))
    return bundle


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


# --- supersede flow (docs/15 §14) ---------------------------------------------------------


def test_supersede_replaces_note_filed_out_of_inbox(paths):
    exp = Exporter(paths)
    exp.export(make_bundle(paths, "beer", SHA_A))
    # Desktop files the note out of Inbox/ and pushes -- supersede must locate it there.
    git(paths.vault_work, "fetch", "origin")
    git(paths.vault_work, "merge", "--ff-only", "origin/main")
    (paths.vault_work / "Filed").mkdir()
    git(paths.vault_work, "mv", f"Inbox/beer--{SHA_A[:8]}", f"Filed/beer--{SHA_A[:8]}")
    git(paths.vault_work, *IDENT, "commit", "-m", "file it")
    git(paths.vault_work, "push")

    exp.export(make_supersede_bundle(paths, "beer", SHA_A, body="the fixed conversion"))

    dest = f"Filed/beer--{SHA_A[:8]}"
    assert bare_has(paths, f"{dest}/beer.md"), "replaced at the FILED path, not recomputed Inbox/"
    assert not bare_has(paths, f"Inbox/beer--{SHA_A[:8]}/beer.md"), "must not resurrect in Inbox/"
    assert "the fixed conversion" in bare_show(paths, f"{dest}/beer.md")
    assert "supersede" in bare_show(paths, f"{dest}/manifest.json")
    assert bare_commits(paths) == 4, "one new supersede commit (seed, file-move, supersede)"
    assert git(paths.vault_work, "status", "--porcelain") == ""


def test_supersede_preserves_old_md_name_when_slug_differs(paths):
    exp = Exporter(paths)
    exp.export(make_bundle(paths, "brain of the firm", SHA_A))  # md == "brain of the firm.md"
    dest = f"Inbox/brain-of-the-firm--{SHA_A[:8]}"
    assert bare_has(paths, f"{dest}/brain of the firm.md")

    # Remedy bundle has a DIFFERENT slug -- supersede must not rename.
    exp.export(make_supersede_bundle(paths, "brain-firm-v2", SHA_A, body="fixed"))

    assert bare_has(paths, f"{dest}/brain of the firm.md"), "old .md name preserved"
    assert not bare_has(paths, f"{dest}/brain-firm-v2.md"), "new slug must never enter the tree"
    assert "fixed" in bare_show(paths, f"{dest}/brain of the firm.md")


def test_supersede_swaps_assets(paths):
    exp = Exporter(paths)
    exp.export(make_bundle(paths, "paper", SHA_A))  # ships assets/page-1.png
    dest = f"Inbox/paper--{SHA_A[:8]}"
    assert bare_has(paths, f"{dest}/assets/page-1.png")

    exp.export(make_supersede_bundle(paths, "paper", SHA_A, asset=b"NEWPNG"))

    assert not bare_has(paths, f"{dest}/assets/page-1.png"), "old asset removed"
    assert bare_has(paths, f"{dest}/assets/fig.png"), "new asset added"
    assert bare_show(paths, f"{dest}/assets/fig.png") == "NEWPNG"


def test_supersede_fail_verdict_refuses_and_keeps_staging(paths):
    exp = Exporter(paths)
    exp.export(make_bundle(paths, "paper", SHA_A))
    dup = make_supersede_bundle(paths, "paper", SHA_A, verdict="fail")
    exp.export(dup)

    assert dup.exists(), "a still-failing remedy must never land -- staging kept"
    assert bare_commits(paths) == 2, "no supersede commit"
    assert "body" in bare_show(paths, f"Inbox/paper--{SHA_A[:8]}/paper.md"), "vault untouched"


def test_supersede_missing_fidelity_refuses(paths):
    exp = Exporter(paths)
    exp.export(make_bundle(paths, "paper", SHA_A))
    dup = make_supersede_bundle(paths, "paper", SHA_A, verdict=None)  # no fidelity block
    exp.export(dup)

    assert dup.exists(), "missing fidelity is not 'pass' -- fail closed, staging kept"
    assert bare_commits(paths) == 2


def test_supersede_ambiguous_refuses(paths):
    exp = Exporter(paths)
    exp.export(make_bundle(paths, "paper", SHA_A))
    # Hand-plant a SECOND vaulted note with the same source_sha (bypassing dedup) so the
    # locate step sees two -- it must refuse rather than guess.
    second = paths.vault_work / "Inbox" / f"dup--{SHA_A[:8]}"
    (second / "assets").mkdir(parents=True)
    (second / "dup.md").write_text("second")
    (second / "manifest.json").write_text(json.dumps({"source_sha256": SHA_A}))
    git(paths.vault_work, "add", "-A")
    git(paths.vault_work, *IDENT, "commit", "-m", "hand-plant dup")
    git(paths.vault_work, "push")

    dup = make_supersede_bundle(paths, "paper", SHA_A)
    exp.export(dup)
    assert dup.exists(), "ambiguous match must keep staging"
    assert bare_commits(paths) == 3, "no supersede commit on ambiguity"


def test_supersede_miss_creates_new_note(paths):
    # Intent says supersede but the sha is not vaulted -> a normal create.
    bundle = make_supersede_bundle(paths, "fresh", SHA_B)
    Exporter(paths).export(bundle)

    dest = f"Inbox/fresh--{SHA_B[:8]}"
    assert bare_has(paths, f"{dest}/fresh.md"), "created a new note under its own slug"
    assert bare_commits(paths) == 2
    assert not bundle.exists()


def test_supersede_noop_identical_bytes(paths):
    exp = Exporter(paths)
    exp.export(make_bundle(paths, "paper", SHA_A))  # md body "body", asset b"\x89PNG fake"

    # A remedy whose note bytes + asset are byte-identical to the vaulted note: only the
    # manifest gains the supersede block -> no swap, no empty commit.
    dup = paths.staging / "paper"
    (dup / "assets").mkdir(parents=True)
    (dup / "paper.md").write_text(f"---\nsource_sha256: {SHA_A}\n---\nbody\n")  # == make_bundle
    (dup / "assets" / "page-1.png").write_bytes(b"\x89PNG fake")  # == make_bundle
    (dup / "manifest.json").write_text(
        json.dumps(
            {
                "source": "paper.pdf",
                "source_sha256": SHA_A,
                "lane": "clean",
                "supersede": {"reason": "audit-remedy", "from_verdict": "fail"},
                "fidelity": {"verdict": "pass"},
            }
        )
    )
    exp.export(dup)

    assert bare_commits(paths) == 2, "byte-identical remedy must not mint an empty commit"
    assert not dup.exists(), "no-op still clears the staging copy"
    assert git(paths.vault_work, "status", "--porcelain") == "", "worktree restored clean"


def test_no_supersede_field_still_skips(paths):
    # Regression guard on today's create-only contract: a same-sha re-drop WITHOUT the field
    # is the old no-op, never a replace.
    exp = Exporter(paths)
    exp.export(make_bundle(paths, "paper", SHA_A))
    dup = make_bundle(paths, "paper re-drop", SHA_A)  # no supersede block
    exp.export(dup)
    assert bare_commits(paths) == 2
    assert not dup.exists()
    assert "body" in bare_show(paths, f"Inbox/paper--{SHA_A[:8]}/paper.md")


def test_supersede_commit_without_push_resumes(paths):
    exp = Exporter(paths)
    exp.export(make_bundle(paths, "paper", SHA_A))
    dest = f"Inbox/paper--{SHA_A[:8]}"

    # Break the push URL: the supersede commits locally but cannot land.
    git(paths.vault_work, "remote", "set-url", "--push", "origin", str(paths.root / "nope"))
    bundle = make_supersede_bundle(paths, "paper", SHA_A, body="the remedy")
    exp.export(bundle)
    assert bundle.exists(), "no blob in the bare repo yet -- deletion gate holds"
    assert bare_commits(paths) == 2, "nothing pushed"
    assert int(git(paths.vault_work, "rev-list", "--count", "main")) == 3, (
        "supersede committed locally"
    )

    # Fix the push and resume: re-push, not re-commit.
    git(paths.vault_work, "remote", "set-url", "--push", "origin", str(paths.vault_bare))
    exp.export(bundle)
    assert not bundle.exists()
    assert bare_commits(paths) == 3, "resumed the SAME commit, no second supersede"
    assert "the remedy" in bare_show(paths, f"{dest}/paper.md")


# ---------------------------------------------------------------------------
# Spot-check sampling + degeneration surfacing (2026-08-16).
# ---------------------------------------------------------------------------
def read_receipts(paths):
    records = []
    for ln in (paths.root / "receipts.jsonl").read_text().splitlines():
        try:
            records.append(json.loads(ln))
        except ValueError:  # a deliberately torn seed line in one test
            continue
    return records


def test_spot_check_fires_on_exactly_the_nth_accept(paths, monkeypatch):
    import converter.exporter as exporter_mod

    monkeypatch.setattr(exporter_mod, "SPOT_CHECK_EVERY", 3)
    ex = Exporter(paths)
    shas = [f"{i:02x}11" * 16 for i in range(4)]
    for i, sha in enumerate(shas):
        ex.export(make_bundle(paths, f"book-{i}", sha))
    exported = [r for r in read_receipts(paths) if r["outcome"] == "exported"]
    assert [r.get("spot_check") for r in exported] == [None, None, True, None]


def test_spot_check_counter_survives_restart(paths, monkeypatch):
    # The counter derives from receipts.jsonl, not process memory: a NEW Exporter instance
    # (a service restart) must keep counting where the old one stopped.
    import converter.exporter as exporter_mod

    monkeypatch.setattr(exporter_mod, "SPOT_CHECK_EVERY", 2)
    Exporter(paths).export(make_bundle(paths, "first", SHA_A))
    Exporter(paths).export(make_bundle(paths, "second", SHA_B))
    exported = [r for r in read_receipts(paths) if r["outcome"] == "exported"]
    assert [r.get("spot_check") for r in exported] == [None, True]


def test_spot_check_counts_only_exported_outcomes_and_tolerates_torn_lines(paths, monkeypatch):
    import converter.exporter as exporter_mod

    monkeypatch.setattr(exporter_mod, "SPOT_CHECK_EVERY", 2)
    # Pre-seed: one non-exported receipt and one torn line -- neither may count.
    (paths.root / "receipts.jsonl").write_text(
        json.dumps({"outcome": "skip", "bundle": "x"}) + "\n" + '{"outcome": "expo'
    )
    ex = Exporter(paths)
    ex.export(make_bundle(paths, "one", SHA_A))
    ex.export(make_bundle(paths, "two", SHA_B))
    exported = [r for r in read_receipts(paths) if r["outcome"] == "exported"]
    assert [r.get("spot_check") for r in exported] == [None, True]


def test_degeneration_flag_reaches_the_receipt(paths):
    bundle = make_bundle(paths, "loopy", SHA_A)
    manifest = json.loads((bundle / "manifest.json").read_text())
    manifest["degeneration"] = {"flagged": True, "repeated_lines": 0, "md_lines": 9, "worst": []}
    (bundle / "manifest.json").write_text(json.dumps(manifest))
    Exporter(paths).export(bundle)
    exported = [r for r in read_receipts(paths) if r["outcome"] == "exported"]
    assert exported[0]["degeneration_flagged"] is True
    # The bundle still exported -- report mode holds nothing.
    assert bare_has(paths, f"Inbox/loopy--{SHA_A[:8]}/manifest.json")


def test_clean_manifest_adds_no_flag_keys(paths):
    Exporter(paths).export(make_bundle(paths, "plain", SHA_A))
    exported = [r for r in read_receipts(paths) if r["outcome"] == "exported"]
    assert "degeneration_flagged" not in exported[0]
    assert "spot_check" not in exported[0]


# ---------------------------------------------------------------------------
# J28 (2026-09-03): blocks.json -- J24's block records -- at the vault seam. Whether they belong
# inside the vault git repo is Rab's call and is NOT made yet, so these pin BOTH answers of the
# SHIP_BLOCKS_TO_VAULT lever on BOTH export paths, plus the manifest that must state which one
# happened. The defect they were written for: the supersede path copies .md + assets/ +
# manifest.json BY NAME and nothing else, and its L12 gate walks the COMMITTED tree, so the drop
# was silent -- every other supersede test above passed straight through it.
# ---------------------------------------------------------------------------
BLOCKS_A = json.dumps(
    {"blocks": [{"id": "/page/0/Text/1", "page": 0, "bbox": [1, 2, 3, 4]}]}
).encode()
BLOCKS_B = json.dumps(
    {"blocks": [{"id": "/page/7/Table/2", "page": 7, "bbox": [5, 6, 7, 8]}]}
).encode()


def plant_blocks(bundle, payload=BLOCKS_A):
    """Drop a blocks.json beside the manifest, where marker_blocks.py writes it into the bundle.
    Returns its TRUE byte size -- the number the exported manifest has to report."""
    (bundle / "blocks.json").write_bytes(payload)
    return len(payload)


def bare_size(paths, rel):
    """Committed blob size in bytes (`cat-file -s`), not len() of the shown text -- `git show`
    comes back through .strip() and would undercount by the trailing newline."""
    return int(git(paths.vault_bare, "cat-file", "-s", f"main:{rel}"))


def vault_manifest(paths, dest):
    return json.loads(bare_show(paths, f"{dest}/manifest.json"))


def ship_blocks(monkeypatch, value):
    """Flip the J28 lever for one test (same shape as the SPOT_CHECK_EVERY patches above)."""
    import converter.exporter as exporter_mod

    monkeypatch.setattr(exporter_mod, "SHIP_BLOCKS_TO_VAULT", value)


def test_blocks_held_is_recorded_in_the_manifest_not_silently_dropped(paths):
    # No monkeypatch: this is the lever as the module ships it (OUT, pending Rab's word).
    bundle = make_bundle(paths, "paper", SHA_A)
    n = plant_blocks(bundle)
    Exporter(paths).export(bundle)

    dest = f"Inbox/paper--{SHA_A[:8]}"
    assert not bundle.exists(), "the L12 gate must not demand a blob it was told not to create"
    assert bare_commits(paths) == 2, "the export still lands"
    assert not bare_has(paths, f"{dest}/blocks.json"), "lever is OUT -- the vault must not have it"
    assert vault_manifest(paths, dest)["blocks"] == {
        "present_in_bundle": True,
        "shipped": False,
        "bytes": n,
    }
    # PLANTED DECOY: `bytes` has a wrong-answer shape -- an implementation that sized the file
    # blocks.json is written beside (manifest.json) still yields a plausible int, and an
    # equality-only assertion on some other run's number would not catch it. Assert the true
    # size AND that it is not the decoy's; the guard only means something because they differ.
    manifest_bytes = bare_size(paths, f"{dest}/manifest.json")
    assert n != manifest_bytes, "decoy degenerate: plant a blocks.json of a different size"
    assert vault_manifest(paths, dest)["blocks"]["bytes"] != manifest_bytes


def test_blocks_ship_byte_identical_when_the_lever_says_in(paths, monkeypatch):
    ship_blocks(monkeypatch, True)
    bundle = make_bundle(paths, "paper", SHA_A)
    n = plant_blocks(bundle)
    Exporter(paths).export(bundle)

    dest = f"Inbox/paper--{SHA_A[:8]}"
    assert bare_has(paths, f"{dest}/blocks.json"), "lever is IN -- the vault must carry it"
    assert bare_size(paths, f"{dest}/blocks.json") == n, "byte-identical, not re-serialized"
    assert bare_show(paths, f"{dest}/blocks.json") == BLOCKS_A.decode()
    assert vault_manifest(paths, dest)["blocks"] == {
        "present_in_bundle": True,
        "shipped": True,
        "bytes": n,
    }


def test_bundle_without_blocks_records_absence(paths):
    # "no block records" and "block records deliberately left behind" must not read the same.
    Exporter(paths).export(make_bundle(paths, "plain", SHA_A))
    dest = f"Inbox/plain--{SHA_A[:8]}"
    assert vault_manifest(paths, dest)["blocks"] == {"present_in_bundle": False}
    assert not bare_has(paths, f"{dest}/blocks.json")


def test_supersede_carries_blocks_when_the_lever_says_in(paths, monkeypatch):
    ship_blocks(monkeypatch, True)
    exp = Exporter(paths)
    exp.export(make_bundle(paths, "paper", SHA_A))  # vaulted before J24: no block records
    dest = f"Inbox/paper--{SHA_A[:8]}"
    assert not bare_has(paths, f"{dest}/blocks.json")

    remedy = make_supersede_bundle(paths, "paper", SHA_A, body="the remedy")
    n = plant_blocks(remedy, BLOCKS_B)
    exp.export(remedy)

    # J28 itself: the Damodaran re-convert is the first bundle to walk this path with block
    # records in it, and before the fix they were dropped here without a word.
    assert bare_has(paths, f"{dest}/blocks.json"), "the remedy's block records must ship too"
    assert bare_show(paths, f"{dest}/blocks.json") == BLOCKS_B.decode()
    assert bare_size(paths, f"{dest}/blocks.json") == n
    assert vault_manifest(paths, dest)["blocks"]["shipped"] is True
    assert not remedy.exists(), "staging cleared -- the L12 gate saw every committed blob"


def test_supersede_held_records_it_and_stale_block_records_do_not_survive(paths, monkeypatch):
    ship_blocks(monkeypatch, True)
    exp = Exporter(paths)
    first = make_bundle(paths, "paper", SHA_A)
    plant_blocks(first, BLOCKS_A)
    exp.export(first)
    dest = f"Inbox/paper--{SHA_A[:8]}"
    assert bare_show(paths, f"{dest}/blocks.json") == BLOCKS_A.decode()

    # The lever flips OUT between the create and the remedy. The vaulted records index markdown
    # the remedy just replaced -- like assets/, they must not outlive the note they describe.
    ship_blocks(monkeypatch, False)
    remedy = make_supersede_bundle(paths, "paper", SHA_A, body="the remedy")
    n = plant_blocks(remedy, BLOCKS_B)
    exp.export(remedy)

    assert "the remedy" in bare_show(paths, f"{dest}/paper.md"), "the swap itself happened"
    assert not bare_has(paths, f"{dest}/blocks.json"), "stale block records must not survive"
    assert vault_manifest(paths, dest)["blocks"] == {
        "present_in_bundle": True,
        "shipped": False,
        "bytes": n,
    }
