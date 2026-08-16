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
from datetime import datetime, timezone
from pathlib import Path

from watchdog.events import FileSystemEventHandler

from converter.config import Paths

logger = logging.getLogger("file-portal-converter")

VAULT_BRANCH = "main"  # HEAD of the bare repo is pinned to refs/heads/main (Decision #4)
# Decision #6's "Library/Inbox/<slug>--<sha8>" is VAULT-relative; the repo root already IS
# the vault's Library folder (Decision #4: only Library/ is a repo), so repo-relative it is
# plain Inbox/ (L14 — the doubled path shipped as Library/Library/Inbox/ in the vault).
INBOX_REL = Path("Inbox")

# Stage C2 (docs/19 §3.3, Rab signed S58): the seam receipt. Every EXPORT-* outcome used to
# exist ONLY in this service's journal — a machine the Desktop cannot read (docs/19 law 12) —
# so the desktop's story of a book ended at `shipped` and the vault's answer had to be fetched
# by a human running journalctl. One JSON line per outcome lands here instead, and the widget
# tails it over the ssh channel it already uses for bless.
#
# Deliberately NOT inside the vault repo (the two rejected alternatives were receipts committed
# to the notes' own history, and a side branch): the vault holds notes, not machine records,
# and this module's vault-touching code stays exactly as risky as it was — the addition is an
# append to a plain file.
RECEIPTS_NAME = "receipts.jsonl"

# Spot-check sampling (2026-08-16): every Nth ACCEPTED export is flagged for Rab's eyes even
# though its verdicts all passed — every mature pipeline assumes its confidence signal
# sometimes lies (FADGI 3rd ed. inspects "10 images or 10% of each batch, whichever is
# larger"; AWS A2I ships a sample-regardless-of-confidence condition; Michigan/TCP sampled 5%
# against 99.995%). At this pipeline's batch size the FADGI floor collapses to "every 10th".
# The counter derives from receipts.jsonl itself (count of prior `exported` outcomes), so it
# is deterministic, stateless, and restart-proof. Report-mode: the flag rides the receipt;
# nothing is held. N is Rab's number — promote to converter.toml when he wants to tune it.
SPOT_CHECK_EVERY = 10

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

    def _receipt(self, outcome: str, bundle_dir: Path, **fields) -> None:
        """Append one seam receipt (RECEIPTS_NAME above). Best-effort in every direction: a
        receipt that cannot be written costs a warning and nothing else — telemetry must never
        cost an export (the same rule the Desktop's events.emit follows)."""
        try:
            record = {
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "outcome": outcome,
                "bundle": bundle_dir.name,
                **fields,
            }
            receipts_path = self.paths.root / RECEIPTS_NAME
            # A crash mid-append can leave a torn final line with no newline; appending
            # straight onto it would glue THIS record into the garbage and lose both. Heal
            # the boundary: if the file doesn't end in a newline, start with one (the torn
            # line stays torn — readers already skip unparseable lines — but this record
            # survives). Observed shape, not hypothetical: S76 took two power cuts mid-run.
            lead = ""
            try:
                with open(receipts_path, "rb") as check:
                    check.seek(-1, 2)
                    if check.read(1) != b"\n":
                        lead = "\n"
            except OSError:
                pass  # missing or empty file needs no lead
            with open(receipts_path, "a", encoding="utf-8") as fh:
                fh.write(lead + json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:  # noqa: BLE001
            logger.warning(
                "receipt %s for %s could not be written (export unaffected)",
                outcome,
                bundle_dir.name,
            )

    def _exported_count(self) -> int:
        """Count prior `exported` receipts — the spot-check counter's source of truth."""
        try:
            with open(self.paths.root / RECEIPTS_NAME, encoding="utf-8") as fh:
                count = 0
                for line in fh:
                    try:
                        if json.loads(line).get("outcome") == "exported":
                            count += 1
                    except ValueError:
                        continue  # a torn line must not break counting
                return count
        except OSError:
            return 0

    def _read_bless_marker(self, bundle_dir: Path, manifest: dict, verdict) -> dict | None:
        """docs/18 §5.4 (S56): a human-bless marker lets a `flag` verdict through the supersede
        guard. Valid iff it parses, its source_sha256 matches the staged manifest's, and the
        staged verdict is exactly `flag` -- a degeneration `fail` stays refused even WITH a
        marker (defense in depth: the widget refuses to author those, and this side refuses to
        honor them). Never raises; anything invalid => None and the guard holds."""
        path = bundle_dir / "bless.json"
        if not path.exists():
            return None
        try:
            marker = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            logger.warning(
                "EXPORT-BLESS-INVALID %s: unreadable bless.json ignored", bundle_dir.name
            )
            self._receipt("bless-invalid", bundle_dir, why="unreadable")
            return None
        if marker.get("source_sha256") != manifest.get("source_sha256"):
            logger.warning(
                "EXPORT-BLESS-INVALID %s: bless source_sha mismatch -- ignored", bundle_dir.name
            )
            self._receipt("bless-invalid", bundle_dir, why="sha mismatch")
            return None
        if verdict != "flag":
            logger.warning(
                "EXPORT-BLESS-INVALID %s: bless on verdict %r refused (flag only)",
                bundle_dir.name,
                verdict,
            )
            self._receipt("bless-invalid", bundle_dir, why=f"verdict {verdict} (flag only)")
            return None
        return {
            "by": marker.get("by", "rab"),
            "ts": marker.get("ts"),
            "reason": marker.get("reason", "human-bless"),
            "from_verdict": "flag",
        }

    def export(self, bundle_dir: Path) -> None:
        # A single bad bundle must not kill the observer thread or block later exports.
        with self._lock:
            try:
                self._export(bundle_dir)
            except ExportError as exc:
                logger.error("EXPORT-FAIL %s: %s (staging copy kept)", bundle_dir.name, exc)
                self._receipt("failed", bundle_dir, error=str(exc)[:200])
            except Exception as exc:  # noqa: BLE001 — logged with its traceback below
                logger.exception("EXPORT-FAIL %s (staging copy kept)", bundle_dir.name)
                self._receipt("failed", bundle_dir, error=f"{type(exc).__name__}: {exc}"[:200])

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

        # A deliberate audit remedy carries an opt-in `supersede` provenance block, authored by
        # NOTHING but the widget's re-convert click (docs/15 §14). Its absence => behave exactly
        # as before: a matching source_sha is a create-only no-op. Its presence is a named, opt-in
        # exception that REPLACES the vaulted note in place. Accidental re-drops of the same PDF
        # carry no field and so still skip, by construction.
        supersede = manifest.get("supersede")
        if supersede is not None:
            # Verdict guard first (SIGNED, fail-closed): supersede ONLY on an incoming `pass` --
            # OR, since S56 (docs/18 §5.4, Rab signed 2026-07-31: "pass, or flag with bless"),
            # an incoming `flag` accompanied by a VALID human-bless marker (bless.json beside
            # the manifest, sha-bound, widget-authored). A remedy that did not actually fix the
            # note -- or whose audit never ran (a MISSING fidelity block is not "pass") -- must
            # never overwrite the vault on its own say-so.
            verdict = (manifest.get("fidelity") or {}).get("verdict")
            blessed = self._read_bless_marker(bundle_dir, manifest, verdict)
            if not (verdict == "pass" or (verdict == "flag" and blessed is not None)):
                logger.info(
                    "EXPORT-SUPERSEDE-HELD %s: incoming verdict %r is not pass (and no valid "
                    "bless) -- vault untouched, staging copy kept",
                    bundle_dir.name,
                    verdict,
                )
                self._receipt("supersede-held", bundle_dir, verdict=verdict, sha=source_sha[:16])
                return
            if blessed is not None:
                # Fold the bless provenance into the manifest BEFORE any vault write: the vault
                # must never pretend a blessed note passed on its own merits. The marker file
                # itself is NOT deleted here -- it dies with the staging dir after the L12 gate,
                # so a failed export retries as still-blessed on the next sweep.
                manifest["blessed"] = blessed
                manifest_path.write_text(
                    json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
                )
                logger.info(
                    "EXPORT-BLESSED %s: flag verdict accepted on human bless (by=%s, ts=%s)",
                    bundle_dir.name,
                    blessed.get("by"),
                    blessed.get("ts"),
                )
                self._receipt(
                    "blessed",
                    bundle_dir,
                    by=blessed.get("by"),
                    bless_ts=blessed.get("ts"),
                    sha=source_sha[:16],
                )
            # Locate the LIVE note by its full source_sha in the BARE repo -- never recompute the
            # Inbox/ path, the Desktop may have filed the note out of Inbox/.
            loc = _git(
                vault_bare, "grep", "-l", "-F", source_sha, VAULT_BRANCH, "--", "*manifest.json"
            )
            if loc.returncode > 1:
                raise ExportError(f"supersede locate grep failed: {loc.stderr.strip()}")
            prefix = f"{VAULT_BRANCH}:"  # `git grep <rev>` prefixes every hit with "<rev>:"
            matches = [
                line[len(prefix) :] if line.startswith(prefix) else line
                for line in loc.stdout.splitlines()
                if line.strip()
            ]
            if len(matches) > 1:
                raise ExportError(
                    f"supersede ambiguous: source_sha {source_sha[:8]} is vaulted at {matches} "
                    "-- refusing to guess which note to overwrite, staging copy kept"
                )
            if len(matches) == 1:
                self._supersede_replace(bundle_dir, supersede, Path(matches[0]))
                return
            # 0 matches: intent said supersede but nothing is vaulted -> fall through to a normal
            # create (do NOT run the dedup skip -- the sha is absent, it would not skip anyway).
            logger.info(
                "EXPORT-SUPERSEDE-MISS %s: source_sha %s not in vault -- creating a new note",
                bundle_dir.name,
                source_sha[:8],
            )
            self._receipt("supersede-miss", bundle_dir, sha=source_sha[:16])
        else:
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
                self._receipt("skip", bundle_dir, sha=source_sha[:16])
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
        extra = {}
        # Surface the linux-lane degeneration verdict at the seam (docs/29: a measured value
        # that reaches nobody is the defect) — a flagged-but-published conversion must be
        # visible in the receipt the Desktop tails, not only in this machine's journal.
        if (manifest.get("degeneration") or {}).get("flagged"):
            extra["degeneration_flagged"] = True
        nth = self._exported_count() + 1
        if SPOT_CHECK_EVERY and nth % SPOT_CHECK_EVERY == 0:
            extra["spot_check"] = True
            logger.info(
                "SPOT-CHECK %s -- accepted export #%d, flagged for human review (every %d)",
                bundle_dir.name,
                nth,
                SPOT_CHECK_EVERY,
            )
        self._receipt(
            "exported",
            bundle_dir,
            note=target_rel.as_posix(),
            commit=commit_sha[:8],
            sha=source_sha[:16],
            **extra,
        )

    def _supersede_replace(self, bundle_dir: Path, supersede: dict, manifest_rel: Path) -> None:
        """Replace an already-vaulted note in place with a passing remedy re-convert (docs/15
        §14). Identity is preserved: the live note's existing `.md` filename and folder stay put
        (a re-convert may compute a different slug, and a rename would break `[[wikilinks]]` and
        move the note between folders). Only contents change -- the markdown under its OLD name,
        a fully swapped assets/, and the manifest. The L12 deletion gate is the create path's:
        push, then `cat-file -e` the commit and every ACTUALLY-committed blob in the BARE repo
        before staging is removed. Called only once the verdict guard passed and exactly one
        vaulted note matched the source_sha (locate-don't-assume happens in the caller)."""
        vault_work, vault_bare = self.paths.vault_work, self.paths.vault_bare
        target_rel = manifest_rel.parent
        target = vault_work / target_rel

        # Identity to preserve: the live note's .md filename, read from the committed tree --
        # never recomputed from the incoming bundle's slug.
        tree = _git_check(
            vault_work, "ls-tree", "--name-only", f"HEAD:{target_rel.as_posix()}"
        ).splitlines()
        old_md = [n for n in tree if n.endswith(".md")]
        if len(old_md) != 1:
            raise ExportError(
                f"supersede: expected exactly one .md in {target_rel} at HEAD, found {old_md}"
            )
        old_md_name = old_md[0]

        new_md = [p for p in bundle_dir.iterdir() if p.is_file() and p.suffix == ".md"]
        if len(new_md) != 1:
            raise ExportError(
                f"supersede: expected exactly one .md in staging bundle {bundle_dir.name}, "
                f"found {sorted(p.name for p in new_md)}"
            )

        # Replace contents in place. The new markdown is written under the OLD name; the new
        # bundle's own slug never enters the tree. assets/ is fully swapped; manifest overwritten.
        _git(
            vault_work,
            "rm",
            "-r",
            "--quiet",
            "--ignore-unmatch",
            "--",
            f"{target_rel.as_posix()}/assets",
        )
        shutil.rmtree(target / "assets", ignore_errors=True)
        if (bundle_dir / "assets").is_dir():
            shutil.copytree(bundle_dir / "assets", target / "assets")
        shutil.copyfile(new_md[0], target / old_md_name)
        shutil.copyfile(bundle_dir / "manifest.json", target / "manifest.json")
        _git_check(vault_work, "add", "--", target_rel.as_posix())

        changed = [
            line
            for line in _git_check(
                vault_work, "diff", "--cached", "--name-only", "HEAD"
            ).splitlines()
            if line
        ]
        manifest_path = f"{target_rel.as_posix()}/manifest.json"
        if not changed:
            # Resume: a prior run committed this exact supersede but the push did not land.
            # Re-push and re-verify rather than minting a second commit.
            logger.info(
                "EXPORT-SUPERSEDE-RESUME %s: %s already committed -- re-pushing + re-verifying",
                bundle_dir.name,
                target_rel,
            )
        elif changed == [manifest_path]:
            # Only the provenance block differs -> the note bytes are identical -> nothing to
            # remedy. Don't mint an empty supersede commit; restore the worktree and stop.
            _git_check(vault_work, "checkout", "HEAD", "--", target_rel.as_posix())
            logger.info(
                "EXPORT-SUPERSEDE-NOOP %s: remedy is byte-identical to the vaulted note -- "
                "no swap, staging copy removed",
                bundle_dir.name,
            )
            self._receipt("supersede-noop", bundle_dir, note=target_rel.as_posix())
            shutil.rmtree(bundle_dir)
            return
        else:
            reason = supersede.get("reason", "supersede")
            from_verdict = supersede.get("from_verdict", "?")
            _git_check(
                vault_work,
                *GIT_IDENTITY,
                "commit",
                "-m",
                f"supersede: {target_rel.name} ({reason}, {from_verdict}→pass)",
                "--",
                target_rel.as_posix(),
            )
            logger.info(
                "EXPORT-SUPERSEDE %s -> %s (%s, %s->pass)",
                bundle_dir.name,
                target_rel,
                reason,
                from_verdict,
            )

        _git_check(vault_work, "push", "origin", VAULT_BRANCH)
        commit_sha = _git_check(vault_work, "rev-parse", "HEAD")

        # L12 gate: the commit and every committed blob must be readable from the BARE repo.
        # The .md basename changed under supersede, so iterate the paths ACTUALLY committed
        # (git ls-tree of the commit), not the staging bundle's filenames.
        _git_check(vault_bare, "cat-file", "-e", f"{commit_sha}^{{commit}}")
        committed = _git_check(
            vault_work, "ls-tree", "-r", "--name-only", commit_sha, "--", target_rel.as_posix()
        ).splitlines()
        for rel in committed:
            if rel:
                _git_check(vault_bare, "cat-file", "-e", f"{commit_sha}:{rel}")

        shutil.rmtree(bundle_dir)
        logger.info(
            "EXPORTED-SUPERSEDE %s -> %s (commit %s pushed + blob-verified, staging removed)",
            bundle_dir.name,
            target_rel,
            commit_sha[:8],
        )
        self._receipt(
            "exported-supersede",
            bundle_dir,
            note=target_rel.as_posix(),
            commit=commit_sha[:8],
            reason=supersede.get("reason", "supersede"),
            from_verdict=supersede.get("from_verdict", "?"),
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
