#!/usr/bin/env python
"""guard_bare_python_selftest.py — the tripwires of guard_bare_python.py (SYM-186, S213): the hook is fed PreToolUse payloads
on stdin, the way the harness feeds it, and its stdout is read. MUST DENY: every shape of a bare python/python3/py/pip head
(plain, chained, piped, wrapped, inside bash -c / powershell -Command / cmd /c / eval, find -exec, Start-Process, a python
heredoc's own head, PowerShell's call operator). MUST PASS: full paths (uv, marker-env, Windows and POSIX forms), variables,
the word as an argument, heredoc and here-string bodies, comments, commit messages. Empty stdin -> silence. NEGATIVE CONTROL:
the same deny cases run against a stub hook that approves everything must FAIL this suite's deny check -- proving the check
can tell a working guard from a silent one. Exit 0 all fired · 1 any silent."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "guard_bare_python.py")
UV = "C:/Users/Bndit/AppData/Roaming/uv/python/cpython-3.12.13-windows-x86_64-none/python.exe"
ME = "C:/Users/Bndit/ml/marker-env/Scripts/python.exe"
N = FAILS = 0


def check(name, cond, detail=""):
    global N, FAILS
    N += 1
    print(("  ok   " if cond else "  BAD  ") + name + ("" if cond else (" — " + detail if detail else "")))
    if not cond:
        FAILS += 1


def run(hook, command, tool="Bash"):
    payload = "" if command is None else json.dumps({"tool_name": tool, "tool_input": {"command": command}})
    r = subprocess.run([sys.executable, hook], input=payload, capture_output=True, text=True, encoding="utf-8")
    return r.returncode, (r.stdout or "").strip()


def denied(hook, command, tool="Bash"):
    rc, out = run(hook, command, tool)
    return rc == 0 and '"permissionDecision": "deny"' in out


DENY = [
    ("plain python3", "python3 -c \"print(1)\"", "Bash"),
    ("plain python", "python script.py", "Bash"),
    ("py launcher", "py -3 script.py", "Bash"),
    ("pip", "pip install requests", "Bash"),
    ("pip3.12", "pip3.12 --version", "Bash"),
    ("python.exe by name", "python.exe x.py", "Bash"),
    ("versioned python3.14", "python3.14 -V", "Bash"),
    ("after cd &&", "cd /c/Users/Bndit && python3 x.py", "Bash"),
    ("after ||", "true || python3 --version", "Bash"),
    ("after ;", "ls; python x.py", "Bash"),
    ("piped into", "cat f.json | python3 -c \"import json\"", "Bash"),
    ("on a new line", "echo start\npython3 x.py", "Bash"),
    ("assignment prefix", "PYTHONIOENCODING=utf-8 python3 x.py", "Bash"),
    ("env wrapper", "env PYTHONIOENCODING=utf-8 python3 x.py", "Bash"),
    ("timeout wrapper", "timeout 60 python x.py", "Bash"),
    ("xargs", "ls *.py | xargs python3", "Bash"),
    ("find -exec", "find . -name '*.py' -exec python3 {} \\;", "Bash"),
    ("command substitution", "echo $(python3 -c \"print(2)\")", "Bash"),
    ("backticks", "echo `python --version`", "Bash"),
    ("bash -c string", "bash -c \"python3 x.py\"", "Bash"),
    ("a python heredoc's own head", "python3 - <<'EOF'\nprint(1)\nEOF", "Bash"),
    ("for loop body", "for f in *.py; do python3 $f; done", "Bash"),
    ("PowerShell plain", "python x.py", "PowerShell"),
    ("PowerShell call operator", "& python x.py", "PowerShell"),
    ("PowerShell Start-Process", "Start-Process python -ArgumentList 'x.py'", "PowerShell"),
    ("PowerShell Start-Process -FilePath", "Start-Process -FilePath py -ArgumentList '-3'", "PowerShell"),
    ("PowerShell after ;", "Get-Date; pip list", "PowerShell"),
    ("cmd /c", "cmd /c python x.py", "Bash"),
    ("unparseable line (fallback): $(python3) inside double quotes still refused",
     "ls \"$(python3 -c 'print(1)')/x\"; echo \"it's", "Bash"),
]
PASS = [
    ("uv interpreter by full path", UV + " x.py", "Bash"),
    ("marker-env by full path", ME + " -m pip list", "Bash"),
    ("quoted full path", "\"" + UV + "\" -u x.py", "Bash"),
    ("POSIX drive path", "/c/Users/Bndit/ml/marker-env/Scripts/python.exe x.py", "Bash"),
    ("PowerShell quoted Windows path", "& \"C:\\Users\\Bndit\\ml\\marker-env\\Scripts\\python.exe\" x.py", "PowerShell"),
    ("variable head", "\"$PY\" -c \"print(1)\"", "Bash"),
    ("word as an argument (grep)", "grep -n python3 notes.md", "Bash"),
    ("word as an argument (echo)", "echo python", "Bash"),
    ("which is not running it", "which python3", "Bash"),
    ("heredoc body holding python3", "cat > run.sh <<'EOF'\npython3 x.py\nEOF", "Bash"),
    ("a comment", "ls  # python3 later", "Bash"),
    ("a commit message", "git commit -m \"python3 is refused now\npython x\"", "Bash"),
    ("assignment then full path", "PYTHONIOENCODING=utf-8 " + UV + " x.py", "Bash"),
    ("PowerShell here-string body", "$s = @'\npython x.py\n'@\nWrite-Output $s", "PowerShell"),
    ("pytest is not python", "pytest -q", "Bash"),
    ("py.test is not py", "py.test -q", "Bash"),
    ("a path named python-config", "python-config --prefix", "Bash"),
    ("unparseable line (fallback): a single-quoted grep pattern holding |py| is data (the replay's one false refusal)",
     "grep -E '\"command\":\"(python3?|py|pip3?)[ \"]' f.jsonl; echo \"it's", "Bash"),
]
rc, out = run(HOOK, None)
check("empty stdin -> silence, exit 0 (a failed probe is UNREAD, never a verdict)", rc == 0 and out == "")
for name, cmd, tool in DENY:
    check("DENY  " + name, denied(HOOK, cmd, tool), repr(cmd))
for name, cmd, tool in PASS:
    rc, out = run(HOOK, cmd, tool)
    check("PASS  " + name, rc == 0 and out == "", repr(cmd) + " -> " + out[:120])
rc, out = run(HOOK, "python3 x.py")
check("the refusal names the full paths to use", "cpython-3.12.13" in out and "marker-env" in out, out[:160])
# NEGATIVE CONTROL: a stub that approves everything must fail the deny check on every deny case
stub = os.path.join(tempfile.mkdtemp(prefix="gbp-stub-"), "stub.py")
open(stub, "w", encoding="utf-8").write("import sys\nsys.stdin.read()\n")
silent = sum(1 for _, cmd, tool in DENY if not denied(stub, cmd, tool))
check("NEGATIVE CONTROL: a stub guard that denies nothing fails the deny check on all %d deny cases" % len(DENY),
      silent == len(DENY), "%d of %d" % (silent, len(DENY)))
print("%s — %d/%d" % ("ALL FIRED" if not FAILS else "SILENT CASES", N - FAILS, N))
sys.exit(1 if FAILS else 0)
