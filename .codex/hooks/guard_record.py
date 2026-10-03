#!/usr/bin/env python
"""PreToolUse (Edit | Write | MultiEdit | NotebookEdit) — J63: the record precedes the act, mechanically (S127).

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

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HOOK_DIR)
from guard_git import REPO, log, record_missing  # noqa: E402  (stdlib-only sibling; the shared rule and the ONE log live there)

EXTRA_ROOTS_ENV = os.environ.get("FP_GIT_GUARD_EXTRA_ROOTS") or ""


def roots():
    out = {REPO}
    for extra in EXTRA_ROOTS_ENV.split(os.pathsep):
        if extra.strip():
            out.add(os.path.normcase(os.path.realpath(extra.strip())))
    return out


def target_of(payload):
    tin = payload.get("tool_input") or {}
    for key in ("file_path", "notebook_path", "path"):
        v = tin.get(key)
        if isinstance(v, str) and v:
            return v
    return None


def decide(payload):
    path = target_of(payload)
    if not path:
        # S141 (guard-holes/guard-record-selftest-shapes; the S140 second reading's I8): the matcher fires only for the writing
        # tools, so a writing tool with NO target is a payload the guard cannot read — UNREAD fails closed, it does not pass
        tool = str(payload.get("tool_name") or "")
        if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
            return f"guard_record: a {tool} with no file_path / notebook_path / path — the target is UNREAD; denied (fails closed)"
        return None
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


def emit_deny(reason, payload=None):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}))
    # S141 (cross-checks/journal-denies-equal-guard-log): every deny goes to the same log guard_git writes — until now
    # guard_record's denies existed only in the transcript, so the log could not corroborate the journal's count
    p = payload if isinstance(payload, dict) else {}
    log("DENY", p.get("tool_name") or "?", p.get("cwd") or "?", str(p.get("tool_input") or {})[:200],
        who="%s/%s" % (p.get("agent_id") or "-", p.get("agent_type") or "-"), extra="guard=record")


def main():
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
