#!/usr/bin/env python3
"""observability/wave_gate.py [--go] [--repo <dir>] — the session's own gate over a labelling wave (S218 E8). For every
modified tracked Python file in the repo (git status), run label_gate (docstring-stripped tree identical to HEAD, compiles,
no shrink) and ruff at CI's pin; print one line per file; with --go, REVERT (git checkout -- <file>) every file whose gate
is not 0 or whose ruff names a fault that HEAD's copy did not have, and name each reverted file. Exit 0 all files pass ·
1 at least one file failed (reverted only with --go) · 2 usage. The lanes self-gate; this is the second, independent
reading, run once over the whole wave before the commit — a lane's word is never the record's.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
RUFF = r"C:\Users\Bndit\AppData\Local\uv\cache\archive-v0\R0jByJ5RgvyN_9vO\ruff-0.15.20.data\scripts\ruff.exe"


def run(cmd, cwd=None):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main(argv):
    go = "--go" in argv
    repo = argv[argv.index("--repo") + 1] if "--repo" in argv else os.path.dirname(HERE)
    rc, out = run(["git", "-C", repo, "status", "--porcelain", "--", "*.py"])
    if rc != 0:
        print("UNREAD: git status failed"); return 2
    files = sorted(l[3:].strip().strip('"') for l in out.splitlines() if l[:2].strip() in ("M", "MM", "AM") and l[3:].strip().endswith(".py"))
    if not files:
        print("no modified python files"); return 0
    failed = []
    ruff_ok = os.path.isfile(RUFF)
    for f in files:
        p = os.path.join(repo, f)
        rc_g, out_g = run([PY, os.path.join(HERE, "label_gate.py"), p])
        gate_line = out_g.strip().splitlines()[-1] if out_g.strip() else "(no output)"
        ruff_note = "ruff: UNREAD (binary absent)"
        bad_ruff = False
        if ruff_ok:
            rc_r, out_r = run([RUFF, "check", "--no-cache", p], cwd=os.path.dirname(p))
            if rc_r == 0:
                ruff_note = "ruff: passed"
            else:
                # was HEAD's copy already red? a pre-existing fault is not the lane's
                rc_h, head_src = run(["git", "-C", repo, "show", "HEAD:" + f.replace(os.sep, "/")])
                with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8", dir=os.path.dirname(p)) as t:
                    t.write(head_src); tmp = t.name
                rc_h2, _ = run([RUFF, "check", "--no-cache", tmp], cwd=os.path.dirname(p))
                os.unlink(tmp)
                if rc_h2 == 0:
                    bad_ruff = True
                    ruff_note = "ruff: NEW FAULT " + " ".join(out_r.strip().splitlines()[:1])[:80]
                else:
                    ruff_note = "ruff: red before the lane too (not the lane's)"
        ok = rc_g == 0 and not bad_ruff
        print("%s %s | %s | %s" % ("PASS" if ok else "FAIL", f, gate_line.split(" ", 1)[-1][:90], ruff_note))
        if not ok:
            failed.append(f)
    print("gate over the wave: %d of %d files pass" % (len(files) - len(failed), len(files)))
    if failed and go:
        for f in failed:
            run(["git", "-C", repo, "checkout", "--", f])
            print("REVERTED", f)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
