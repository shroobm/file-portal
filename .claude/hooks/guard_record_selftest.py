"""guard_record_selftest.py — the tripwire for guard_record.py (J63). A throwaway File Portal-shaped root (coordination/,
sessions/) registered through the hook's environment; payloads fed by subprocess. Case 0 is the positive control (the
record exists → a write passes); the rest violate the property or prove the exemptions. Deny count derived. Exit 1 on red.

Run:  python .claude/hooks/guard_record_selftest.py
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "guard_record.py")
PY = sys.executable


def run_hook(payload_text, env_extra):
    env = dict(os.environ)
    env.update(env_extra)
    p = subprocess.run([PY, HOOK], input=payload_text.encode("utf-8"), capture_output=True, env=env)
    out = p.stdout.decode("utf-8", errors="replace").strip()
    if not out:
        return "allow"
    try:
        return json.loads(out)["hookSpecificOutput"]["permissionDecision"]
    except Exception:
        return f"UNPARSEABLE:{out[:80]}"


def payload(tool, path):
    return json.dumps({"session_id": "selftest", "hook_event_name": "PreToolUse", "tool_name": tool,
                       "tool_input": {"file_path": path, "content": "x"}, "cwd": "C:/"})


def main():
    tmp = tempfile.mkdtemp(prefix="guard-record-")
    root = os.path.join(tmp, "repo")
    os.makedirs(os.path.join(root, "coordination", "private"))
    os.makedirs(os.path.join(root, "sessions"))
    os.makedirs(os.path.join(root, "docs"))
    marker = os.path.join(root, "coordination", "private", "session.current")
    env = {"FP_GIT_GUARD_EXTRA_ROOTS": root}
    results, denies = [], []

    def case(name, expect, got):
        n = len(results)
        ok = got == expect
        results.append(ok)
        if expect == "deny":
            denies.append(n)
        print(f"  [{n:>2}] {'ok ' if ok else 'RED'} {name}: expect {expect}, got {got}")

    try:
        print("guard_record selftest — throwaway root", root)
        io.open(marker, "w").write("S42 desktop 2026-09-10T00:00:00Z\n")
        io.open(os.path.join(root, "sessions", "S42-desktop-2026-09-10.md"), "w").write("# S42\n")
        case("positive control: marker + record → a write to docs/x.md passes", "allow", run_hook(payload("Write", os.path.join(root, "docs", "x.md")), env))
        os.remove(os.path.join(root, "sessions", "S42-desktop-2026-09-10.md"))
        case("marker but NO sessions/S42-*.md → a write to docs/x.md is refused", "deny", run_hook(payload("Write", os.path.join(root, "docs", "x.md")), env))
        case("… but a write to sessions/ (the record itself) passes", "allow", run_hook(payload("Write", os.path.join(root, "sessions", "S42-desktop-2026-09-10.md")), env))
        case("… and a write to coordination/private/ (untracked, per-machine) passes", "allow", run_hook(payload("Write", os.path.join(root, "coordination", "private", "x.log")), env))
        case("… and a write OUTSIDE the repository passes", "allow", run_hook(payload("Write", os.path.join(tmp, "elsewhere.md")), env))
        case("… and an Edit to a tracked file is refused like a Write", "deny", run_hook(payload("Edit", os.path.join(root, "README.md")), env))
        os.remove(marker)
        case("NO marker (no open ran) → a write to a tracked file is refused", "deny", run_hook(payload("Write", os.path.join(root, "docs", "x.md")), env))
        io.open(marker, "w").write("garbage\n")
        case("an unreadable marker refuses (UNREAD is not clean)", "deny", run_hook(payload("Write", os.path.join(root, "docs", "x.md")), env))
        case("a payload without a file path is not a write and passes", "allow", run_hook(json.dumps({"tool_name": "Write", "tool_input": {}}), env))
        case("a malformed payload is refused (fails closed)", "deny", run_hook("not json", env))
        shutil.rmtree(os.path.join(root, "coordination"))
        case("a root without coordination/ is exempt (not a File Portal checkout)", "allow", run_hook(payload("Write", os.path.join(root, "docs", "x.md")), env))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    n_ok = sum(results)
    print(f"guard_record selftest: {n_ok}/{len(results)} green" + ("" if n_ok == len(results) else "  *** RED ***"))
    sys.exit(0 if n_ok == len(results) else 1)


if __name__ == "__main__":
    main()
