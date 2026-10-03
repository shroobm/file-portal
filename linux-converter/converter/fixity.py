"""WHAT THIS FILE DOES: runs a weekly integrity check of the bare vault git repository. check(root)
runs `git rev-parse` and `git fsck --strict` against it and appends one "fixity-check" receipt
(pass or fail) to receipts.jsonl; main() is the command-line entry (--root) and exits with
check()'s code (0 pass, 1 fsck/tip failure, 2 vault missing). Run by the systemd timer/service.

Scheduled vault fixity check -- `git fsck` over the bare authoritative vault.

NDSA Levels of Digital Preservation, level 3: fixity is checked at fixed intervals, with
logs. The vault verifies every ingest (the L12 blob gate) but nothing ever RE-verified it
afterward, and NDSA's guidance is explicit that trusting the storage layer alone is not
enough. Runs as the oneshot file-portal-vault-fixity.service, fired weekly by the matching
.timer (Persistent=true, so a week the laptop slept through fires on the next boot).

Outcome is one `fixity-check` receipt in receipts.jsonl (the PREMIS preservation-event
vocabulary's "fixity check" term), pass or fail, with the vault tip it verified. Report-mode:
a fail exits nonzero (the unit shows red) and writes the receipt -- nothing is auto-repaired.
Repair of a corrupt vault is archaeology with Rab, never automation.
"""

import argparse
import subprocess
import sys
from pathlib import Path

from converter.config import DEFAULT_ROOT, Paths
from converter.exporter import VAULT_BRANCH, append_receipt


# -- the check --
def check(root: Path) -> int:
    """Verify the vault under root with git fsck and record a receipt; return the exit code.

    Returns 0 on pass, 1 on fsck failure or unresolvable tip, 2 if the bare repo is missing.
    Side effects: runs git subprocesses, appends a receipt line. Never repairs anything.
    """
    paths = Paths.from_root(root)
    bare = paths.vault_bare
    if not (bare / "HEAD").is_file():
        append_receipt(paths.root, "fixity-check", result="fail", error="vault bare repo missing")
        return 2

    def git(*args: str) -> subprocess.CompletedProcess:
        """Run git against the bare vault with the given arguments; return the finished process."""
        return subprocess.run(
            ["git", "--git-dir", str(bare), *args], capture_output=True, text=True
        )

    # resolve the vault branch tip (first 8 characters), then fsck the whole repository
    tip_proc = git("rev-parse", VAULT_BRANCH)
    tip = tip_proc.stdout.strip()[:8] if tip_proc.returncode == 0 else None
    # --strict tightens object checks; dangling objects are normal git life, not corruption.
    fsck = git("fsck", "--strict", "--no-dangling")
    if fsck.returncode == 0 and tip is not None:
        append_receipt(paths.root, "fixity-check", result="pass", tip=tip)
        return 0
    # failure path: keep the first line of git's complaint (200 chars) in the receipt
    error = (fsck.stderr.strip() or fsck.stdout.strip() or "branch tip unresolvable").splitlines()
    append_receipt(paths.root, "fixity-check", result="fail", tip=tip, error=error[0][:200])
    return 1


# -- command-line entry --
def main() -> None:
    """Parse --root, run check(), and exit the process with its code."""
    parser = argparse.ArgumentParser(description="File Portal vault fixity check")
    parser.add_argument(
        "--root", type=Path, default=DEFAULT_ROOT, help="file-portal root directory"
    )
    sys.exit(check(parser.parse_args().root))


if __name__ == "__main__":
    main()
