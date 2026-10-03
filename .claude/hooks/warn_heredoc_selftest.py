#!/usr/bin/env python
"""WHAT THIS FILE DOES: a standalone test script for warn_heredoc.py. When run it feeds the hook a series of command
lines as payloads on stdin, checks the exit code and the printed JSON (silence, warning or deny) against what each case
expects, prints one ok/BAD line per case and a total, and exits 0 only when every case behaved. It writes nothing to
disk. It runs top to bottom at import time (no main function).

warn_heredoc_selftest.py — the tripwires of warn_heredoc.py (S170): the hook is fed PreToolUse payloads on stdin, the way the
harness feeds it, and its stdout is read. ERR-009's half (a heredoc with escapes → the warning; a heredoc without → silence; the
signed over-sensitivity: a QUOTED heredoc with an escaped quote still warns) and ERR-054's half (S170: a `python -c` program with
a backslash or a `$` → DENIED since S213, a backtick alone → the ERR-054 warning; a plain `python -c "print(1)"` →
silence — the NEGATIVE CONTROL; a
`python.exe -c '…'` by absolute path counts; `-c` on a non-python head does not). Empty stdin → silence, exit 0 (the smoke's own
case). Exit 0 all fired · 1 any silent."""
import json
import os
import subprocess
import sys

# -- the hook path and the pass/fail counters --
HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "warn_heredoc.py")
N = FAILS = 0


# -- helpers: record a result, run the hook --
def check(name, cond, detail=""):
    """Count one case (N), print an ok/BAD line for `name` (with `detail` when it failed) and count a failure (FAILS)."""
    global N, FAILS
    N += 1
    if cond:
        print("  ok   " + name)
    else:
        FAILS += 1
        print("  BAD  " + name + (" — " + detail if detail else ""))


def hook(command):
    """Run warn_heredoc.py with a Bash payload carrying `command` on stdin (empty stdin when `command` is None).
    Returns (exit code, stripped stdout)."""
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}) if command is not None else ""
    r = subprocess.run([sys.executable, HOOK], input=payload, capture_output=True, text=True, encoding="utf-8")
    return r.returncode, (r.stdout or "").strip()


# -- the cases, run in order: heredoc warnings first, then the `python -c` cases, then the output shape --
rc, out = hook(None)
check("empty stdin → silence, exit 0 (a failed probe is UNREAD, never a verdict)", rc == 0 and out == "")
rc, out = hook("cat > x.txt <<EOF\nplain text\nEOF")
check("a heredoc with no escapes → silence", rc == 0 and out == "")
rc, out = hook("python - <<EOF\nimport re\nre.findall(r\"\\\\begin\\{array\\}\", s)\nEOF")
check("ERR-009: a heredoc with backslash escapes → the ERR-009 warning", rc == 0 and "ERR-009" in out and "heredoc" in out, out[:160])
rc, out = hook("cat <<'EOF'\nit\\'s\nEOF")
check("the SIGNED over-sensitivity: a QUOTED heredoc with an escaped quote still warns (Rab, 2026-08-27)", rc == 0 and "ERR-009" in out, out[:120])
rc, out = hook("python -c \"print(1)\"")
check("NEGATIVE CONTROL: a plain `python -c \"print(1)\"` → silence", rc == 0 and out == "", out[:120])
def denied(out):
    """True when `out` is the hook's JSON with a PreToolUse deny decision whose reason names ERR-054; any parse failure
    gives False."""
    try:
        h = json.loads(out).get("hookSpecificOutput", {})
    except Exception:  # noqa: BLE001
        return False
    return h.get("hookEventName") == "PreToolUse" and h.get("permissionDecision") == "deny" and "ERR-054" in h.get("permissionDecisionReason", "")


# S213 (Rab, Desk 17258df3, 2026-09-25): the -c program with a backslash or a $ is now REFUSED; a backtick alone still warns
rc, out = hook("PYTHONIOENCODING=utf-8 /c/Users/x/python.exe -c \"import io; p='C:\\\\x\\\\y.md'; print(p)\"")
check("S213 BLOCK: a `python.exe -c` program with a backslash path → DENIED (ERR-054), not merely warned", rc == 0 and denied(out), out[:160])
rc, out = hook("python3 -c 'import os; print(os.environ[\"$HOME\"])'")
check("S213 BLOCK: a $ inside the -c program → DENIED", rc == 0 and denied(out), out[:120])
rc, out = hook("python -c 'print(`x`)'")
check("NEGATIVE (the offered scope): a backtick alone inside the -c program still only WARNS, never denies",
      rc == 0 and "ERR-054" in out and not denied(out), out[:120])
rc, out = hook("python - <<EOF\nimport re\nre.findall(r\"\\\\d+\", s)\nEOF")
check("NEGATIVE (his 2026-08-27 signature): a heredoc with backslashes still only WARNS (ERR-009), never denies",
      rc == 0 and "ERR-009" in out and not denied(out), out[:120])
rc, out = hook("cat <<EOF\nre.sub(r'\\\\s+', ' ', x)\nEOF\npython -c \"print('$HOME')\"")
check("S213: a heredoc warning AND a blocked -c on one line → the block wins (DENIED)", rc == 0 and denied(out), out[:120])
rc, out = hook("grep -c 'x\\\\y' file.txt")
check("NEGATIVE CONTROL: a backslash outside any heredoc or -c program → silence (grep is not python)", rc == 0 and out == "", out[:120])
rc, out = hook("python -c \"print(1)\"; cat <<EOF\nre.sub(r'\\\\s+', ' ', x)\nEOF")
check("both on one line: the heredoc's ERR-009 message is the one printed (one message per call)", rc == 0 and "ERR-009" in out, out[:120])
rc, out = hook("python -c \"print(1)\"")
try:
    js = json.loads(hook("python -c 'print(`a`)'")[1])  # S213: a backtick case (a backslash now denies, checked above)
    shape = js.get("hookSpecificOutput", {}).get("hookEventName") == "PreToolUse" and "additionalContext" in js["hookSpecificOutput"]
except Exception as e:  # noqa: BLE001
    shape = False
    js = str(e)
check("the warning is the harness's JSON shape (PreToolUse · additionalContext)", shape, str(js)[:120])

print("warn_heredoc_selftest: %s" % ("ALL OK: %d/%d" % (N, N) if FAILS == 0 else "%d of %d FAILED" % (FAILS, N)))
sys.exit(1 if FAILS else 0)
