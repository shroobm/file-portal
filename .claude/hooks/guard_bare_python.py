#!/usr/bin/env python
"""PreToolUse/Bash|PowerShell — SYM-186's guard (Rab, Desk c7b3aa7c, 2026-09-25T22:36Z: "guard bare python").

WHAT THIS FILE DOES: a Claude Code PreToolUse hook script. main() reads the hook payload (JSON) from stdin, bad_heads()
tokenises the command text and returns every command head that is a bare python / py / pip name, and main() prints a deny
JSON naming them (exit 0) or stays silent. It reads only stdin and writes only stdout; it has no log file and runs no
other program. Its selftest is guard_bare_python_selftest.py.

On this machine a BARE `python`, `python3`, `py` or `pip` does not fail: since 2026-09-25 04:30Z they resolve to the
Python Install Manager, which silently downloads and installs a runtime from python.org. It happened twice that day --
15:17Z (the coordinator's own call) and 18:58Z (a research sub-agent, whose ground rules said "NEVER a bare python3"),
the second unnoticed for three hours. A rule in a prompt did not hold for sub-agents; this is the half a machine can hold.

REFUSES a command in which any command HEAD is a bare python / python3 / python3.14 / pythonw / py / pip / pip3 (with or
without .exe, any case). A head is the first word of each part of the command line -- after ; && || | & ( ) newlines and
backticks -- looking past variable assignments (FOO=1), wrappers (env, timeout, nohup, time, exec, command, nice, stdbuf,
xargs, sudo, Start-Process, the PowerShell call operator &) and shell keywords (if, then, do, ...), and INSIDE the string
given to bash/sh -c, powershell/pwsh -Command, cmd /c and eval.
LETS THROUGH a head that is a path (it holds / or \\ or :), a variable ($PY, %PY%), the word as an ARGUMENT
(`grep python3 f`, `echo python`), and the bodies of heredocs (<<EOF ... EOF) and PowerShell here-strings (@' ... '@).
Sub-agents' calls pass through the same project hooks (their payload carries agent_id -- guard_git's tier 2 relies on it),
so the guard binds them too.

CANNOT SEE: a python started from inside a script or program (a .sh that calls python3, subprocess in Python), or a name
assembled at run time ($(echo py)thon). Only the command line as the tool receives it.

Reads the hook payload on stdin; on a refusal prints the deny JSON and exits 0. An unreadable payload is silence (exit 0),
the harness's own contract for a failed probe; the settings line around this script DENIES if the interpreter itself fails."""
import json
import re
import shlex
import sys

# -- patterns and word lists: what counts as a bare name, separators, wrappers to look past, shells to look inside --
BARE = re.compile(r"^(?:python(?:\d+(?:\.\d+)*)?w?|py|pip(?:\d+(?:\.\d+)*)?)(?:\.exe)?$", re.I)
SEP = set(";&|()\n`")
WRAPPERS = {"env", "timeout", "nohup", "time", "exec", "command", "builtin", "nice", "stdbuf", "xargs", "sudo",
            "start-process", "start", "&", ".", "call", "then", "do", "else", "elif", "if", "while", "until", "!", "{", "}"}
TAKES_ARG = {"timeout": 1, "nice": 0}     # timeout's DURATION is a positional; nice's -n N handled by the option rule below
OPT_WITH_ARG = {"-n", "-s", "-k", "-I", "-P", "-d", "-E", "-L", "-u", "-FilePath", "-ArgumentList", "-o", "-e", "-i"}
SHELLS = {"bash", "sh", "zsh", "dash", "bash.exe", "sh.exe", "powershell", "powershell.exe", "pwsh", "pwsh.exe", "cmd",
          "cmd.exe", "eval"}
SHELL_FLAGS = {"-c", "-command", "/c", "/k", "-lc", "-ic"}
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")


# -- reading the command text: heredoc bodies, tokens, quotes, paths --
def strip_bodies(cmd):
    """Drop heredoc bodies and PowerShell here-string bodies: data, not commands."""
    out, lines, i = [], cmd.split("\n"), 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        delims = [m.group(2) for m in HEREDOC.finditer(line)]
        if re.search(r"@['\"]\s*$", line):
            i += 1
            while i < len(lines) and not re.match(r"^\s*['\"]@", lines[i]):
                i += 1
        for d in delims:
            i += 1
            while i < len(lines) and lines[i].strip() != d:
                i += 1
        i += 1
    return "\n".join(out)


def tokens(cmd, posix):
    """Split `cmd` into shell-like tokens with shlex (posix quoting rules when `posix`, else shlex's non-POSIX mode,
    which the caller picks for PowerShell/cmd text although it is not their own quoting: a backtick splits as
    punctuation and `'` quotes). Separator characters come out as their own tokens and each newline as a "\\n"
    token. Returns a list of strings;
    unbalanced quotes raise ValueError (the caller handles it)."""
    lex = shlex.shlex(cmd, posix=posix, punctuation_chars=";&|()`")
    lex.whitespace = " \t\r"
    lex.commenters = ""
    lex.whitespace_split = False
    out = []
    for t in lex:
        out.extend(["\n"] * t.count("\n") if t.strip("\n") == "" and "\n" in t else [t])
    return out


def unquote(t):
    """Remove one pair of matching surrounding quotes (single or double) from token `t`; otherwise return it unchanged."""
    return t[1:-1] if len(t) >= 2 and t[0] == t[-1] and t[0] in "'\"" else t


def is_path(t):
    """True when token `t` contains `/`, a backslash or `:` (so it names a path, not a bare program name)."""
    return any(c in t for c in "/\\:")


# -- finding bare-python command heads --
def bad_heads(cmd, posix, depth=0):
    """Every bare-python head in cmd (recursing into shell -c strings, one level deep per call, at most 3)."""
    found = []
    try:
        toks = tokens(strip_bodies(cmd), posix)
    except ValueError:
        # unbalanced quotes: fall back to a line-and-separator scan of the raw text, with SINGLE-quoted spans removed first
        # (bash never runs them -- a grep pattern '(python3?|py)' is data; the replay of this session's 28,098 commands found
        # that one false refusal) while double-quoted text stays, since "$(python3 ...)" inside it does run.
        raw = re.sub(r"'[^'\n]*'", "''", strip_bodies(cmd)) if posix else strip_bodies(cmd)
        for m in re.finditer(r"(?:^|[;&|(`\n])\s*(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*([^\s;&|()`'\"]+)", raw):
            if BARE.match(m.group(1)):
                found.append(m.group(1))
        return found
    # cut the token list into command parts at separator tokens and check each part's head
    seg = []
    for t in toks + ["\n"]:
        if t and all(c in SEP for c in t):
            found.extend(check_segment(seg, posix, depth))
            seg = []
        else:
            seg.append(t)
    return found


def check_segment(seg, posix, depth):
    """Find the command head of one part of the command line (list of tokens `seg`) and judge it. Skips variable
    assignments, wrappers and their options, follows `find -exec`, and recurses into the string given to a shell
    (-c / -Command / /c / eval) when depth < 3. Returns a list of bare names found (empty when the head is a path, a
    variable, or not a bare name)."""
    i, n = 0, len(seg)
    while i < n:
        t = unquote(seg[i])
        low = t.lower()
        if t.startswith("#"):
            return []                                    # a comment from here to the end of the part
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", t):
            i += 1                                       # FOO=bar
            continue
        if low == "find":                                # find ... -exec / -execdir PROG: PROG runs
            for j in range(i + 1, n - 1):
                if unquote(seg[j]).lower() in ("-exec", "-execdir", "-ok", "-okdir"):
                    return check_segment(seg[j + 1:], posix, depth)
            return []
        if low in WRAPPERS:
            skip = TAKES_ARG.get(low, 0)
            i += 1
            while i < n:
                a = unquote(seg[i])
                if a.lower() == "-filepath" and i + 1 < n:    # Start-Process -FilePath PROG: PROG is the head
                    i += 1
                    break
                if a in OPT_WITH_ARG or a.lower() in {o.lower() for o in OPT_WITH_ARG}:
                    i += 2
                elif a.startswith("-") or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", a):
                    i += 1
                elif skip:
                    skip -= 1
                    i += 1
                else:
                    break
            continue
        if low in SHELLS or low.rsplit("/", 1)[-1].rsplit("\\", 1)[-1] in SHELLS:
            base = low.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
            inner = []
            j = i + 1
            if base == "eval":
                inner = [" ".join(unquote(x) for x in seg[j:])]
            else:
                while j < n:
                    a = unquote(seg[j]).lower()
                    if a in SHELL_FLAGS and j + 1 < n:
                        inner.append(unquote(seg[j + 1]))
                        j += 2
                    else:
                        j += 1
            out = []
            if depth < 3:
                for s in inner:
                    out.extend(bad_heads(s, posix=not base.startswith(("powershell", "pwsh", "cmd")), depth=depth + 1))
            return out
        if t.startswith(("$", "%")) or is_path(t):
            return []
        return [t] if BARE.match(t) else []
    return []


# -- hook entry point --
def main():
    """Hook entry: read the payload from stdin, run bad_heads() over tool_input.command (posix rules unless the tool is
    PowerShell), print the deny JSON when any bare head is found. Exits 0 for every payload the harness sends (silence =
    allow; an unreadable payload is also silence; a JSON payload that is not an object would raise at the tool_input read,
    outside the try, and exit 1 - which settings.json turns into a deny)."""
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    cmd = (payload.get("tool_input") or {}).get("command") or ""
    posix = (payload.get("tool_name") or "") != "PowerShell"
    heads = bad_heads(cmd, posix)
    if not heads:
        sys.exit(0)
    reason = ("BARE PYTHON BLOCKED (SYM-186; Rab, Desk c7b3aa7c, 2026-09-25: 'guard bare python'): this command runs {h} "
              "by its bare name. On this machine a bare python/python3/py/pip goes to the Python Install Manager, which "
              "silently downloads and installs a runtime (it did, twice, on 2026-09-25). Use the full path: "
              "C:/Users/Bndit/AppData/Roaming/uv/python/cpython-3.12.13-windows-x86_64-none/python.exe for tools, or "
              "C:/Users/Bndit/ml/marker-env/Scripts/python.exe for the converter's environment.").format(
                  h=", ".join("`%s`" % h for h in sorted(set(heads))))
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}))
    sys.exit(0)


if __name__ == "__main__":
    main()
