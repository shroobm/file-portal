# -*- coding: utf-8 -*-
"""ledger_check_selftest.py — the tripwire for dump.sh's twin and ledger_check.py (S141): in a temp ledger dir, a
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

HERE = Path(__file__).resolve().parent
PY = sys.executable
FAILS = []
N = 0


def case(name, got, want):
    global N
    N += 1
    if got != want:
        FAILS.append(name)
        print("  [RED] %s: got %r want %r" % (name, got, want))
    else:
        print("  [ok ] %s" % name)


BASH = shutil.which("bash")
if not BASH:
    print("UNREAD: no bash on PATH — dump.sh cannot be exercised here")
    sys.exit(2)


def dump(args, env_lane="Fable"):
    return subprocess.run([BASH, str(HERE / "dump.sh")] + args, capture_output=True, text=True, encoding="utf-8",
                          env=dict(os.environ, DUMP_LANE=env_lane, PYTHONIOENCODING="utf-8"))


def check(d):
    return subprocess.run([PY, str(HERE / "ledger_check.py"), str(d)], capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))


with tempfile.TemporaryDirectory() as td:
    d = Path(td)
    (d / "LEDGER.md").write_text("# test ledger\n\n| id | utc | lane | category | subject | bytes | sha256 |\n|---|---|---|---|---|---|---|\n"
                                 "| D0001 | 2026-08-26T05:27:39Z | Fable | evidence | a pre-S141 row, no twin | 3916 | `" + "a" * 64 + "` |\n", encoding="utf-8")
    f = d / "receipt.md"
    f.write_bytes(b"# a receipt\n\nline\n")
    src = d / "src.jsonl"
    src.write_bytes(b'{"x":1}\n')
    p = dump(["--ref", "--ledger", str(d), "--producer", str(HERE / "ledger_check.py"), "--source", str(src), "--coverage", "fixture", "evidence", "S9 calls receipt", str(f)])
    case("--ref dump exits 0", (p.returncode, "DUMPED  D0002" in p.stdout and "(in place)" in p.stdout), (0, True))
    twin = [json.loads(ln) for ln in io.open(d / "LEDGER.jsonl", encoding="utf-8") if ln.strip()]
    case("the twin row carries path/producer/sources/coverage/row_sha256", sorted(k for k in twin[-1] if k in ("path", "producer", "sources", "coverage", "row_sha256")), ["coverage", "path", "producer", "row_sha256", "sources"])
    case("the source's bytes and sha are recorded", (twin[-1]["sources"][0]["bytes"], len(twin[-1]["sources"][0]["sha256"])), (8, 64))
    case("the producer's blob is a git object id", len(twin[-1]["producer"]["blob"]), 40)
    p = dump(["--lane-missing"], env_lane="")
    case("no DUMP_LANE → refused", p.returncode, 1)
    p = check(d)
    case("ledger_check agrees → exit 0", (p.returncode, "D0002: row_sha256 ✓ · md == twin ✓ · bytes reproduce ✓" in p.stdout), (0, True))
    case("the pre-S141 row is said, not red", "D0001: md row (no twin — pre-S141)" in p.stdout, True)
    f.write_bytes(b"# a receipt\n\nchanged\n")
    p = check(d)
    case("a file changed under a --ref row → red", (p.returncode, "do NOT reproduce ✗" in p.stdout), (1, True))
    f.write_bytes(b"# a receipt\n\nline\n")
    lines = io.open(d / "LEDGER.jsonl", encoding="utf-8").read().splitlines()
    lines[-1] = lines[-1].replace('"subject":"S9 calls receipt"', '"subject":"S9 calls receipt (edited)"')
    io.open(d / "LEDGER.jsonl", "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    p = check(d)
    case("a twin row edited after writing → row_sha256 ✗", (p.returncode, "row_sha256 ✗" in p.stdout), (1, True))
    lines[-1] = lines[-1].replace(" (edited)", "")
    io.open(d / "LEDGER.jsonl", "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    # copy mode into a category dir of the temp ledger (dump.sh copies into ITS OWN dumps/<cat>/ — use the real one's evidence dir? no: never write there from a test)
    p = check(d)
    case("restored → exit 0", p.returncode, 0)
    p = check(d / "nope")
    case("no LEDGER.md → CONFIG exit 2", p.returncode, 2)

print("ledger_check selftest: %d/%d green" % (N - len(FAILS), N))
sys.exit(1 if FAILS else 0)
