#!/usr/bin/env python
"""PreToolUse (Edit | Write | MultiEdit | NotebookEdit) — J63: the record precedes the act, mechanically (S127).

WHAT THIS FILE DOES: a Claude Code PreToolUse hook script. main() reads the hook payload (JSON) from stdin, decide()
finds the file the tool is about to write and, when it lies inside this repository (or a root named in
FP_GIT_GUARD_EXTRA_ROOTS) and the session record is missing, returns a refusal. main() prints that refusal as a deny
JSON on stdout and appends a DENY line to the guard log through guard_git.log(). It reads the session marker and the
sessions/ folder (through guard_git.record_missing) and writes only that log.

ERR-063 (S120), ERR-078 (S126), ERR-080 (S127): three sessions in a row edited and committed instruments before the
session's own record existed. docs/28's chokepoint — "recording precedes action" — was a discipline; this makes it a
gate on the one act it can see: a write to a TRACKED file of this repository.

  - The card (`open.sh`) publishes the session number in coordination/private/session.current (`S<N> <machine> <utc>`).
  - A write to a file inside the repository's tracked tree is DENIED while sessions/S<N>-*.md does not exist, or while
    no marker exists (no open ran). The message says what to write.
  - EXEMPT: the sessions/ directory itself (the record is what gets written), the scratchpad and anything outside the
    repository, `coordination/private/` (untracked, per-machine), and a repository without a coordination/ directory.
  - FAILS CLOSED on an unreadable payload; a tool input without a file path is not a write and passes.

Shares `record_missing(root)` with guard_git.py, which applies the same rule to `git commit` in the shared checkout —
so an instrument written through a script (invisible to this hook) is still stopped at its commit. Together they are
the tripwire ERR-078 named. Tripwire for this file: `.claude/hooks/guard_record_selftest.py`.
"""
import json
import os
import sys

# -- setup: import the shared rule and log from guard_git.py (the sibling file), and the extra-roots variable --
HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HOOK_DIR)
from guard_git import REPO, log, record_missing  # noqa: E402  (stdlib-only sibling; the shared rule and the ONE log live there)

EXTRA_ROOTS_ENV = os.environ.get("FP_GIT_GUARD_EXTRA_ROOTS") or ""


# -- which roots and which target path --
def roots():
    """Set of guarded roots for this hook: REPO plus each path in FP_GIT_GUARD_EXTRA_ROOTS (normalised). No side effects.
    (Unlike guard_git.guarded_roots it does not read the roots file.)"""
    out = {REPO}
    for extra in EXTRA_ROOTS_ENV.split(os.pathsep):
        if extra.strip():
            out.add(os.path.normcase(os.path.realpath(extra.strip())))
    return out


def target_of(payload):
    """The file path the tool will write: the first non-empty string among tool_input file_path, notebook_path, path;
    None when there is none."""
    tin = payload.get("tool_input") or {}
    for key in ("file_path", "notebook_path", "path"):
        v = tin.get(key)
        if isinstance(v, str) and v:
            return v
    return None


# -- the verdict --
def decide(payload):
    """Judge one payload (a dict). Returns a refusal string (deny) or None (allow). A writing tool with no target is
    refused; a path outside every root, under sessions/ or under coordination/private/ passes; any other path inside a
    root passes only when guard_git.record_missing(root) finds the session record (or the root has no coordination/
    folder, where record_missing returns None)."""
    path = target_of(payload)
    if not path:
        # S141 (guard-holes/guard-record-selftest-shapes; the S140 second reading's I8): the matcher fires only for the writing
        # tools, so a writing tool with NO target is a payload the guard cannot read — UNREAD fails closed, it does not pass
        tool = str(payload.get("tool_name") or "")
        if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
            return f"guard_record: a {tool} with no file_path / notebook_path / path — the target is UNREAD; denied (fails closed)"
        return None
    # find the root that contains the resolved target path, then apply the exemptions and the record check
    p = os.path.normcase(os.path.realpath(path))
    for root in roots():
        if not (p == root or p.startswith(root.rstrip("\\/") + os.sep)):
            continue
        rel = p[len(root):].lstrip("\\/")
        top = rel.split(os.sep)[0].lower() if rel else ""
        if top == "sessions":
            return None  # the record itself
        if rel.lower().startswith(os.path.join("coordination", "private").lower()):
            return None  # untracked, per-machine
        why = record_missing(root)
        if why:
            return f"guard_record: a write to `{rel}` refused — {why} (J63: the record precedes the act, docs/28)"
        return None
    return None


# -- output and entry point --
def emit_deny(reason, payload=None):
    """Print the PreToolUse deny JSON for `reason` on stdout, then log a DENY line (tool, cwd, the first 200 characters
    of tool_input, agent id and type, `guard=record`) through guard_git.log(). `payload` may be None. Returns None."""
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}))
    # S141 (cross-checks/journal-denies-equal-guard-log): every deny goes to the same log guard_git writes — until now
    # guard_record's denies existed only in the transcript, so the log could not corroborate the journal's count
    p = payload if isinstance(payload, dict) else {}
    log("DENY", p.get("tool_name") or "?", p.get("cwd") or "?", str(p.get("tool_input") or {})[:200],
        who="%s/%s" % (p.get("agent_id") or "-", p.get("agent_type") or "-"), extra="guard=record")


def main():
    """Hook entry: read the JSON payload from stdin, call decide() and print a deny through emit_deny() when it returns
    a reason. An unreadable payload or any exception in decide() is a deny (fails closed). Returns None."""
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace"))
        if not isinstance(payload, dict):
            raise ValueError("payload is not an object")
    except Exception as e:
        emit_deny(f"guard_record: could not read the hook payload ({e}) — UNREAD is not clean; denied")
        return
    try:
        reason = decide(payload)
    except Exception as e:
        emit_deny(f"guard_record: internal error ({e}) — fails closed; denied", payload)
        return
    if reason:
        emit_deny(reason, payload)


if __name__ == "__main__":
    main()
