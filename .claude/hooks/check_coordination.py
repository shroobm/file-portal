#!/usr/bin/env python
"""Stop hook — ERROR-BIN ERR-017 / ERR-018, made mechanical.

WHAT THIS FILE DOES: a Claude Code hook script with one helper, git(), and the rest running top to bottom. It runs
`git status --porcelain -- coordination` in the repository (CLAUDE_PROJECT_DIR, else the fixed File Portal path). When
that folder has uncommitted changes it prints a JSON systemMessage naming up to four of the files; when it is clean, or
git cannot be read, it prints nothing. Exit code is always 0. It reads git state only and writes nothing but stdout.

ERR-017: I committed coordination/ack-fable.json and then, in the same command,
ran a beat announcing it was clean. A beat WRITES that file, so the announcement
was the act that ended the cleanliness. The rule the error produced is an
ORDERING - write, commit, nothing - and the last write must be the commit.

ERR-018 is its twin: a hardcoded `echo "(clean)"` printed one line under a
`git status` that said dirty. A claim about state whose evidence I never asked
for. Codex caught ERR-017; Fable caught ERR-018 by reading its own adjacent
contradictory output.

This fires at the end of every turn and reports the actual state, derived. It is
the check that cannot print the wrong answer, because it has no answer of its own
to print - it prints git's.

Never blocks. A dirty tree mid-work is normal; a dirty coordination/ that nobody
mentioned at the end of a turn is what cost Codex a blocked close today.
"""
import json
import os
import subprocess
import sys

# -- the repository to inspect --
REPO = os.environ.get("CLAUDE_PROJECT_DIR") or "C:/Users/Bndit/Projects/file-portal"


# -- helper: run git in REPO --
def git(*args):
    """Run `git -C REPO <args>` (15 s timeout). Returns its stdout as text on exit 0, otherwise None (also on any
    exception). Read-only as called here."""
    try:
        r = subprocess.run(
            ["git", "-C", REPO] + list(args),
            capture_output=True, text=True, timeout=15,
        )
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None  # failed probe is UNREAD, never "clean"


# -- the check: list uncommitted entries under coordination/ --
out = git("status", "--porcelain", "--", "coordination")
if out is None:
    # Say nothing rather than assert health. A guard that cannot read must not
    # render its blindness as a green — the failure open.sh shipped once already.
    sys.exit(0)

dirty = [l for l in out.splitlines() if l.strip()]
if not dirty:
    sys.exit(0)

# -- output: a systemMessage naming up to four dirty paths (the status line minus its two status columns and space) --
files = ", ".join(l[3:] for l in dirty[:4])
msg = (
    "ERR-017/018: coordination/ is DIRTY at end of turn ({n} file(s): {f}). "
    "If a beat or post ran, the sidecar is uncommitted and the close gate will "
    "block on it - Codex refused to stage it today, correctly. The rule is an "
    "ordering: write, commit, NOTHING. The last write must be the commit."
).format(n=len(dirty), f=files)

print(json.dumps({"systemMessage": msg}))
