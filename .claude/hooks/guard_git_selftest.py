"""guard_git_selftest.py — the tripwire for guard_git.py (docs/32 §6: a guard born today gets its tripwire today).

Builds a throwaway repository under the temp dir with ONE real linked worktree and one unguarded neighbour,
registers the throwaway main checkout as a guarded root through the hook's environment (never the real roots
file), points the hook's log at a scratch file, and feeds the hook payloads by subprocess exactly as the harness
would. Case 0 is the positive control (a harmless `git status` passes); every other case violates the property its
guard stands for, or proves the guard is SCOPED (an unguarded repository, a linked worktree, a script file, a
verb inside data all pass). The deny count is derived, never typed. Prints its own count; exit 1 on any red.

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
    p = subprocess.run([PY, HOOK], input=payload_text.encode("utf-8"), capture_output=True, env=env)
    out = p.stdout.decode("utf-8", errors="replace").strip()
    if not out:
        return "allow", p
    try:
        j = json.loads(out)
        return j["hookSpecificOutput"]["permissionDecision"], p
    except Exception:
        return f"UNPARSEABLE:{out[:80]}", p


def payload(tool, cmd, cwd, agent=None):
    d = {"session_id": "selftest", "hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": {"command": cmd}, "cwd": cwd}
    if agent:
        d["agent_id"] = agent
        d["agent_type"] = "selftest-lane"
    return json.dumps(d, ensure_ascii=False)


def main():
    tmp = tempfile.mkdtemp(prefix="guard-selftest-")
    main_repo = os.path.join(tmp, "main")
    other_repo = os.path.join(tmp, "unguarded")
    wt = os.path.join(tmp, "wt")
    logf = os.path.join(tmp, "guard.log")
    env = {"FP_GIT_GUARD_EXTRA_ROOTS": main_repo, "FP_GIT_GUARD_LOG": logf}
    results, expected_denies = [], []

    def case(name, expect, got, tool="Bash", ):
        n = len(results)
        ok = got == expect
        results.append(ok)
        if expect == "deny":
            expected_denies.append(n)
        print(f"  [{n:>3}] {'ok ' if ok else 'RED'} {name}: expect {expect}, got {got}")

    def bash(cmd, cwd=None, agent=None, e=None):
        return run_hook(payload("Bash", cmd, cwd or main_repo, agent), e if e is not None else env)[0]

    def ps(cmd, cwd=None, agent=None):
        return run_hook(payload("PowerShell", cmd, cwd or main_repo, agent), env)[0]

    try:
        for r in (main_repo, other_repo):
            os.makedirs(r)
            sh(["git", "init", "-q", "-b", "main"], r)
            sh(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "one"], r)
            sh(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "two"], r)
        sh(["git", "worktree", "add", "-q", wt, "-b", "lane"], main_repo)
        sh(["git", "config", "alias.zap", "reset --hard"], main_repo)
        sh(["git", "config", "alias.ll", "log --oneline"], main_repo)
        sh(["git", "config", "alias.boom", "!echo boom"], main_repo)
        assert os.path.isfile(os.path.join(wt, ".git")), "the linked worktree's .git must be a FILE"
        assert os.path.isdir(os.path.join(main_repo, ".git")), "the main checkout's .git must be a DIRECTORY"
        msys_main = "/" + main_repo[0].lower() + "/" + main_repo[3:].replace("\\", "/")

        print("guard_git selftest — throwaway repo", tmp)
        case("positive control: git status in the guarded main", "allow", bash("git status"))
        # TIER 1 — the twelve working-tree destroyers, everyone
        for verb in ("reset --hard HEAD~1", "checkout -- .", "clean -fdx", "stash", "restore .", "switch -", "read-tree -u --reset HEAD",
                     "checkout-index -a -f", "rm -f tracked.txt", "mv a b", "apply -R x.patch", "am x.mbox"):
            case(f"tier 1: git {verb.split()[0]} in the guarded main", "deny", bash(f"git {verb}"))
        case("tier 1 read-only-looking form still denied: git stash list", "deny", bash("git stash list"))
        # scoping
        case("git reset --hard inside the LINKED WORKTREE passes", "allow", bash("git reset --hard HEAD~1", wt))
        case("a LANE's git reset --hard inside the linked worktree passes", "allow", bash("git reset --hard HEAD~1", wt, agent="lane-1"))
        case("git reset --hard in an UNGUARDED repository passes", "allow", bash("git reset --hard HEAD~1", other_repo))
        case("git reset --hard in a non-repository directory passes", "allow", bash("git reset --hard", tmp))
        # targeting forms
        case("git -C <main> checkout from elsewhere", "deny", bash(f'git -C "{main_repo}" checkout -- .', tmp))
        case("cd <main> (MSYS path) && git clean", "deny", bash(f"cd {msys_main} && git clean -fdx", tmp))
        case("--work-tree=<main> reset from elsewhere", "deny", bash(f'git --work-tree="{main_repo}" reset --hard', tmp))
        case("subshell (cd <main> && git reset --hard) from elsewhere", "deny", bash(f"(cd {msys_main} && git reset --hard)", tmp))
        case("command substitution echo $(cd <main>; git reset --hard) from elsewhere", "deny", bash(f'echo "$(cd {msys_main}; git reset --hard)"', tmp))
        case("PowerShell: Set-Location <main>; git stash", "deny", ps(f"Set-Location '{main_repo}'; git stash", tmp))
        case("PowerShell: Push-Location <main>; & git reset --hard", "deny", ps(f"Push-Location '{main_repo}'; & git reset --hard", tmp))
        case("PowerShell call operator & git reset in main", "deny", ps("& git reset --hard"))
        case("git.exe reset in main", "deny", bash("git.exe reset --hard"))
        case("full path to git.exe reset in main", "deny", bash('"C:/Program Files/Git/bin/git.exe" reset --hard'))
        case("options before the verb (-c, --no-pager) still read", "deny", bash("git -c core.autocrlf=false --no-pager checkout -b x"))
        case("later segment: git status && git reset --hard", "deny", bash("git status && git reset --hard"))
        case("pipe: echo y | git checkout -- .", "deny", bash("echo y | git checkout -- ."))
        # obfuscation of the verb
        case("quote-split verb git re'set'", "deny", bash("git re'set' --hard"))
        case("backslash verb git res\\et", "deny", bash("git res\\et --hard"))
        case("variable verb VERB=reset; git $VERB", "deny", bash("VERB=reset; git $VERB --hard"))
        case("variable command head $G reset", "deny", bash("G=git; $G reset --hard"))
        case("alias on the line: git -c alias.zap=reset zap", "deny", bash("git -c 'alias.zap=reset --hard' zap"))
        case("configured alias to a tier-1 verb: git zap", "deny", bash("git zap"))
        case("configured shell alias: git boom (!echo)", "deny", bash("git boom"))
        case("configured read-only alias: git ll passes for the main session", "allow", bash("git ll"))
        case("unknown verb git frobnicate denied (no alias)", "deny", bash("git frobnicate"))
        # wrappers
        case("bash -c 'git reset --hard'", "deny", bash("bash -c 'git reset --hard'"))
        case("sh -c with cd inside", "deny", bash(f"sh -c 'cd {msys_main} && git reset --hard'", tmp))
        case("python -c subprocess git reset", "deny", bash("python -c \"import subprocess;subprocess.run(['git','reset','--hard'])\""))
        case("xargs git reset", "deny", bash("echo HEAD | xargs git reset --hard"))
        case("find -exec git checkout", "deny", bash("find . -name x -exec git checkout -- {} \\;"))
        case("eval in main (unreadable) denied even without the word git", "deny", bash('eval "$cmd"'))
        case("PowerShell -EncodedCommand in main denied", "deny", ps("powershell -EncodedCommand ZwBpAHQAIAByAGUAcwBlAHQA"))
        case("Invoke-Expression in main denied", "deny", ps('Invoke-Expression "git reset --hard"'))
        case("cmd /c git clean", "deny", ps('cmd /c "git clean -fdx"'))
        case("Start-Process git -ArgumentList reset", "deny", ps("Start-Process git -ArgumentList 'reset --hard'"))
        case("a wrapper that does not mention git passes: bash open.sh", "allow", bash("bash .claude/skills/muster/open.sh"))
        case("python script.py passes (a script file is residue, stated)", "allow", bash("python observability/error_families.py --census"))
        case("uv run python selftest.py passes", "allow", bash("uv run python .claude/skills/relay-gate/selftest.py"))
        # the verb inside data
        case('echo "git reset --hard" passes (first token is echo)', "allow", bash('echo "git reset --hard"'))
        case("grep 'git reset' file passes", "allow", bash("grep -n 'git reset' SYMPTOM-INDEX.md"))
        case("non-ASCII command passes: echo with an em dash and CJK", "allow", bash('echo "— 東京 — ok"'))
        case("non-ASCII branch still denied: git reset --hard 東京", "deny", bash("git reset --hard 東京"))
        # the lane tier
        case("LANE: git status passes", "allow", bash("git status --short", agent="lane-1"))
        case("LANE: git log / diff / fetch pass", "allow", bash("git log --oneline -3 && git diff --stat && git fetch -q", agent="lane-1"))
        case("LANE: git add -A denied", "deny", bash("git add -A", agent="lane-1"))
        case("LANE: git commit denied", "deny", bash("git commit -m x", agent="lane-1"))
        case("LANE: git pull denied", "deny", bash("git pull --rebase", agent="lane-1"))
        case("LANE: git push denied", "deny", bash("git push", agent="lane-1"))
        case("LANE: git branch (list) passes", "allow", bash("git branch --show-current", agent="lane-1"))
        case("LANE: git branch -D denied", "deny", bash("git branch -D x", agent="lane-1"))
        case("LANE: git config --get passes", "allow", bash("git config --get core.autocrlf", agent="lane-1"))
        case("LANE: git config alias.z (a write) denied", "deny", bash("git config alias.z 'reset --hard'", agent="lane-1"))
        case("LANE: git worktree list passes", "allow", bash("git worktree list", agent="lane-1"))
        case("LANE: git worktree add denied", "deny", bash("git worktree add ../x", agent="lane-1"))
        case("LANE: unknown verb denied without an alias lookup", "deny", bash("git ll", agent="lane-1"))
        case("LANE: git tag -l passes", "allow", bash("git tag -l", agent="lane-1"))
        case("LANE: git tag v1 denied", "deny", bash("git tag v1", agent="lane-1"))
        # environment-directed targets, from an unguarded cwd
        case("GIT_WORK_TREE=<main> prefix from elsewhere", "deny", bash(f"GIT_WORK_TREE={msys_main} GIT_DIR={msys_main}/.git git reset --hard", tmp))
        case("export GIT_DIR=<main>/.git; git clean from elsewhere", "deny", bash(f"export GIT_DIR={msys_main}/.git; git clean -fdx", tmp))
        case("PowerShell $env:GIT_WORK_TREE = <main>; git reset from elsewhere", "deny", ps(f"$env:GIT_WORK_TREE = '{main_repo}'; git reset --hard", tmp))
        case("--git-dir=<main>/.git reset from elsewhere", "deny", bash(f'git --git-dir="{main_repo}/.git" reset --hard', tmp))
        # self-defined command names
        case("alias g=git; g reset --hard in main", "deny", bash("alias g=git; g reset --hard"))
        case("Set-Alias g git; g reset --hard in main", "deny", ps("Set-Alias g git; g reset --hard"))
        case("function g { git reset --hard }; g in main", "deny", ps("function g { git reset --hard }; g"))
        case("g() { git reset --hard; }; g in main", "deny", bash("g() { git reset --hard; }; g"))
        case("alias defined from elsewhere naming <main>", "deny", bash(f"alias g='git -C {msys_main}'; g reset --hard", tmp))
        case("an alias with no shared checkout in play passes", "allow", bash("alias ll='ls -la'; ll", tmp))
        # more process starters
        case(".NET Process::Start git reset in main", "deny", ps("[System.Diagnostics.Process]::Start('git','reset --hard')"))
        case("wsl git reset in main", "deny", bash("wsl git reset --hard"))
        case("schtasks scheduling a git reset in main", "deny", ps('schtasks /create /tn x /tr "git reset --hard" /sc once /st 00:00'))
        case("Start-Job { git clean } in main", "deny", ps("Start-Job { git clean -fdx }"))
        # an unguarded repository whose core.worktree points INTO the guarded main
        sh(["git", "config", "core.worktree", main_repo], other_repo)
        case("core.worktree → <main>: git reset --hard in the unguarded repo denied", "deny", bash("git reset --hard", other_repo))
        case("core.worktree → <main>: git clean denied", "deny", bash("git clean -fdx", other_repo))
        case("core.worktree → <main>: a LANE's git add denied", "deny", bash("git add -A", other_repo, agent="lane-1"))
        case("core.worktree → <main>: git status still passes", "allow", bash("git status", other_repo))
        sh(["git", "config", "--unset", "core.worktree"], other_repo)
        case("core.worktree unset again: git reset --hard in the unguarded repo passes", "allow", bash("git reset --hard", other_repo))
        # THE RED-TEAM HOLES (clone-6, S124): an UNREAD target — a shell variable in --work-tree/--git-dir/-C/env/cd —
        # must fail closed for a destructive verb, not read as "not guarded".
        case("RED-TEAM: --git-dir=$C/.git --work-tree=$C checkout (the clone-6 destroyer)", "deny",
             bash('C=' + f'"{main_repo}"' + '; git --git-dir="$C/.git" --work-tree="$C" checkout -- tracked.txt', tmp))
        case("RED-TEAM: --work-tree=$C reset --hard", "deny", bash('C=x; git --work-tree="$C" reset --hard', tmp))
        case("RED-TEAM: -C $C clean -fdx", "deny", bash('C=x; git -C "$C" clean -fdx', tmp))
        case("RED-TEAM: GIT_WORK_TREE=$C git reset", "deny", bash('C=x; GIT_WORK_TREE="$C" GIT_DIR="$C/.git" git reset --hard', tmp))
        case("RED-TEAM: cd $C && git reset --hard (unresolved cwd)", "deny", bash('C=x; cd "$C" && git reset --hard', tmp))
        case("RED-TEAM: %VAR% cmd-style var in --work-tree", "deny", ps('git --work-tree="%CLONE%" reset --hard', tmp))
        case("a variable target with a READ-ONLY verb from MAIN still passes (no destruction possible)", "allow", bash('C=x; git -C "$C" status', tmp))
        case("a LANE with a variable target and a write is denied (UNREAD)", "deny", bash('C=x; git -C "$C" add -A', tmp, agent="lane-1"))
        case("a concrete -C to an UNGUARDED repo with a var-free reset still passes", "allow", bash(f'git -C "{other_repo}" reset --hard', tmp))
        # THE SIBLING core.worktree-in-one-command hole (clone-6): set core.worktree then destroy, all before the hook can read it
        sib = os.path.join(tmp, "sibling")
        case("RED-TEAM: git config core.worktree <main> in a sibling is denied", "deny",
             bash(f'git init "{sib}"; git -C "{sib}" config core.worktree "{main_repo}"; git -C "{sib}" checkout -- .', tmp))
        case("RED-TEAM: a lane setting core.worktree anywhere is denied", "deny", bash(f'git -C "{other_repo}" config core.worktree /tmp/x', tmp, agent="lane-1"))
        case("git config core.worktree to an UNGUARDED path still passes for main", "allow", bash(f'git -C "{other_repo}" config core.worktree "{tmp}/harmless"', tmp))
        # CRITIC CLASS #1 — backslash Windows path in the equals form, from a NON-repo cwd (no accidental resolution)
        case("CRITIC: --work-tree=<backslash main> reset from a non-repo cwd", "deny", bash(f'git --work-tree="{main_repo}" --git-dir="{main_repo}\\.git" reset --hard', tmp))
        # CRITIC CLASS #2 — git behind a command prefix keyword
        case("CRITIC: command git -C <main> reset", "deny", bash(f'command git -C "{main_repo}" reset --hard'))
        case("CRITIC: exec git -C <main> clean", "deny", bash(f'exec git -C "{main_repo}" clean -fdx'))
        case("CRITIC: ! git -C <main> reset", "deny", bash(f'! git -C "{main_repo}" reset --hard'))
        case("CRITIC: if/then git reset in main", "deny", bash("if true; then git reset --hard; fi"))
        case("CRITIC: while/do git clean in main", "deny", bash("while :; do git clean -fdx; done"))
        # CRITIC CLASS #4 — ANSI-C quoted head that spells git
        case("CRITIC: $'\\x67it' -C <main> reset (ANSI-C, from unguarded cwd, -C names main)", "deny", bash(f"$'\\x67it' -C \"{main_repo}\" reset --hard", tmp))
        case("CRITIC: $'\\x67it' reset in main cwd", "deny", bash("$'\\x67it' reset --hard"))
        # CRITIC CLASS #5 — IFS word-glue head in main cwd
        case("CRITIC: git${IFS}reset --hard in main cwd", "deny", bash("git${IFS}reset --hard"))
        # CRITIC CLASS #6 — variable head, -C names the guarded tree, from an unguarded cwd
        case("CRITIC: G=git; $G -C <main> reset from unguarded cwd", "deny", bash(f'G=git; $G -C "{main_repo}" reset --hard', tmp))
        case("CRITIC: a variable head with NO guarded target from unguarded cwd still passes", "allow", bash("G=git; $G status", tmp))
        # FALSE-DENY REGRESSION (S124): arithmetic expansion is data, not a command — the guard denied a read-only sed
        # for a "$p" head it manufactured out of "$((L+1)),$p"
        case("arithmetic $((L+1)) in double quotes with a $p passes (read-only sed)", "allow",
             bash('L=5; sed -n "$((L+1)),\\$p" SYMPTOM-INDEX.md | head -3'))
        case("arithmetic $((1+2)) bare passes", "allow", bash("echo $((1+2)); git status"))
        case("a real $( ) command substitution with git reset in main is still denied", "deny", bash('echo "$(git reset --hard)"'))
        # FALSE-DENY REGRESSION (S125): PowerShell expression heads are not invocations
        case("PS: Where-Object { $_.TaskName -like ... } in main passes (expression head)", "allow",
             ps('Get-ScheduledTask | Where-Object { $_.TaskName -like "*File Portal*" } | ForEach-Object { $_.State }'))
        case("PS: $t = Get-Process; $t.Path in main passes (assignment + property)", "allow", ps("$t = Get-Process -Id 1; $t.Path"))
        case("PS: & $G reset --hard in main is still denied (the call operator invokes)", "deny", ps("$G = 'git'; & $G reset --hard"))
        case("PS: . $G clean in main is still denied", "deny", ps("$G = 'git'; . $G clean -fdx"))
        case("Bash: $G reset --hard in main is still denied (bash invokes a variable head)", "deny", bash("G=git; $G reset --hard"))
        # FALSE-DENY REGRESSION (S126): -E / -e are only ENCODED-COMMAND flags on a powershell head
        case("timeout ssh host 'grep -E ...' in main passes (grep's -E is not -EncodedCommand)", "allow",
             bash("timeout 40 ssh -o BatchMode=yes rab@archlinux 'systemctl --user cat x | grep -E \"ExecStart|WorkingDirectory\"'"))
        case("find -exec grep -e x in main passes (no git, -e is grep's)", "allow", bash("find . -name x -exec grep -e y {} \\;"))
        case("powershell -e <base64> in main is still denied", "deny", ps("powershell -e ZwBpAHQA"))
        case("pwsh -EncodedCommand in main is still denied", "deny", ps("pwsh -EncodedCommand ZwBpAHQA"))
        # FALSE-DENY REGRESSION (S126, the fourth shape): a PowerShell expression whose basename lost its `$`, and a
        # static method call that is not a process start
        case("PS: [math]::Round($w.WorkingSet64/1MB) in main passes (expression, not a process start)", "allow",
             ps("$w = Get-Process -Id 1; Write-Output ([math]::Round($w.WorkingSet64/1MB))"))
        case("PS: Get-CimInstance ... | Where-Object { $_.ParentProcessId -eq $w.Id } passes", "allow",
             ps('$kids = Get-CimInstance Win32_Process -Filter "Name = \'x.exe\'" | Where-Object { $_.ParentProcessId -eq $w.Id }; $kids.Count'))
        case("PS: [System.Diagnostics.Process]::Start git reset in main is still denied", "deny",
             ps("[System.Diagnostics.Process]::Start('git','reset --hard')"))
        # FALSE-DENY REGRESSION (S127, the fifth shape): a quoted-string head in PowerShell (a switch case label with a GUID)
        case("PS: switch ($x) { \"{D6886603-...}\" { 'PIN' } default { 'other' } } in main passes", "allow",
             ps('$p = "x"; $name = switch ($p.ToUpper()) { "{D6886603-9D2F-4EB2-B667-1971041FA96B}" { "PIN" } default { "other" } }; $name'))
        case("Bash: brace-expansion head {git,} reset in main is still denied", "deny", bash("{git,} reset --hard"))
        case("PS: & \"git\" reset in main is still denied (a quoted head after the call operator invokes)", "deny", ps('& "git" reset --hard'))
        # the main session's own writes
        case("MAIN: git add / commit / push pass", "allow", bash("git add x && git commit -q -m x && git push -q"))
        case("MAIN: git pull --rebase passes", "allow", bash("git pull --rebase"))
        case("MAIN: git worktree add passes", "allow", bash("git worktree add ../x"))
        # fail closed
        case("malformed payload denies", "deny", run_hook("this is not json", env)[0])
        case("payload without a command denies", "deny", run_hook(json.dumps({"tool_name": "Bash", "tool_input": {}, "cwd": main_repo}), env)[0])
        # the bypass: never silent
        got = bash("FP_GIT_GUARD_BYPASS='selftest: proving the bypass is logged' git reset --hard")
        logged = os.path.exists(logf) and "BYPASS" in io.open(logf, encoding="utf-8").read()
        case("bypass with a 20+ char reason passes AND is logged", "allow+logged", f"{got}+{'logged' if logged else 'NOT LOGGED'}")
        case("bypass with a short reason denies", "deny", bash("FP_GIT_GUARD_BYPASS='short' git reset --hard"))
        # the real object: this repository is guarded by default, with no environment at all
        case("the REAL checkout: git reset --hard denied with no env override", "deny", bash("git reset --hard feat/library-pipeline", REPO, e={"FP_GIT_GUARD_LOG": logf}))
        case("the REAL checkout: git status passes", "allow", bash("git status --short", REPO, e={"FP_GIT_GUARD_LOG": logf}))
        case("the REAL checkout: a LANE's git commit denied", "deny", bash("git commit -m x", REPO, agent="lane-1", e={"FP_GIT_GUARD_LOG": logf}))
        # every deny was logged
        n_deny = sum(1 for line in io.open(logf, encoding="utf-8") if " DENY " in line) if os.path.exists(logf) else 0
        case(f"every DENY wrote a log line ({len(expected_denies)} deny cases so far)", len(expected_denies), n_deny)
        n_agent = sum(1 for line in io.open(logf, encoding="utf-8") if " agent=lane-1/selftest-lane " in line) if os.path.exists(logf) else 0
        case("a lane's denials carry its agent id in the log", True, n_agent > 0)
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
