#!/usr/bin/env python
"""PreToolUse (Bash | PowerShell) — J56's mechanical half. Born of ERR-068 / SYM-085 (2026-09-10).

On 2026-09-10T02:40:41Z an in-place fleet lane ran `git reset --hard feat/library-pipeline` in the SHARED
main checkout — its brief pointed it at a ground written for worktree lanes — and destroyed the peer lane's
uncommitted relay entry (MSG-CDX-0064), its `sent` record and its beat. The shared tree had no guard against
a destructive git verb from any process that could reach it. This is that guard.

THE RULE (docs/47 §9, Rab's signature, J56). In the SHARED checkout (a guarded root whose `.git` is a
directory), git is ALLOWLISTED and denied by default:
  - TIER 1, everyone: the working-tree destroyers are always denied —
        reset · checkout · clean · stash · restore · switch · read-tree · checkout-index · rm · mv · apply · am
  - TIER 2, a subagent lane (the payload carries `agent_id`): only READ-ONLY git passes (status, log, diff,
    show, rev-parse, ls-files, blame, grep, fetch, …); add/commit/push/pull/merge/rebase and every unknown or
    aliased verb are denied. A lane's bytes go through its own worktree or through the main session.
  - The main session: READ-ONLY plus its own writes (add, commit, push, fetch, pull, merge, rebase,
    cherry-pick, revert, tag, branch, worktree, remote, config, notes). An unknown verb is resolved as an alias
    in the target repository; an alias that expands to a tier-1 verb or to a shell command (`!…`) is denied.
Inside a LINKED WORKTREE (`.git` is a FILE) and in any unguarded repository every verb passes: that tree is the
lane's own.

HOW IT READS A COMMAND
  The command is split into segments (`&&`, `||`, `;`, `|`, newlines, `$(`, backticks, parentheses, braces);
  `cd`/`pushd`/`Set-Location`/`Push-Location` earlier in the same command move the target; `git -C <path>` and
  `--work-tree=<path>` name it; MSYS `/c/…` paths are read as `C:/…`; quotes and backslashes inside the head and
  verb tokens are removed (`git re'set'` is `git reset`); `-c alias.x=…` on the line is denied. A segment whose
  first token is a wrapper (`bash -c`, `sh`, `powershell`, `cmd`, `python -c`, `xargs`, `find … -exec`, `eval`,
  `iex`, `Start-Process`, `timeout`, `nohup`, `env`, `sudo`, …) and that mentions `git` at all, or that
  carries an encoded command, is denied when aimed at a guarded root — a wrapper must not be a door. A verb
  or a command head that is a shell variable is UNREAD and denied.
  FAILS CLOSED: a payload it cannot read → DENY (docs/32 §5 rule 4: UNREAD never renders as clean).

THE ONE BYPASS, NEVER SILENT
  A command that begins with  FP_GIT_GUARD_BYPASS='<reason of 20+ characters>'  passes, and the reason is
  logged with the command. The bypass is in the command text on purpose: transcript, log, and the reader of
  either see it. Fleet briefs never mention it.

THE LOG — `coordination/private/git-guard.log` (UTC): every DENY and BYPASS, with the caller's agent id and
type when the payload carries them. If `coordination/private/git-guard.trace` exists, ALLOWs are logged too
with the payload's top-level keys (the empirical probe of what a call carries).

GUARDED ROOTS: this repository (two levels above this file) + each line of
`coordination/private/git-guard.roots` (untracked) + `FP_GIT_GUARD_EXTRA_ROOTS` from the HOOK PROCESS
environment (the selftest's; a lane's command text cannot reach the hook's environment). `FP_GIT_GUARD_LOG`
(same environment) redirects the log.

Output: DENY → JSON on stdout (permissionDecision "deny" + reason), exit 0 — the JSON is the verdict and it
blocks even in bypass-permissions mode; ALLOW → nothing, exit 0. `settings.json` turns an interpreter failure
into exit 2, so a missing python also denies. No shell layer in this file, deliberately (ERR-009).

WHAT IT CANNOT SEE (residue, stated): a script FILE that runs git (`bash x.sh`, `python x.py`) — the guard
reads the command line, not files; a git invoked by a process the harness does not route through these two
tools; the roots file and this hook are ordinary files a lane could edit (the guard's config is not itself
guarded — docs/47 §9 forbids it by law, and the log shows the denial that preceded any such edit).

Tripwire: `.claude/hooks/guard_git_selftest.py` — a positive control and every negative, on a throwaway
repository with a real linked worktree. Run it whenever this file changes.
"""
import io
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

TIER1 = ("reset", "checkout", "clean", "stash", "restore", "switch", "read-tree", "checkout-index", "rm", "mv", "apply", "am")
READ_ONLY = ("status", "log", "diff", "show", "rev-parse", "ls-files", "ls-tree", "ls-remote", "cat-file", "blame", "grep",
             "reflog", "describe", "merge-base", "check-ignore", "check-attr", "shortlog", "count-objects", "fsck",
             "rev-list", "name-rev", "for-each-ref", "diff-tree", "diff-index", "diff-files", "var", "version", "help",
             "fetch", "show-ref", "verify-commit", "whatchanged", "cherry", "range-diff", "annotate")
MAIN_WRITES = ("add", "commit", "push", "pull", "merge", "rebase", "cherry-pick", "revert", "tag", "branch", "worktree",
               "remote", "config", "notes", "submodule", "gc", "update-ref", "symbolic-ref", "commit-tree", "mktree",
               "hash-object", "write-tree", "update-index", "init", "clone", "bundle", "archive", "format-patch", "mailinfo")
# read-only forms of verbs that can also write; a lane gets only these forms
LANE_FORMS = {
    "branch": lambda a: all(x.startswith("-") and x in ("-a", "-r", "-v", "-vv", "--list", "--show-current", "--contains",
                                                        "--merged", "--no-merged", "--all", "--remotes") for x in a),
    "tag": lambda a: all(x in ("-l", "--list", "-n") or x.startswith("-n") for x in a),
    "config": lambda a: any(x in ("--get", "--get-all", "--get-regexp", "--list", "-l", "--show-origin") for x in a)
    and not any(x in ("--add", "--unset", "--unset-all", "--replace-all", "--edit", "-e", "--rename-section", "--remove-section") for x in a)
    and len([x for x in a if not x.startswith("-")]) <= 1,
    "remote": lambda a: (not a) or a[0] in ("-v", "show", "get-url") or all(x.startswith("-") for x in a),
    "worktree": lambda a: bool(a) and a[0] == "list",
    "stash": lambda a: False,
}
WRAPPERS = ("bash", "sh", "zsh", "dash", "ksh", "fish", "powershell", "pwsh", "cmd", "python", "python3", "py", "uv", "uvx",
            "env", "eval", "exec", "xargs", "find", "timeout", "nohup", "nice", "time", "sudo", "runas", "start", "call",
            "start-process", "invoke-expression", "iex", "invoke-command", "icm", "node", "perl", "ruby", "busybox",
            "parallel", "watch", "script", "source")
DIR_WORDS = ("cd", "pushd", "set-location", "push-location", "sl", "chdir")
HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normcase(os.path.realpath(os.path.join(HOOK_DIR, "..", "..")))
ROOTS_FILE = os.path.join(REPO, "coordination", "private", "git-guard.roots")
LOG_FILE = os.environ.get("FP_GIT_GUARD_LOG") or os.path.join(REPO, "coordination", "private", "git-guard.log")
EXTRA_ROOTS_ENV = os.environ.get("FP_GIT_GUARD_EXTRA_ROOTS") or ""
TRACE_FILE = os.path.join(REPO, "coordination", "private", "git-guard.trace")
BYPASS = re.compile(r"^\s*FP_GIT_GUARD_BYPASS=(['\"])(.{20,}?)\1\s+")
# (segments() below replaced the flat SPLIT regex: a separator inside quotes is data, a $( inside double quotes is a command)
ENCODED = re.compile(r"(?i)(^|\s)-(enc|encodedcommand|ec|e)\s+\S")
LAW = "docs/47 §9, J56 (ERR-068 destroyed the peer's uncommitted bytes this way)"


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(kind, tool, cwd, cmd, who="-", extra=""):
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with io.open(LOG_FILE, "a", encoding="utf-8", newline="\n") as fh:
            one = " ".join(str(cmd).split())[:240]
            fh.write(f"{now()} {kind} tool={tool} agent={who} cwd={cwd} {extra} cmd={one}\n")
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


def clean_token(t):
    """Remove quotes and bash escapes so `re'set'` and `res\\et` read as `reset` (verbs and options only — never paths)."""
    return t.replace("'", "").replace('"', "").replace("\\", "")


def clean_head(t):
    """The command head: quotes removed, backslashes read as path separators (a Windows path keeps its shape)."""
    return t.replace("'", "").replace('"', "").replace("\\", "/").lower()


def to_windows(path):
    """A path token: quotes removed, backslashes KEPT, MSYS /c/… read as C:/…"""
    p = path.strip().replace("'", "").replace('"', "")
    m = re.match(r"^/([a-zA-Z])/(.*)$", p)
    if m:
        p = m.group(1).upper() + ":/" + m.group(2)
    return p


def segments(cmd):
    """Quote-aware split into command segments. Separators outside quotes: && || ; | newline ( ) { } $( and backticks;
    inside DOUBLE quotes `$(` and backticks still open a command (bash expands them there); single quotes are literal."""
    out, buf, stack = [], [], ["cmd"]
    i, n = 0, len(cmd)

    def flush():
        s = "".join(buf).strip()
        if s:
            out.append(s)
        buf.clear()

    while i < n:
        c = cmd[i]
        top = stack[-1]
        if top == "squote":
            buf.append(c)
            if c == "'":
                stack.pop()
            i += 1
            continue
        if top == "dquote":
            if c == "\\" and i + 1 < n:
                buf.append(cmd[i:i + 2])
                i += 2
                continue
            if c == '"':
                buf.append(c)
                stack.pop()
                i += 1
                continue
            if cmd.startswith("$(", i):
                flush()
                stack.append("cmd")
                i += 2
                continue
            if c == "`":
                flush()
                stack.append("cmd")
                i += 1
                continue
            buf.append(c)
            i += 1
            continue
        # command context
        if c == "'":
            buf.append(c)
            stack.append("squote")
            i += 1
            continue
        if c == '"':
            buf.append(c)
            stack.append("dquote")
            i += 1
            continue
        if cmd.startswith("$(", i):
            flush()
            stack.append("cmd")
            i += 2
            continue
        if c == ")" and len(stack) > 1 and stack[-1] == "cmd":
            flush()
            stack.pop()
            i += 1
            continue
        if c == "`":
            flush()
            if len(stack) > 1 and stack[-1] == "cmd":
                stack.pop()
            else:
                stack.append("cmd")
            i += 1
            continue
        if c in "(){}|;&\n\r":
            flush()
            i += 1
            continue
        buf.append(c)
        i += 1
    flush()
    return out


def repo_root_of(path):
    """Walk up to the first `.git`; (root, 'dir'|'file') or (None, None)."""
    try:
        p = os.path.realpath(path)
    except Exception:
        return None, None
    for _ in range(64):
        g = os.path.join(p, ".git")
        if os.path.isdir(g):
            return os.path.normcase(p), "dir"
        if os.path.isfile(g):
            return os.path.normcase(p), "file"
        parent = os.path.dirname(p)
        if parent == p:
            return None, None
        p = parent
    return None, None


def tokens(segment):
    return re.findall(r"\"[^\"]*\"|'[^']*'|\S+", segment)


def is_abs(p):
    return os.path.isabs(p) or bool(re.match(r"^[A-Za-z]:", p))


def resolve_alias(root, verb):
    """Return the alias expansion for `verb` in `root`, '' when none; None when git could not answer (UNREAD)."""
    try:
        p = subprocess.run(["git", "-C", root, "config", "--get", "alias." + verb], capture_output=True, text=True, timeout=5)
    except Exception:
        return None
    if p.returncode == 1 and not p.stdout.strip():
        return ""
    if p.returncode != 0:
        return None
    return p.stdout.strip()


def head_of(toks):
    """Skip env assignments and PowerShell call operators; return (index, cleaned lowercase basename)."""
    i = 0
    while i < len(toks) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", toks[i]):
        i += 1
    while i < len(toks) and toks[i] in ("&", "."):
        i += 1
    if i >= len(toks):
        return i, ""
    head = clean_head(toks[i])
    base = head.rsplit("/", 1)[-1]
    if base.endswith(".exe"):
        base = base[:-4]
    return i, base


def parse_git(toks, i):
    """toks[i] is git. Return (verb, args, c_path, work_tree, alias_on_line)."""
    i += 1
    c_path = work_tree = None
    alias_on_line = False
    while i < len(toks):
        t = clean_token(toks[i])
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
            if clean_token(toks[i + 1]).lower().startswith("alias."):
                alias_on_line = True
            i += 2
            continue
        if t.startswith("-"):
            i += 1
            continue
        args = [clean_token(x) for x in toks[i + 1:]]
        return t.lower(), args, c_path, work_tree, alias_on_line
    return "", [], c_path, work_tree, alias_on_line


def decide(payload):
    tool = payload.get("tool_name") or ""
    tin = payload.get("tool_input") or {}
    cmd = tin.get("command")
    who = payload.get("agent_id") or ""
    lane = bool(who)
    if not isinstance(cmd, str):
        return "deny", "guard_git: the tool input carries no command string — UNREAD is not clean", tool, "", ""
    cwd = to_windows(str(payload.get("cwd") or os.getcwd()))
    m = BYPASS.match(cmd)
    if m:
        return "bypass", m.group(2), tool, cwd, cmd
    roots = guarded_roots()

    def guarded(target):
        root, kind = repo_root_of(target)
        if root is None or kind == "file":
            return None
        return root if root in roots else None

    # every guarded root in the spellings a command might carry: C:\x, C:/x, /c/x — for the wrapper text rule
    spellings = []
    for r in roots:
        fw = r.replace("\\", "/")
        spellings += [r.lower(), fw.lower(), ("/" + fw[0].lower() + "/" + fw[3:]).lower() if re.match(r"^[a-z]:/", fw.lower()) else fw.lower()]

    def names_guarded_root(text):
        t = text.replace("\\", "/").lower()
        return any(s.replace("\\", "/") in t for s in spellings)

    def scan(text, cur, depth):
        """Walk the segments of `text` from directory `cur`; return a deny reason or None. Recurses into a wrapper's
        quoted arguments (bash -c '…', sh -c "…", powershell -Command "…", cmd /c "…") up to three levels."""
        for seg in segments(text):
            toks = tokens(seg)
            if not toks:
                continue
            i, base = head_of(toks)
            if not base:
                continue
            if base in DIR_WORDS and len(toks) > i + 1:
                target = to_windows(toks[-1])
                if target in ("-", "~"):
                    continue
                cur = target if is_abs(target) else os.path.join(cur, target)
                continue
            here = guarded(cur)
            if base.startswith("$") or base.startswith("%") or base.startswith("${"):
                if here:
                    return f"guard_git: a command head that is a shell variable ({base}) is UNREAD in the shared checkout {here}; denied ({LAW})"
                continue
            if base in WRAPPERS:
                mentions_git = re.search(r"(?i)\bgit(\.exe)?\b", seg) is not None
                unreadable = base in ("eval", "iex", "invoke-expression", "invoke-command", "icm") or ENCODED.search(seg) is not None
                if here and (mentions_git or unreadable):
                    why = "carries an encoded or evaluated command" if unreadable else "mentions git"
                    return (f"guard_git: a wrapper ({base}) {why} inside the shared checkout {here}; run git directly so the guard "
                            f"can read its verb and target — or this verb is forbidden here ({LAW})")
                if mentions_git and names_guarded_root(seg):
                    return f"guard_git: a wrapper ({base}) mentions git and names a shared checkout; run git directly ({LAW})"
                if depth < 3:
                    for t in toks[i + 1:]:
                        if len(t) > 2 and t[0] in "'\"" and t[-1] == t[0]:
                            r = scan(t[1:-1], cur, depth + 1)
                            if r:
                                return r
                continue
            if base != "git":
                continue
            verb, args, c_path, work_tree, alias_on_line = parse_git(toks, i)
            target = work_tree or c_path or cur
            if not is_abs(target):
                target = os.path.join(cur, target)
            root = guarded(target)
            if root is None:
                continue  # a linked worktree, an unguarded repository, or not a repository: the lane's own business
            if alias_on_line:
                return f"guard_git: `git -c alias.…` on the command line is denied in the shared checkout {root} ({LAW})"
            if not verb or "$" in verb or "%" in verb:
                return f"guard_git: the git verb is UNREAD ({verb or 'missing'}) in the shared checkout {root}; denied ({LAW})"
            if verb in TIER1:
                return (f"guard_git: `git {verb}` aimed at the SHARED checkout {root} is forbidden to any lane not in its own worktree "
                        f"({LAW}). Work in a worktree, or leave the shared tree to Rab.")
            if lane:
                if verb in READ_ONLY:
                    continue
                if verb in LANE_FORMS and LANE_FORMS[verb](args):
                    continue
                return (f"guard_git: a subagent lane may run only READ-ONLY git in the shared checkout {root}; `git {verb}` "
                        f"is denied — commit in your own worktree or hand the bytes to the main session ({LAW})")
            if verb in READ_ONLY or verb in MAIN_WRITES:
                continue
            exp = resolve_alias(root, verb)
            if exp is None:
                return f"guard_git: `git {verb}` is not a known verb and the alias lookup failed in {root}; UNREAD, denied ({LAW})"
            if exp == "":
                return f"guard_git: `git {verb}` is not a verb the shared checkout {root} admits; denied ({LAW})"
            first = clean_token(exp.split()[0]) if exp.split() else ""
            if exp.startswith("!") or first in TIER1 or first not in READ_ONLY + MAIN_WRITES:
                return f"guard_git: alias `{verb}` expands to `{exp[:60]}` in the shared checkout {root}; denied ({LAW})"
        return None

    reason = scan(cmd, cwd, 0)
    if reason:
        return "deny", reason, tool, cwd, cmd
    return "allow", "", tool, cwd, cmd


def emit_deny(reason):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}))


def main():
    try:
        raw = sys.stdin.buffer.read()
        payload = json.loads(raw.decode("utf-8", errors="replace"))
        if not isinstance(payload, dict):
            raise ValueError("payload is not an object")
    except Exception as e:
        log("DENY", "?", "?", "", extra=f"reason=unreadable-payload:{e}")
        emit_deny(f"guard_git: could not read the hook payload ({e}) — UNREAD is not clean; denied")
        return
    who = f"{payload.get('agent_id') or '-'}/{payload.get('agent_type') or '-'}"
    try:
        verdict, reason, tool, cwd, cmd = decide(payload)
    except Exception as e:
        log("DENY", payload.get("tool_name"), payload.get("cwd"), (payload.get("tool_input") or {}).get("command"), who, f"reason=exception:{e}")
        emit_deny(f"guard_git: internal error ({e}) — fails closed; denied")
        return
    traced = os.path.exists(TRACE_FILE)
    keys = f"keys={sorted(payload.keys())}" if traced else ""
    if verdict == "deny":
        log("DENY", tool, cwd, cmd, who, keys)
        emit_deny(reason)
        return
    if verdict == "bypass":
        log("BYPASS", tool, cwd, cmd, who, f"reason={reason!r}")
        return
    if traced:
        log("ALLOW", tool, cwd, cmd, who, keys)


if __name__ == "__main__":
    main()
