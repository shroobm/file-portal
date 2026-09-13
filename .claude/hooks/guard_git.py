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

WHAT IT CANNOT SEE (residue, stated — a command-line guard is defense in depth, not a sandbox; the LAW's
real isolation is the worktree):
  - a git run from inside a script FILE the guard did not read (`echo '…git…' > x.sh; bash x.sh`), or a target
    the program ASSEMBLES at runtime (`python -c "…bytes([103,105,116])…"`) — the guard reads the command
    line, not files, and not a program's runtime strings. A heredoc body IS on the command line, so its git is
    seen (it lands on its own segment).
  - a git invoked by a process the harness does not route through the Bash / PowerShell tools.
  - the roots file and this hook are ordinary files a lane could edit; the guard's config is not itself guarded
    (docs/47 §9 forbids the edit by law, and the trace log shows the ALLOW that preceded any such write).
These residues were surfaced by the S124 red team (the critic lane) and are named here rather than papered over.

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
            "start-process", "saps", "start-job", "sajb", "start-threadjob", "invoke-item", "ii", "invoke-expression", "iex",
            "invoke-command", "icm", "node", "perl", "ruby", "busybox", "parallel", "watch", "script", "source", "wsl",
            "conhost", "schtasks", "at", "register-scheduledtask", "new-scheduledtask", "new-scheduledtaskaction",
            "forfiles", "msiexec", "wmic", "psexec")
DEFINERS = ("alias", "set-alias", "sal", "new-alias", "nal", "function", "filter")  # a command that names its own commands
# J64 (S137): the wrappers whose QUOTED ARGUMENT is itself shell text (bash -c '…', cmd /c "…", powershell -Command "…",
# eval "…"). Only these are recursed into; a python -c payload, a `time -f '%es'` format or a `find -printf '%TY…'`
# format is that program's own text, and reading it with the bash grammar manufactured five false heads (SYM-110's
# shapes 6, 7, 10 and the heredoc bodies). A non-shell wrapper that shells out to git is still caught by the
# mentions-git rule over the whole segment (the R4 red-team case: python -c "os.system('git reset --hard')").
SHELL_WRAPPERS = ("bash", "sh", "zsh", "dash", "ksh", "fish", "cmd", "powershell", "pwsh", "eval", "iex",
                  "invoke-expression", "invoke-command", "icm", "wsl", "busybox", "script", "source", "xargs", "parallel")
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
DIR_WORDS = ("cd", "pushd", "set-location", "push-location", "sl", "chdir")
ENV_TARGETS = ("GIT_WORK_TREE", "GIT_DIR")
HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normcase(os.path.realpath(os.path.join(HOOK_DIR, "..", "..")))
ROOTS_FILE = os.path.join(REPO, "coordination", "private", "git-guard.roots")
LOG_FILE = os.environ.get("FP_GIT_GUARD_LOG") or os.path.join(REPO, "coordination", "private", "git-guard.log")
EXTRA_ROOTS_ENV = os.environ.get("FP_GIT_GUARD_EXTRA_ROOTS") or ""
TRACE_FILE = os.path.join(REPO, "coordination", "private", "git-guard.trace")
BYPASS = re.compile(r"^\s*FP_GIT_GUARD_BYPASS=(['\"])(.{20,}?)\1\s+")
# a path the guard cannot resolve because the SHELL would expand it at runtime and the guard is not a shell:
# $VAR, ${VAR}, $(...), backticks, %VAR% (cmd). An UNREAD target must fail closed, never read as "not guarded".
UNRESOLVED = re.compile(r"\$\w|\$\{|\$\(|`|%[A-Za-z_][A-Za-z0-9_]*%")
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


def unquote(t):
    """Remove surrounding/embedded quotes but KEEP backslashes — for path arguments, where `\\` is a separator."""
    return t.replace("'", "").replace('"', "")


def clean_head(t):
    """The command head: quotes removed, backslashes read as path separators (a Windows path keeps its shape)."""
    return t.replace("'", "").replace('"', "").replace("\\", "/").lower()


def is_unresolved(p):
    """True when a path token is empty or carries a shell expansion the guard cannot perform (so the target is UNREAD)."""
    return (not p) or bool(UNRESOLVED.search(p))


def to_windows(path):
    """A path token: quotes removed, backslashes KEPT, MSYS /c/… read as C:/…"""
    p = path.strip().replace("'", "").replace('"', "")
    m = re.match(r"^/([a-zA-Z])/(.*)$", p)
    if m:
        p = m.group(1).upper() + ":/" + m.group(2)
    return p


def segments(cmd, ps=False):
    """Quote-aware split into command segments. Separators outside quotes: && || ; | newline ( ) { } $( and backticks;
    inside DOUBLE quotes `$(` and backticks still open a command (bash expands them there); single quotes are literal.
    ps=True (the PowerShell tool): a lone `&` is the CALL OPERATOR, not a separator — `& $G reset` must keep its `&`
    so head_of can see the variable being invoked (bash's lone `&` is a background separator and stays one)."""
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
            if cmd.startswith("$((", i):  # arithmetic inside double quotes: data, same as in command context
                depth, j = 0, i + 3
                while j < n:
                    if cmd[j] == "(":
                        depth += 1
                    elif cmd[j] == ")":
                        if depth == 0 and cmd.startswith("))", j):
                            j += 2
                            break
                        depth -= 1
                    j += 1
                buf.append(cmd[i:j])
                i = j
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
        if cmd.startswith("$((", i):
            # arithmetic expansion, not a command: copy through its matching "))" as data (the guard once denied
            # sed -n "$((L+1)),$p" for a "$p" head it manufactured here — a false deny on a read-only command)
            depth, j = 0, i + 3
            while j < n:
                if cmd[j] == "(":
                    depth += 1
                elif cmd[j] == ")":
                    if depth == 0 and cmd.startswith("))", j):
                        j += 2
                        break
                    depth -= 1
                j += 1
            buf.append(cmd[i:j])
            i = j
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
        if cmd.startswith("&&", i) or cmd.startswith("||", i):
            flush()
            i += 2
            continue
        if c == "&" and ps:
            buf.append(c)  # PowerShell call operator, kept for head_of
            i += 1
            continue
        if c in "{}" and not ps:
            # bash: `{ cmd; }` is a group (a separator); `{git,}` is BRACE EXPANSION inside a word — keep it in the token so
            # head_of sees the `{` and renders the head UNREAD (S127: `{git,} reset --hard` had split into `git,` and passed)
            boundary = (c == "{" and (i + 1 >= n or cmd[i + 1] in " \t\n\r")) or (c == "}" and (i == 0 or cmd[i - 1] in " \t\n\r;"))
            if not boundary:
                buf.append(c)
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


def row_check_missing(root):
    """J71 (S136): a `git push` from the main session that CARRIES a change to CLAUDE_README.md (the ledger) is refused
    when the newest row does not pass its reader — `.claude/skills/muster/row_check.sh <N>` (J69), N from the session
    marker. S130's three-cell row reached origin and opened the next muster on an INCIDENT (SYM-113); S133's chain pushed
    a red row past a hand-check. Returns the deny reason, or None. Everything the guard cannot judge is UNREAD and is
    NOT a verdict: no coordination/ (not a File Portal checkout), no row_check.sh, an unreadable marker, a row_check
    exit 2, bash absent, a timeout — all None, the caller logs the note. Only exit 1 denies. S141: NO UPSTREAM is no longer
    "nothing to judge" — the row is checked unconditionally then (the reader needs no upstream), said in the reason."""
    if not os.path.isdir(os.path.join(root, "coordination")):
        return None
    script = os.path.join(root, ".claude", "skills", "muster", "row_check.sh")
    if not os.path.isfile(script):
        return None
    try:
        p = subprocess.run(["git", "-C", root, "diff", "--quiet", "@{upstream}..HEAD", "--", "CLAUDE_README.md"],
                           capture_output=True, text=True, timeout=20)
    except Exception:
        return None
    if p.returncode == 0:          # the ledger is unchanged since upstream: nothing to judge
        return None
    no_upstream = p.returncode != 1
    # S141 (guard-holes/row-check-with-no-upstream; the S140 second reading's I9): no upstream to diff against used to be
    # "nothing to judge" — a push with no tracking branch carried the ledger unread. The row reader needs no upstream:
    # it runs on the working tree's newest row anyway; only its exit 1 denies, everything else stays UNREAD.
    marker = os.path.join(root, "coordination", "private", "session.current")
    marker = os.path.join(root, "coordination", "private", "session.current")
    try:
        first = io.open(marker, encoding="utf-8").read().split()
    except OSError:
        return None
    if not first or not re.match(r"^S\d+$", first[0]):
        return None
    n = first[0][1:]
    try:
        q = subprocess.run(["bash", script, n], capture_output=True, text=True, timeout=60,
                           env=dict(os.environ, FP_REPO=root), cwd=root)
    except Exception:
        return None
    if q.returncode == 1:
        last = (q.stdout.strip().splitlines() or ["(no output)"])[-1]
        return (f"guard_git: `git push` refused — the ledger row does not pass its reader: {last[:220]} "
                f"(J71; fix the row — five cells, the SHA alone in the last — then push)"
                + (" [no upstream to compare against — the ledger was checked unconditionally, S141]" if no_upstream else ""))
    return None


def record_missing(root):
    """J63: why a write/commit in `root` must wait — or None when the session's record exists. The card publishes the
    session number in coordination/private/session.current (`S<N> <machine> <utc>`); the record is sessions/S<N>-*.md.
    A root without a coordination/ directory is not a File Portal checkout and is exempt. Shared with guard_record.py."""
    import glob
    if not os.path.isdir(os.path.join(root, "coordination")):
        return None
    marker = os.path.join(root, "coordination", "private", "session.current")
    try:
        first = io.open(marker, encoding="utf-8").read().split()
    except OSError:
        return "no session marker (coordination/private/session.current): no open ran — run `bash .claude/skills/muster/open.sh` first"
    if not first or not re.match(r"^S\d+$", first[0]):
        return "the session marker is unreadable — re-run `bash .claude/skills/muster/open.sh`"
    n = first[0][1:]
    if glob.glob(os.path.join(root, "sessions", f"S{n}-*.md")):
        return None
    return f"sessions/S{n}-*.md does not exist — open.sh said this session is S{n}; write the record (§1 in Rab's words, the card, the pin) before any instrument"


def targets_named(toks, i, cur, guarded):
    """Scan toks[i:] for git target flags (-C, --work-tree[=], --git-dir[=]); return the guarded root any of them
    names, or a marker string when one is UNREAD (a shell-expanded value), else None. Used when the command HEAD is
    UNREAD so the precise git path was not taken, but an explicit target could still name the shared tree."""
    j = i
    while j < len(toks):
        t = clean_token(toks[j])
        raw = unquote(toks[j])
        val = None
        if t in ("-C", "--work-tree", "--git-dir") and j + 1 < len(toks):
            val = to_windows(toks[j + 1])
            j += 2
        elif t.startswith("--work-tree=") or t.startswith("--git-dir="):
            val = to_windows(raw.split("=", 1)[1])
            j += 1
        else:
            j += 1
            continue
        if is_unresolved(val):
            return "UNREAD"
        base = val if is_abs(val) else os.path.join(cur, val)
        if t in ("--git-dir", "--git-dir=") or t.startswith("--git-dir="):
            base = os.path.dirname(base.rstrip("/\\"))
        g = guarded(base)
        if g:
            return g
    return None


def core_worktree(root):
    """The repository's core.worktree, absolute; '' when unset; None when git could not answer (UNREAD)."""
    try:
        p = subprocess.run(["git", "-C", root, "config", "--get", "core.worktree"], capture_output=True, text=True, timeout=5)
    except Exception:
        return None
    if p.returncode == 1 and not p.stdout.strip():
        return ""
    if p.returncode != 0:
        return None
    wt = to_windows(p.stdout.strip())
    return wt if is_abs(wt) else os.path.normpath(os.path.join(root, ".git", wt))


# shell prefixes that run the NEXT word as the real command (so `command git … reset` must expose `git`, not hide it).
# These take no args of their own, so we strip them and re-read the head. (env/sudo/nohup/time stay WRAPPERS: they
# can carry their own args before the command, so they are handled opaquely there.)
CMD_PREFIX = ("command", "builtin", "exec", "then", "do", "else", "elif", "!", "..", ";")


def head_of(toks):
    """Skip env assignments (collecting them), PowerShell call operators, and command-prefix keywords; return
    (index, cleaned lowercase basename, env). base carries any residual shell-expansion metachar so the caller can
    render it UNREAD (git${IFS}reset, $'\\x67it', $G all reach here without being mistaken for a safe literal)."""
    i, env, called = 0, {}, False
    while i < len(toks):
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", toks[i]) and "=" in toks[i]:
            k, v = toks[i].split("=", 1)
            env[k.upper()] = to_windows(v)
            i += 1
            continue
        if toks[i] in ("&", "."):
            called = True  # PowerShell's call operator: what follows IS invoked, even a variable
            i += 1
            continue
        if clean_head(toks[i]).rsplit("/", 1)[-1] in CMD_PREFIX:
            i += 1
            continue
        break
    if i >= len(toks):
        return i, "", env, called
    head = clean_head(toks[i])
    base = head.rsplit("/", 1)[-1]
    if base.endswith(".exe"):
        base = base[:-4]
    if "::start" in head or "diagnostics.process" in head:
        base = "start-process"  # a .NET process start is a wrapper by any name (a bare `]::` — [math]::Round — is not; S126)
    if base.endswith("()"):
        base = "function"  # NAME() { … } defines a command
    return i, base, env, called


def parse_git(toks, i):
    """toks[i] is git. Return (verb, args, target_override, alias_on_line); the override comes from --work-tree, -C or
    --git-dir (the directory holding that .git), in that precedence."""
    i += 1
    c_path = work_tree = git_dir = None
    alias_on_line = False
    while i < len(toks):
        t = clean_token(toks[i])       # backslash-stripped: for matching flag NAMES only
        raw = unquote(toks[i])         # quotes off, backslashes KEPT: for path VALUES (ERR at clone-6: the equals
        #                                forms read t, so a Windows path lost its separators and became UNREAD garbage)
        if t == "-C" and i + 1 < len(toks):
            c_path = to_windows(toks[i + 1])
            i += 2
            continue
        if t.startswith("--work-tree="):
            work_tree = to_windows(raw.split("=", 1)[1])
            i += 1
            continue
        if t == "--work-tree" and i + 1 < len(toks):
            work_tree = to_windows(toks[i + 1])
            i += 2
            continue
        if t.startswith("--git-dir="):
            git_dir = to_windows(raw.split("=", 1)[1])
            i += 1
            continue
        if t == "--git-dir" and i + 1 < len(toks):
            git_dir = to_windows(toks[i + 1])
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
        args = [unquote(x) for x in toks[i + 1:]]
        override = work_tree or c_path or (os.path.dirname(git_dir.rstrip("/\\")) if git_dir else None)
        return t.lower(), args, override, alias_on_line
    override = work_tree or c_path or (os.path.dirname(git_dir.rstrip("/\\")) if git_dir else None)
    return "", [], override, alias_on_line


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
        env_target = None  # GIT_WORK_TREE / GIT_DIR exported earlier in the same command
        cur_unresolved = False  # cur came from a `cd $VAR` the guard could not resolve
        worktree_redirect = False  # an earlier segment set core.worktree — a later unguarded-repo verb is UNREAD
        for seg in segments(text, tool == "PowerShell"):
            toks = tokens(seg)
            if not toks:
                continue
            i, base, env, called = head_of(toks)
            for k in ENV_TARGETS:
                if k in env and not base:  # a bare assignment segment: it persists for the rest of the command
                    env_target = env[k] if k == "GIT_WORK_TREE" else os.path.dirname(env[k].rstrip("/\\"))
            if not base:
                continue
            if base == "export" and len(toks) > i + 1:
                for t in toks[i + 1:]:
                    m = re.match(r"^(GIT_WORK_TREE|GIT_DIR)=(.+)$", clean_token(t), re.I)
                    if m:
                        v = to_windows(m.group(2))
                        env_target = v if m.group(1).upper() == "GIT_WORK_TREE" else os.path.dirname(v.rstrip("/\\"))
                continue
            if base in DIR_WORDS and len(toks) > i + 1:
                target = to_windows(toks[-1])
                # S141 (guard-holes/cd-tilde-and-cd-dash; the S140 second reading's I6): `cd ~` is knowable — the profile;
                # `cd -` is the shell's previous directory, which the guard cannot know — UNREAD, like `cd $VAR`; before
                # this both were no-ops for the tracked cwd, so `cd -; git branch -D x` from an unguarded cwd was ALLOWED
                if target == "~" or target.startswith("~/") or target.startswith("~\\"):
                    home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
                    target = home if target == "~" else os.path.join(home, target[2:])
                elif target == "-":
                    cur_unresolved = True  # the previous directory: the guard is not a shell and does not know it
                    cur = target
                    continue
                if is_unresolved(target):
                    cur_unresolved = True  # we no longer know where we are; a bare destructive verb here is UNREAD
                    cur = target
                    continue
                cur_unresolved = False
                cur = target if is_abs(target) else os.path.join(cur, target)
                continue
            here = None if cur_unresolved else guarded(cur)
            m = re.match(r"^\$env:(git_work_tree|git_dir)$", base)
            if m and len(toks) > i + 1:  # PowerShell: $env:GIT_WORK_TREE = '<path>'
                v = to_windows(toks[-1])
                env_target = v if m.group(1) == "git_work_tree" else os.path.dirname(v.rstrip("/\\"))
                continue
            # an UNREAD head — a shell variable, ANSI-C/parameter/command expansion, or a word the shell will assemble
            # at runtime ($G, $'\\x67it', git${IFS}reset, `printf git`). Test the RAW token: clean_head splits on '/'
            # and would drop a leading '$' before a stripped backslash ($'\\x67it' -> x67it). We cannot know the
            # command; fail closed.
            head_raw = toks[i]
            expands = any(c in base for c in ("$", "`", "{", "%")) or any(c in head_raw for c in ("$", "`")) \
                or re.search(r"%[A-Za-z_][A-Za-z0-9_]*%", head_raw) is not None
            # PowerShell (S12, a platform-semantics trap the guard itself fell into): a bare `$x …` is an EXPRESSION or an
            # assignment (`$_.Name -like …`, `$t = Get-Process`), never an invocation — `$G reset` is a syntax error there;
            # only the call operator (`& $G …`, `. $G`) invokes a variable. The guard false-denied a read-only
            # `Where-Object { $_.TaskName -like "*File Portal*" }` for a "$_.taskname" head (S125, 05:1xZ).
            # (S126: the exception keys on the RAW token — `$w.WorkingSet64/1MB` has basename `1mb`, its `$` lost to the
            # path split; the fourth false deny of this family.)
            # (S127: a QUOTED string as a PowerShell head — a `switch` case label "{D6886603-…}" — is an expression too;
            # the `{` inside it is data, not bash brace expansion. The fifth shape.)
            if expands and tool == "PowerShell" and not called and head_raw.lstrip("(").startswith(("$", "'", '"')):
                expands = False
            if expands:
                if here:
                    return f"guard_git: a command head the shell expands ({base[:40]}) is UNREAD in the shared checkout {here}; denied ({LAW})"
                # even from an unguarded cwd, an explicit -C/--work-tree/--git-dir/env target may name the shared tree
                hit = targets_named(toks, i, cur, guarded)
                if hit:
                    return f"guard_git: a command head the shell expands ({base[:40]}) carries a target at the shared checkout {hit}; UNREAD, denied ({LAW})"
                continue
            if base in DEFINERS:
                if here or names_guarded_root(text):
                    return (f"guard_git: the command defines its own command names ({base}) — what they run is UNREAD in the shared "
                            f"checkout; denied ({LAW})")
                continue
            if base in WRAPPERS:
                mentions_git = re.search(r"(?i)\bgit(\.exe)?\b", seg) is not None
                # an encoded command (-EncodedCommand / -enc / -e <base64>) is a POWERSHELL flag: only a powershell/pwsh
                # head carries one. (S126: `timeout 40 ssh … grep -E "…"` was denied for grep's -E — a third live false deny.)
                unreadable = base in ("eval", "iex", "invoke-expression", "invoke-command", "icm") or \
                    (base in ("powershell", "pwsh") and ENCODED.search(seg) is not None)
                if here and (mentions_git or unreadable):
                    why = "carries an encoded or evaluated command" if unreadable else "mentions git"
                    return (f"guard_git: a wrapper ({base}) {why} inside the shared checkout {here}; run git directly so the guard "
                            f"can read its verb and target — or this verb is forbidden here ({LAW})")
                if mentions_git and names_guarded_root(seg):
                    return f"guard_git: a wrapper ({base}) mentions git and names a shared checkout; run git directly ({LAW})"
                if depth < 3 and base in SHELL_WRAPPERS:
                    for t in toks[i + 1:]:
                        if len(t) > 2 and t[0] in "'\"" and t[-1] == t[0]:
                            r = scan(t[1:-1], cur, depth + 1)
                            if r:
                                return r
                continue
            if base != "git":
                continue
            verb, args, override, alias_on_line = parse_git(toks, i)
            seg_env = None
            for k in ENV_TARGETS:
                if k in env:
                    seg_env = env[k] if k == "GIT_WORK_TREE" else os.path.dirname(env[k].rstrip("/\\"))
            # is the target UNREAD — a value the shell will expand that the guard cannot? (the clone-6 destroyer:
            # `git --work-tree="$CLONE" --git-dir="$CLONE/.git" checkout` slipped through as a literal "$CLONE")
            target_unread = (override is not None and is_unresolved(override)) or (seg_env is not None and is_unresolved(seg_env)) \
                or (env_target is not None and is_unresolved(env_target)) \
                or (override is None and seg_env is None and env_target is None and cur_unresolved)
            is_write = verb not in READ_ONLY  # for a lane, anything not read-only is a write; TIER1 is destruction for anyone
            # setting core.worktree is a redirection primitive: it aims one repo's git at another's working tree
            if verb == "config" and any("core.worktree" == clean_token(a).lower() for a in args):
                worktree_redirect = True
                idx_cw = next((j for j, a in enumerate(args) if clean_token(a).lower() == "core.worktree"), -1)
                val = args[idx_cw + 1] if -1 < idx_cw < len(args) - 1 else ""
                unset = any(a in ("--unset", "--unset-all") for a in args)
                if not unset:
                    if lane or is_unresolved(val):
                        return f"guard_git: `git config core.worktree` (a working-tree redirection) with an UNREAD or lane-issued value is denied ({LAW})"
                    vabs = to_windows(val) if is_abs(to_windows(val)) else os.path.normpath(os.path.join(cur, to_windows(val)))
                    if guarded(vabs):
                        return f"guard_git: `git config core.worktree` pointing into the shared checkout {guarded(vabs)} is denied ({LAW})"
            target = override or seg_env or env_target or cur
            if not is_abs(target):
                target = os.path.join(cur, target)
            root = guarded(target)
            if root is None:
                if target_unread and (verb in TIER1 or (lane and is_write) or worktree_redirect):
                    return (f"guard_git: `git {verb}` has an UNREAD target (a shell-expanded path the guard cannot resolve) and "
                            f"cannot be proven to spare the shared checkout; denied — use a concrete path, a worktree, or the logged bypass ({LAW})")
                # an unguarded repository whose core.worktree points INTO a guarded tree drives a guarded working tree
                r0, kind0 = repo_root_of(target)
                if r0 and kind0 == "dir" and (verb in TIER1 or lane):
                    if worktree_redirect:
                        return f"guard_git: `git {verb}` in {r0} after a core.worktree redirect in the same command is UNREAD; denied ({LAW})"
                    wt = core_worktree(r0)
                    if wt is None:
                        return f"guard_git: core.worktree of {r0} could not be read; UNREAD, denied ({LAW})"
                    if wt and guarded(wt):
                        return f"guard_git: {r0} has core.worktree inside the shared checkout {guarded(wt)}; `git {verb}` there is denied ({LAW})"
                continue
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
            if verb == "commit" and root in roots:
                # J63 (S127): the record precedes the act, mechanically. open.sh publishes the session number in
                # coordination/private/session.current; a commit in the shared checkout while sessions/S<N>-*.md for that
                # number does not exist is refused (ERR-063 / -078 / -080: three sessions in a row committed instruments
                # before their record). No marker = no open ran = refused too (the MUSTER law: open first).
                why = record_missing(root)
                if why:
                    return f"guard_git: `git commit` refused — {why} (J63: the record precedes the act, docs/28)"
            if verb == "push" and root in roots:
                # J71 (S136): the ledger row is validated by its reader before it reaches origin. A push that
                # carries a CLAUDE_README.md change runs row_check.sh <N>; exit 1 denies; everything else is
                # UNREAD and allowed (a guard that cannot judge does not block a push).
                why = row_check_missing(root)
                if why:
                    return why
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

    if tool != "PowerShell":
        cmd_for_scan, why = fold_data_heredocs(cmd, guarded(cwd) is not None, names_guarded_root)
        if why:
            return "deny", why, tool, cwd, cmd
    else:
        cmd_for_scan = cmd
    reason = scan(cmd_for_scan, cwd, 0)
    if reason:
        return "deny", reason, tool, cwd, cmd
    return "allow", "", tool, cwd, cmd


def fold_data_heredocs(cmd, cwd_guarded, names_guarded_root):
    """J64 (S137): a heredoc body is shell text only when its RECEIVER is a shell — `bash <<EOF`, `sh <<EOF`, or the
    opener line pipes into one (`cat <<EOF | sh`). Those bodies stay and are scanned line by line as before (the R1/R2
    red-team cases). A body fed to anything else — python, cat > file, tee, git commit -F -, printf — is that program's
    DATA: it is removed before the scan, so a Python line ` - [%s] %s:%s %s` or a message line `git reset --hard` is
    never read as a command (SYM-110's eleventh shape, S133–S136: every heredoc with a format string was denied).
    One narrowing that CLOSES a hole rather than opening one: a body fed to a non-shell WRAPPER (python, node, perl,
    ruby, uv, …) that mentions git while the cwd is a guarded root (or the body names one) is denied as UNREAD — `python - <<EOF` with
    `os.system("git reset --hard")` in the body had no `git` head and passed the old scan.
    Returns (text_for_scan, deny_reason_or_None)."""
    lines = cmd.split("\n")
    out, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        m = HEREDOC.search(line)
        if not m:
            out.append(line)
            i += 1
            continue
        tag = m.group(2)
        strip_tabs = "<<-" in line[:m.end()]
        # the opener line's heads: every segment of this one line
        heads = []
        for seg in segments(line, False):
            t = tokens(seg)
            if not t:
                continue
            _, base, _, _ = head_of(t)
            if base:
                heads.append(base)
        shellish = any(h in ("bash", "sh", "zsh", "dash", "ksh", "fish", "eval", "source", ".") for h in heads)
        wrapperish = any(h in WRAPPERS for h in heads)
        body, j = [], i + 1
        while j < n:
            probe = lines[j].lstrip("\t") if strip_tabs else lines[j]
            if probe.rstrip("\r") == tag:
                break
            body.append(lines[j])
            j += 1
        if shellish:
            out.append(line)
            out.extend(body)
            if j < n:
                out.append(lines[j])
            i = j + 1
            continue
        body_text = "\n".join(body)
        if wrapperish and re.search(r"(?i)\bgit(\.exe)?\b", body_text) and (cwd_guarded or names_guarded_root(body_text)):
            return cmd, (f"guard_git: a heredoc fed to a program ({', '.join(h for h in heads if h in WRAPPERS)}) mentions git "
                         f"inside the shared checkout; what the program does with it is UNREAD; denied ({LAW})")
        out.append(line)          # the opener stays (its own head is scanned); the body is data and goes
        if j < n:
            out.append(lines[j])
        i = j + 1
    return "\n".join(out), None


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
