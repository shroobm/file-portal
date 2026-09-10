"""guard_git_selftest.py — the tripwire for guard_git.py (docs/32 §6: a guard born today gets its tripwire today).

Builds a throwaway repository under the scratchpad with ONE real linked worktree, registers the throwaway main
checkout as a guarded root through the hook's environment (never the real roots file), points the hook's log at a
scratch file, and feeds the hook payloads by subprocess exactly as the harness would. Case 0 is the positive
control (a harmless `git status` passes); every other case violates the property its guard stands for, or proves
the guard is SCOPED (an unguarded repository and a linked worktree pass). Prints its own count; exit 1 on any red.

Run:  python .claude/hooks/guard_git_selftest.py
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "guard_git.py")
REPO = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PY = sys.executable


def sh(args, cwd):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True)


def run_hook(payload_text, env_extra):
    env = dict(os.environ)
    env.update(env_extra)
    p = subprocess.run([PY, HOOK], input=payload_text, capture_output=True, text=True, env=env)
    out = p.stdout.strip()
    if not out:
        return "allow", p
    try:
        j = json.loads(out)
        return j["hookSpecificOutput"]["permissionDecision"], p
    except Exception:
        return f"UNPARSEABLE:{out[:80]}", p


def payload(tool, cmd, cwd):
    return json.dumps({"session_id": "selftest", "hook_event_name": "PreToolUse", "tool_name": tool,
                       "tool_input": {"command": cmd}, "cwd": cwd})


def main():
    tmp = tempfile.mkdtemp(prefix="guard-selftest-", dir=os.environ.get("FP_SELFTEST_DIR") or None)
    main_repo = os.path.join(tmp, "main")
    other_repo = os.path.join(tmp, "unguarded")
    wt = os.path.join(tmp, "wt")
    logf = os.path.join(tmp, "guard.log")
    env = {"FP_GIT_GUARD_EXTRA_ROOTS": main_repo, "FP_GIT_GUARD_LOG": logf}
    results = []
    expected_denies = []  # derived, never hand-typed (SYM-039: a hand-typed count is a future defect)

    def case(n, name, expect, got, extra=""):
        ok = got == expect
        results.append(ok)
        if expect == "deny":
            expected_denies.append(n)
        print(f"  [{n:>3}] {'ok ' if ok else 'RED'} {name}: expect {expect}, got {got} {extra}")

    try:
        for r in (main_repo, other_repo):
            os.makedirs(r)
            sh(["git", "init", "-q", "-b", "main"], r)
            sh(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "one"], r)
            sh(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "two"], r)
        sh(["git", "worktree", "add", "-q", wt, "-b", "lane"], main_repo)
        assert os.path.isfile(os.path.join(wt, ".git")), "the linked worktree's .git must be a FILE"
        assert os.path.isdir(os.path.join(main_repo, ".git")), "the main checkout's .git must be a DIRECTORY"
        msys_main = "/" + main_repo[0].lower() + "/" + main_repo[3:].replace("\\", "/")

        print("guard_git selftest — throwaway repo", tmp)
        # 0 positive control
        case(0, "positive control: git status in the guarded main", "allow", run_hook(payload("Bash", "git status", main_repo), env)[0])
        # the six verbs in the guarded main
        for i, verb in enumerate(["reset --hard HEAD~1", "checkout -- .", "clean -fdx", "stash", "restore .", "switch -"], 1):
            case(i, f"git {verb.split()[0]} in the guarded main", "deny", run_hook(payload("Bash", f"git {verb}", main_repo), env)[0])
        # scoping: linked worktree and unguarded repo pass
        case(7, "git reset --hard inside the LINKED WORKTREE passes", "allow", run_hook(payload("Bash", "git reset --hard HEAD~1", wt), env)[0])
        case(8, "git reset --hard in an UNGUARDED repository passes", "allow", run_hook(payload("Bash", "git reset --hard HEAD~1", other_repo), env)[0])
        # targeting forms
        case(9, "git -C <main> checkout from elsewhere", "deny", run_hook(payload("Bash", f'git -C "{main_repo}" checkout -- .', tmp), env)[0])
        case(10, "cd <main> (MSYS path) && git clean", "deny", run_hook(payload("Bash", f"cd {msys_main} && git clean -fdx", tmp), env)[0])
        case(11, "--work-tree=<main> reset from elsewhere", "deny", run_hook(payload("Bash", f'git --work-tree="{main_repo}" reset --hard', tmp), env)[0])
        case(12, "PowerShell tool: Set-Location <main>; git stash", "deny", run_hook(payload("PowerShell", f"Set-Location '{main_repo}'; git stash", tmp), env)[0])
        case(13, "options before the verb (-c, --no-pager) still read", "deny", run_hook(payload("Bash", "git -c core.autocrlf=false --no-pager checkout -b x", main_repo), env)[0])
        case(14, "later segment: git status && git reset --hard", "deny", run_hook(payload("Bash", "git status && git reset --hard", main_repo), env)[0])
        case(15, "a wrapper hides the verb: bash -c 'git reset --hard'", "deny", run_hook(payload("Bash", "bash -c 'git reset --hard'", main_repo), env)[0])
        # not a git invocation: the verb inside data passes
        case(16, "echo \"git reset --hard\" passes (first token is echo)", "allow", run_hook(payload("Bash", 'echo "git reset --hard"', main_repo), env)[0])
        case(17, "grep 'git reset' file passes", "allow", run_hook(payload("Bash", "grep -n 'git reset' SYMPTOM-INDEX.md", main_repo), env)[0])
        # fail closed
        case(18, "malformed payload denies", "deny", run_hook("this is not json", env)[0])
        case(19, "payload without a command denies", "deny", run_hook(json.dumps({"tool_name": "Bash", "tool_input": {}, "cwd": main_repo}), env)[0])
        # the bypass: never silent
        got, _ = run_hook(payload("Bash", "FP_GIT_GUARD_BYPASS='selftest: proving the bypass is logged' git reset --hard", main_repo), env)
        logged = os.path.exists(logf) and "BYPASS" in io.open(logf, encoding="utf-8").read()
        case(20, "bypass with a 20+ char reason passes AND is logged", "allow+logged", f"{got}+{'logged' if logged else 'NOT LOGGED'}")
        case(21, "bypass with a short reason denies", "deny", run_hook(payload("Bash", "FP_GIT_GUARD_BYPASS='short' git reset --hard", main_repo), env)[0])
        # the real object: this repository is guarded by default, with no environment at all
        case(22, "the REAL checkout: git reset --hard denied with no env override", "deny", run_hook(payload("Bash", "git reset --hard feat/library-pipeline", REPO), {"FP_GIT_GUARD_LOG": logf})[0])
        case(23, "the REAL checkout: git status passes", "allow", run_hook(payload("Bash", "git status --short", REPO), {"FP_GIT_GUARD_LOG": logf})[0])
        # every deny was logged
        n_deny = sum(1 for line in io.open(logf, encoding="utf-8") if " DENY " in line) if os.path.exists(logf) else 0
        case(24, f"every DENY wrote a log line ({len(expected_denies)} deny cases so far)", len(expected_denies), n_deny)
    finally:
        try:
            subprocess.run(["git", "worktree", "remove", "--force", wt], cwd=main_repo, capture_output=True)
        except Exception:
            pass
        shutil.rmtree(tmp, ignore_errors=True)

    n_ok = sum(results)
    print(f"guard_git selftest: {n_ok}/{len(results)} green" + ("" if n_ok == len(results) else "  *** RED ***"))
    sys.exit(0 if n_ok == len(results) else 1)


if __name__ == "__main__":
    main()
