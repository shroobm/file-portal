"""Exporter (L11/L12): ships converted bundles from library/staging/ into the vault repo.

Transport is the wiring resolved in Open Decision #4: a non-bare working clone at
<root>/vault-work whose origin is the local bare repo <root>/vault.git; the Desktop's
Obsidian vault pulls from that bare repo over Tailscale SSH. This module never initializes
or repairs either repository -- exactly one side initializes, and that already happened.
If the repos are missing the export fails loudly and the staging copy stays put.

Placement is Open Decision #6: every bundle lands at Library/Inbox/<slug>--<sha256[:8]>/
in VAULT terms — repo-relative that is Inbox/<slug>--<sha256[:8]>/, because the repo root is
the vault's Library folder — with its assets/ nested inside the bundle folder. No tag or folder mapping, and no
[[link]] minting (Decision #5) -- the exporter copies bundle bytes, it does not read them.

Invariants, in the order the code enforces them:
- Creates new notes only, never edits existing ones: the dedup check runs first, the
  commit is pathspec-scoped to the new bundle directory, and a *committed* path is never
  overwritten (only an uncommitted stray from a previously failed run is cleaned).
- Re-ingesting an identical source_sha256 is a no-op with a log line: the full sha is
  grepped over committed manifest.json files in the BARE repo, so a bundle the Desktop has
  filed out of Inbox/ still counts (the manifest travels with the note).
- L12 deletion gate: the staging copy is removed only after the push succeeded AND
  `git cat-file -e` confirms the commit and every bundle file's blob IN THE BARE REPO --
  never on write-success alone. Any git failure leaves staging intact; the startup sweep
  retries on the next service start.
"""

import json
import logging
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler

from converter.config import Paths

logger = logging.getLogger("file-portal-converter")

VAULT_BRANCH = "main"  # HEAD of the bare repo is pinned to refs/heads/main (Decision #4)
# Decision #6's "Library/Inbox/<slug>--<sha8>" is VAULT-relative; the repo root already IS
# the vault's Library folder (Decision #4: only Library/ is a repo), so repo-relative it is
# plain Inbox/ (L14 — the doubled path shipped as Library/Library/Inbox/ in the vault).
INBOX_REL = Path("Inbox")

# Machine-produced commits identify themselves; hand commits keep the user's identity.
GIT_IDENTITY = [
    "-c",
    "user.name=file-portal-converter",
    "-c",
    "user.email=converter@file-portal.invalid",
]


class ExportError(Exception):
    """A git step failed or a precondition did not hold; staging must be kept."""


def slugify(name: str) -> str:
    """Filesystem/URL-safe bundle slug: lowercase, non-alphanumerics collapsed to '-'."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    slug = slug[:60].rstrip("-")
    return slug or "untitled"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
    )


def _git_check(repo: Path, *args: str) -> str:
    proc = _git(repo, *args)
    if proc.returncode != 0:
        raise ExportError(f"git {' '.join(args)}: {proc.stderr.strip() or proc.stdout.strip()}")
    return proc.stdout.strip()


class Exporter:
    """Serializes all vault-repo work behind one lock (startup sweep and watchdog events
    run on different threads; git operations must never interleave)."""

    def __init__(self, paths: Paths):
        self.paths = paths
        self._lock = threading.Lock()

    def sweep(self) -> None:
        """Export bundles that landed while the service was down (no inotify replay)."""
        for entry in sorted(self.paths.staging.iterdir()):
            if entry.is_dir() and not entry.name.startswith("."):
                self.export(entry)

    def export(self, bundle_dir: Path) -> None:
        # A single bad bundle must not kill the observer thread or block later exports.
        with self._lock:
            try:
                self._export(bundle_dir)
            except ExportError as exc:
                logger.error("EXPORT-FAIL %s: %s (staging copy kept)", bundle_dir.name, exc)
            except Exception:
                logger.exception("EXPORT-FAIL %s (staging copy kept)", bundle_dir.name)

    def _export(self, bundle_dir: Path) -> None:
        if not bundle_dir.is_dir() or bundle_dir.name.startswith("."):
            return
        vault_work, vault_bare = self.paths.vault_work, self.paths.vault_bare
        if not (vault_work / ".git").exists() or not vault_bare.is_dir():
            raise ExportError(
                f"vault repos not wired ({vault_work} / {vault_bare}) -- this module never "
                "initializes them (Decision #4: exactly one side initializes)"
            )

        manifest_path = bundle_dir / "manifest.json"
        if not manifest_path.is_file():
            raise ExportError("no manifest.json -- not a published bundle")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        source_sha = manifest["source_sha256"]

        # The Desktop may have pushed filing moves; commit on top of them, not behind them.
        _git_check(vault_work, "fetch", "origin")
        _git_check(vault_work, "merge", "--ff-only", f"origin/{VAULT_BRANCH}")

        # Dedup on the FULL source sha, against the bare repo (what the vault actually has,
        # not what this clone has committed-but-maybe-not-pushed).
        grep = _git(
            vault_bare, "grep", "-q", "-F", source_sha, VAULT_BRANCH, "--", "*manifest.json"
        )
        if grep.returncode == 0:
            logger.info(
                "EXPORT-SKIP %s: source_sha256 %s already in vault -- no-op, staging copy removed",
                bundle_dir.name,
                source_sha[:8],
            )
            shutil.rmtree(bundle_dir)
            return
        if grep.returncode > 1:
            raise ExportError(f"dedup grep failed: {grep.stderr.strip()}")

        target_rel = INBOX_REL / f"{slugify(bundle_dir.name)}--{source_sha[:8]}"
        target = vault_work / target_rel

        # Resume point: a previous run may have committed but failed to push (service died,
        # bare repo unreachable). Committed content is never re-copied or touched.
        committed = _git(vault_work, "cat-file", "-e", f"HEAD:{target_rel}/manifest.json")
        if committed.returncode != 0:
            if target.exists():
                # Uncommitted stray from a failed copy -- machine-produced and unpushed, so
                # cleaning it is not an edit of an existing note.
                _git(vault_work, "rm", "-r", "--cached", "--ignore-unmatch", "--", str(target_rel))
                shutil.rmtree(target)
            # Same .part- pattern as every other hop: assemble hidden, publish by rename.
            tmp = target.parent / f".part-{target.name}"
            if tmp.exists():
                shutil.rmtree(tmp)
            tmp.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(bundle_dir, tmp)
            tmp.rename(target)
            _git_check(vault_work, "add", "--", str(target_rel))
            _git_check(
                vault_work,
                *GIT_IDENTITY,
                "commit",
                "-m",
                f"ingest: {target_rel.name} ({manifest.get('source', bundle_dir.name)}, "
                f"lane={manifest.get('lane', '?')})",
                "--",
                str(target_rel),
            )

        _git_check(vault_work, "push", "origin", VAULT_BRANCH)
        commit_sha = _git_check(vault_work, "rev-parse", "HEAD")

        # L12 gate: the commit and every file's blob must be readable from the BARE repo.
        _git_check(vault_bare, "cat-file", "-e", f"{commit_sha}^{{commit}}")
        for file in sorted(p for p in bundle_dir.rglob("*") if p.is_file()):
            rel = file.relative_to(bundle_dir)
            _git_check(vault_bare, "cat-file", "-e", f"{commit_sha}:{target_rel / rel}")

        shutil.rmtree(bundle_dir)
        logger.info(
            "EXPORTED %s -> %s (commit %s pushed + blob-verified, staging copy removed)",
            bundle_dir.name,
            target_rel,
            commit_sha[:8],
        )


class ExportHandler(FileSystemEventHandler):
    """Watches library/staging/ (non-recursive). The converter publishes bundles by atomic
    rename within staging, which is an on_moved; a manual cp -r arrives as on_created and
    gets a stability wait, mirroring the inbox handler's event model."""

    def __init__(self, exporter: Exporter):
        self.exporter = exporter

    def on_moved(self, event):
        if event.is_directory and not Path(event.dest_path).name.startswith("."):
            self.exporter.export(Path(event.dest_path))

    def on_created(self, event):
        # The dot-check must happen BEFORE the stability wait: the converter assembles two
        # dot-prefixed temp dirs inside staging per bundle, and their created events would
        # otherwise each hold the dispatch thread for the full timeout (the dir gets renamed
        # away, so its manifest never appears -- observed live as a 2x60s export delay).
        if not event.is_directory:
            return
        bundle_dir = Path(event.src_path)
        if bundle_dir.name.startswith("."):
            return
        self._wait_until_stable(bundle_dir)
        self.exporter.export(bundle_dir)

    @staticmethod
    def _wait_until_stable(bundle_dir: Path, interval: float = 0.5, timeout: float = 60.0):
        """Block until the bundle's file list + sizes are unchanged across one interval and
        manifest.json exists (it is written last by assemble, and a copy without it is still
        in flight). Gives up after `timeout` and lets export() judge what is there."""
        deadline = time.monotonic() + timeout
        last = None
        while time.monotonic() < deadline:
            if not bundle_dir.is_dir():
                # Renamed away or already consumed -- nothing to wait for (rglob on a
                # missing dir yields [] rather than raising, which would spin here until
                # the timeout).
                return
            try:
                snapshot = [
                    (str(p), p.stat().st_size) for p in sorted(bundle_dir.rglob("*")) if p.is_file()
                ]
            except OSError:
                return
            if snapshot == last and (bundle_dir / "manifest.json").exists():
                return
            last = snapshot
            time.sleep(interval)
