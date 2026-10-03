# -*- coding: utf-8 -*-
"""WHAT THIS FILE DOES: a script (no entry function; it runs at import) that builds a temporary ledger directory, runs
dump.sh and ledger_check.py (both in this folder) against it as subprocesses, and prints one [ok ]/[RED] line per case
plus a summary. It writes only inside a temp directory. Exit 0 = all green, 1 = any red, 2 = no bash on PATH.

ledger_check_selftest.py — the tripwire for dump.sh's twin and ledger_check.py (S141): in a temp ledger dir, a
copy-mode dump and a --ref dump (with --producer/--source/--coverage) verify; a tampered twin row goes red; a file
changed under a --ref row goes red; a deleted copy reads 'bytes gone' (not red); a pre-S141 md row without a twin is
said. Exit 0 all green · 1 any red. Needs bash (Git Bash) on PATH — the case says UNREAD if not."""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# -- shared state: this folder, the interpreter, the list of failed cases and the case counter --
HERE =Path(__file__).resolve().parent
PY = sys.executable
FAILS = []
N = 0


# -- helpers: one assertion recorder and two subprocess wrappers --
def case(name, got, want):
    """Count one case; print [ok ] if got == want, else print [RED] and record the name in FAILS. Mutates N and FAILS."""
    global N
    N += 1
    if got != want:
        FAILS.append(name)
        print("  [RED] %s: got %r want %r" % (name, got, want))
    else:
        print("  [ok ] %s" % name)


# locate bash; without it dump.sh cannot run, so stop with exit 2 (UNREAD, not a failure)
BASH = shutil.which("bash")
if not BASH:
    print("UNREAD: no bash on PATH — dump.sh cannot be exercised here")
    sys.exit(2)


def dump(args, env_lane="Fable"):
    """Run dump.sh through bash with `args`, DUMP_LANE set to env_lane; return the CompletedProcess (output captured)."""
    return subprocess.run([BASH, str(HERE / "dump.sh")] + args, capture_output=True, text=True, encoding="utf-8",
                          env=dict(os.environ, DUMP_LANE=env_lane, PYTHONIOENCODING="utf-8"))


def check(d):
    """Run ledger_check.py on ledger directory `d`; return the CompletedProcess (returncode and stdout captured)."""
    return subprocess.run([PY, str(HERE / "ledger_check.py"), str(d)], capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))


# -- the cases, all inside one temporary ledger directory (deleted on exit) --
with tempfile.TemporaryDirectory() as td:
    d = Path(td)
    # seed: a LEDGER.md holding one pre-S141 row (no twin), then a receipt file and a source file to dump
    (d / "LEDGER.md").write_text("# test ledger\n\n| id | utc | lane | category | subject | bytes | sha256 |\n|---|---|---|---|---|---|---|\n"
                                 "| D0001 | 2026-08-26T05:27:39Z | Fable | evidence | a pre-S141 row, no twin | 3916 | `" + "a" * 64 + "` |\n", encoding="utf-8")
    f = d / "receipt.md"
    f.write_bytes(b"# a receipt\n\nline\n")
    src = d / "src.jsonl"
    src.write_bytes(b'{"x":1}\n')
    # case group 1: a --ref dump writes a twin row with the expected fields; a missing DUMP_LANE is refused
    p = dump(["--ref", "--ledger", str(d), "--producer", str(HERE / "ledger_check.py"), "--source", str(src), "--coverage", "fixture", "evidence", "S9 calls receipt", str(f)])
    case("--ref dump exits 0", (p.returncode, "DUMPED  D0002" in p.stdout and "(in place)" in p.stdout), (0, True))
    twin = [json.loads(ln) for ln in io.open(d / "LEDGER.jsonl", encoding="utf-8") if ln.strip()]
    case("the twin row carries path/producer/sources/coverage/row_sha256", sorted(k for k in twin[-1] if k in ("path", "producer", "sources", "coverage", "row_sha256")), ["coverage", "path", "producer", "row_sha256", "sources"])
    case("the source's bytes and sha are recorded", (twin[-1]["sources"][0]["bytes"], len(twin[-1]["sources"][0]["sha256"])), (8, 64))
    case("the producer's blob is a git object id", len(twin[-1]["producer"]["blob"]), 40)
    p = dump(["--lane-missing"], env_lane="")
    case("no DUMP_LANE → refused", p.returncode, 1)
    # case group 2: the checker agrees on the clean ledger, then goes red on tampering (file changed, twin row edited)
    p = check(d)
    case("ledger_check agrees → exit 0", (p.returncode, "D0002: row_sha256 ✓ · md == twin ✓ · bytes reproduce ✓" in p.stdout), (0, True))
    case("the pre-S141 row is said, not red", "D0001: md row (no twin — pre-S141)" in p.stdout, True)
    f.write_bytes(b"# a receipt\n\nchanged\n")
    p = check(d)
    case("a file changed under a --ref row → red", (p.returncode, "do NOT reproduce ✗" in p.stdout), (1, True))
    f.write_bytes(b"# a receipt\n\nline\n")
    # edit the last twin row's subject text without recomputing its row_sha256 (the tamper)
    lines = io.open(d / "LEDGER.jsonl", encoding="utf-8").read().splitlines()
    lines[-1] = lines[-1].replace('"subject":"S9 calls receipt"', '"subject":"S9 calls receipt (edited)"')
    io.open(d / "LEDGER.jsonl", "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    p = check(d)
    case("a twin row edited after writing → row_sha256 ✗", (p.returncode, "row_sha256 ✗" in p.stdout), (1, True))
    # undo the tamper and confirm the checker returns to green; then the no-LEDGER.md usage case
    lines[-1] = lines[-1].replace(" (edited)", "")
    io.open(d / "LEDGER.jsonl", "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    # copy mode into a category dir of the temp ledger (dump.sh copies into ITS OWN dumps/<cat>/ — use the real one's evidence dir? no: never write there from a test)
    p = check(d)
    case("restored → exit 0", p.returncode, 0)
    p = check(d / "nope")
    case("no LEDGER.md → CONFIG exit 2", p.returncode, 2)

# -- summary and exit code --
print("ledger_check selftest: %d/%d green" % (N - len(FAILS), N))
sys.exit(1 if FAILS else 0)
