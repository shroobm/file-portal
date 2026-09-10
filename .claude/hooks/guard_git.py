#!/usr/bin/env python
"""PreToolUse (Bash | PowerShell) — J56's mechanical half. Born of ERR-068 / SYM-085 (2026-09-10).

On 2026-09-10T02:40:41Z an in-place fleet lane ran `git reset --hard feat/library-pipeline` in the SHARED
main checkout — its brief pointed it at a ground written for worktree lanes — and destroyed the peer lane's
uncommitted relay entry (MSG-CDX-0064), its `sent` record and its beat. The shared tree had no guard against
a destructive git verb from any process that could reach it. This is that guard.

THE RULE (docs/47 §9, Rab's signature, J56): a lane that is not in its own worktree may not run
    git reset · checkout · clean · stash · restore · switch
against the shared checkout. Inside a linked worktree (`.git` is a FILE, not a directory) the same verbs are
the lane's own business and pass.

WHAT IT DOES
  - reads the hook payload on stdin; finds every command segment whose FIRST token is `git` (options such as
    `-C <path>`, `-c k=v`, `--no-pager` skipped) and whose verb is one of the six; resolves the segment's
    target checkout from `cd`/`pushd`/`Set-Location` earlier in the same command, from `git -C <path>` /
    `--work-tree=<path>`, else from the payload's `cwd`;
  - DENIES when that target's repository root is a GUARDED root and its `.git` is a directory (the main
    checkout). Guarded roots: this repository (the hook's own location, two levels up) plus every line of
    `coordination/private/git-guard.roots` (untracked; used by the selftest and the red-team clone);
  - ALLOWS in a linked worktree, in any unguarded repository, and for every other command;
  - a segment whose first token is a shell or interpreter (`bash`, `sh`, `powershell`, `pwsh`, `cmd`,
    `python`, `uv`, `env`) and whose text contains a destructive verb is denied conservatively — a wrapper
    must not be a door;
  - FAILS CLOSED: a payload it cannot read, a tool input without a command, an exception anywhere → DENY.
    UNREAD never renders as clean (docs/32 §5 rule 4).

THE ONE BYPASS, NEVER SILENT
  A command that begins with  FP_GIT_GUARD_BYPASS='<reason of 20+ characters>'  passes, and the reason is
  written to the log with the command. The bypass lives in the command text on purpose: it is in the
  transcript, in the log, and in front of whoever reads either. Fleet briefs never mention it.

THE LOG
  Every DENY and every BYPASS appends a line to `coordination/private/git-guard.log` (UTC). If the file
  `coordination/private/git-guard.trace` exists, every decision is logged with the payload's top-level keys —
  the empirical probe of what a subagent's call carries.

Output: on DENY, JSON on stdout with permissionDecision "deny" and the reason, exit 0 (the JSON is the
verdict); on ALLOW, nothing, exit 0. `settings.json` wires the interpreter failure to exit 2 so a missing
python also denies. No shell layer inside this file, deliberately (ERR-009).

Tripwire: `.claude/hooks/guard_git_selftest.py` — a positive control and every negative, on a throwaway
repository with a real linked worktree. Run it whenever this file changes.
"""
import io
import json
import os
import re
import sys
from datetime import datetime, timezone

VERBS = ("reset", "checkout", "clean", "stash", "restore", "switch")
WRAPPERS = ("bash", "sh", "zsh", "powershell", "pwsh", "cmd", "python", "python3", "py", "uv", "uvx", "env", "eval", "exec")
HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normcase(os.path.realpath(os.path.join(HOOK_DIR, "..", "..")))
ROOTS_FILE = os.path.join(REPO, "coordination", "private", "git-guard.roots")
# Two overrides read from the HOOK PROCESS environment only — the selftest's subprocess sets them; a lane's command
# text cannot reach the hook's environment (hooks inherit the harness's env, not the tool's shell).
LOG_FILE = os.environ.get("FP_GIT_GUARD_LOG") or os.path.join(REPO, "coordination", "private", "git-guard.log")
EXTRA_ROOTS_ENV = os.environ.get("FP_GIT_GUARD_EXTRA_ROOTS") or ""
TRACE_FILE = os.path.join(REPO, "coordination", "private", "git-guard.trace")
BYPASS = re.compile(r"^\s*FP_GIT_GUARD_BYPASS=(['\"])(.{20,}?)\1\s+")
SPLIT = re.compile(r"&&|\|\||;|\||\r?\n")


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(kind, tool, cwd, cmd, extra=""):
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with io.open(LOG_FILE, "a", encoding="utf-8", newline="\n") as fh:
            one = " ".join(str(cmd).split())[:240]
            fh.write(f"{now()} {kind} tool={tool} cwd={cwd} {extra} cmd={one}\n")
    except Exception:
        pass


def guarded_roots():
    roots = {REPO}
    for extra in EXTRA_ROOTS_ENV.split(os.pathsep):
        if extra.strip():
            roots.add(os.path.normcase(os.path.realpath(extra.strip())))
    try:
        with io.open(ROOTS_FILE, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#"):
                    roots.add(os.path.normcase(os.path.realpath(line)))
    except Exception:
        pass
    return roots


def to_windows(path):
    """MSYS /c/Users/x -> C:/Users/x ; strip quotes."""
    p = path.strip().strip("'\"")
    m = re.match(r"^/([a-zA-Z])/(.*)$", p)
    if m:
        p = m.group(1).upper() + ":/" + m.group(2)
    return p


def repo_root_of(path):
    """Walk up from path to the first `.git`; return (root, kind) with kind 'dir' (main checkout), 'file'
    (linked worktree) or None (not a repository)."""
    try:
        p = os.path.realpath(path)
    except Exception:
        return None, None
    seen = 0
    while seen < 64:
        g = os.path.join(p, ".git")
        if os.path.isdir(g):
            return os.path.normcase(p), "dir"
        if os.path.isfile(g):
            return os.path.normcase(p), "file"
        parent = os.path.dirname(p)
        if parent == p:
            return None, None
        p = parent
        seen += 1
    return None, None


def tokens(segment):
    return re.findall(r"\"[^\"]*\"|'[^']*'|\S+", segment)


def git_verb(toks):
    """If toks is a git invocation, return (verb, c_path, work_tree) — verb None when not destructive."""
    if not toks:
        return None, None, None
    i = 0
    # leading env assignments (FOO=bar git ...)
    while i < len(toks) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", toks[i]):
        i += 1
    if i >= len(toks):
        return None, None, None
    head = toks[i].strip("'\"").replace("\\", "/").lower()
    if not (head == "git" or head.endswith("/git") or head.endswith("/git.exe") or head == "git.exe"):
        return None, None, None
    i += 1
    c_path, work_tree = None, None
    while i < len(toks):
        t = toks[i]
        if t == "-C" and i + 1 < len(toks):
            c_path = to_windows(toks[i + 1])
            i += 2
            continue
        if t.startswith("--work-tree="):
            work_tree = to_windows(t.split("=", 1)[1])
            i += 1
            continue
        if t == "--work-tree" and i + 1 < len(toks):
            work_tree = to_windows(toks[i + 1])
            i += 2
            continue
        if t == "-c" and i + 1 < len(toks):
            i += 2
            continue
        if t.startswith("-"):
            i += 1
            continue
        return (t.strip("'\"").lower() if t.strip("'\"").lower() in VERBS else None), c_path, work_tree
    return None, c_path, work_tree


def decide(payload):
    tool = payload.get("tool_name") or ""
    tin = payload.get("tool_input") or {}
    cmd = tin.get("command")
    if not isinstance(cmd, str):
        return "deny", "guard_git: the tool input carries no command string — UNREAD is not clean", tool, "", ""
    cwd = to_windows(str(payload.get("cwd") or os.getcwd()))
    m = BYPASS.match(cmd)
    if m:
        return "bypass", m.group(2), tool, cwd, cmd
    roots = guarded_roots()
    cur = cwd
    for seg in SPLIT.split(cmd):
        toks = tokens(seg)
        if not toks:
            continue
        first = toks[0].strip("'\"").replace("\\", "/").lower()
        base = first.rsplit("/", 1)[-1]
        # directory changes carried forward within the same command
        if base in ("cd", "pushd", "set-location", "sl", "chdir") and len(toks) > 1:
            target = to_windows(toks[-1])
            if target in ("-", "~"):
                continue
            cur = target if os.path.isabs(target) or re.match(r"^[A-Za-z]:", target) else os.path.join(cur, target)
            continue
        if base in WRAPPERS or base.endswith(".exe") and base[:-4] in WRAPPERS:
            if re.search(r"\bgit\b.*\b(" + "|".join(VERBS) + r")\b", seg):
                return ("deny", f"guard_git: a wrapper ({base}) carries a destructive git verb; run git directly so the guard "
                        "can read its target — or this is the shared checkout and the verb is forbidden (docs/47 §9, J56)", tool, cwd, cmd)
            continue
        verb, c_path, work_tree = git_verb(toks)
        if verb is None:
            continue
        target = work_tree or c_path or cur
        if not (os.path.isabs(target) or re.match(r"^[A-Za-z]:", target)):
            target = os.path.join(cur, target)
        root, kind = repo_root_of(target)
        if root is None:
            # not a repository as far as the guard can see: nothing shared to protect
            continue
        if kind == "file":
            continue  # a linked worktree: the lane's own tree
        if root in roots:
            return ("deny", f"guard_git: `git {verb}` aimed at the SHARED checkout {root} is forbidden to any lane not in "
                    "its own worktree (docs/47 §9, J56; ERR-068 destroyed the peer's uncommitted bytes this way). "
                    "Work in a worktree, or leave the shared tree to Rab.", tool, cwd, cmd)
    return "allow", "", tool, cwd, cmd


def main():
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("payload is not an object")
    except Exception as e:
        log("DENY", "?", "?", "", f"reason=unreadable-payload:{e}")
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                          "permissionDecisionReason": f"guard_git: could not read the hook payload ({e}) — UNREAD is not clean; denied"}}))
        return
    try:
        verdict, reason, tool, cwd, cmd = decide(payload)
    except Exception as e:
        log("DENY", payload.get("tool_name"), payload.get("cwd"), (payload.get("tool_input") or {}).get("command"), f"reason=exception:{e}")
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                          "permissionDecisionReason": f"guard_git: internal error ({e}) — fails closed; denied"}}))
        return
    traced = os.path.exists(TRACE_FILE)
    if verdict == "deny":
        log("DENY", tool, cwd, cmd, f"keys={sorted(payload.keys())}" if traced else "")
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                          "permissionDecisionReason": reason}}))
        return
    if verdict == "bypass":
        log("BYPASS", tool, cwd, cmd, f"reason={reason!r}")
        return
    if traced:
        log("ALLOW", tool, cwd, cmd, f"keys={sorted(payload.keys())}")


if __name__ == "__main__":
    main()
