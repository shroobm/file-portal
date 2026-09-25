#!/usr/bin/env python
"""PreToolUse/Bash — C3's mechanical half, for ERROR-BIN ERR-009.

ERR-009's own remedy, in its words: "anything containing backslashes or nested
quotes goes in a FILE via Write, never a heredoc." That rule was filed at 02:40
and broken at least twice afterwards, in the same session, including inside the
run that documented it. A rule I have to remember is not a rule; this is the
half a machine can hold.

It WARNS. It never blocks — most heredocs are fine, and a gate that fires on
every one would be tuned away within a day (close.sh's own DEBT comment says so).
S213 (2026-09-25, Rab's word on Desk 17258df3): ONE narrow case now BLOCKS, a
`python -c` whose program holds a backslash or a `$` (see below). The heredoc case
is untouched and still only warns, as signed.

⚠ THE OVER-SENSITIVITY IS SIGNED, NOT A DEFAULT. Rab, 2026-08-27: "I like the
over-sensitivity, I sign." It deliberately warns on \" and \' inside a QUOTED
heredoc, where the shell would not have interfered — because ERR-009's SECOND
instance was exactly that: a quoted heredoc that broke anyway, on Python string
termination rather than on the shell. Narrowing this to unquoted delimiters would
look like a tidy improvement and would silence the case that already bit.

So: do NOT tune this down to reduce noise without his word. A guard loosened
because it was annoying is the shape of every decayed tripwire in this project —
close.sh's own CI check decayed exactly that way and nobody noticed for a session.

Reads the hook payload on stdin, writes JSON on stdout. No jq on this machine,
and no shell layer, deliberately: a guard against quoting bugs must not be one.
"""
import json
import re
import sys

try:
    payload = json.load(sys.stdin)
except Exception:
    sys.exit(0)  # a failed probe is UNREAD, never a verdict — say nothing

cmd = (payload.get("tool_input") or {}).get("command") or ""

# A heredoc: << or <<- , optional quote, then the delimiter word.
HEREDOC = re.compile(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?")
marks = list(HEREDOC.finditer(cmd))

# S170 (ERR-053 / ERR-054's mechanical half, the same shape one layer over): a `python -c "…"` / `python.exe -c '…'` whose
# program text carries a backslash, a backtick or a `$` is the heredoc case without the heredoc — the S1xx rule said "NO
# Markdown or code text in a `python -c` or heredoc, ever — a FILE", and it lived in memory only. Same posture: warn, never
# block; additive to the heredoc rule, which is left exactly as Rab signed it.
DASH_C = re.compile(r"(?:^|[\s;&|(])(?:[\w./\\:-]*python[\w.]*|py)\s+(?:-[A-Za-z]+\s+)*-c\s+(['\"])(.*?)\1", re.S)
dash_c = [m.group(2) for m in DASH_C.finditer(cmd)]
DASH_RISK = re.compile(r"\\|`|\$")
dash_hits = sorted({h for prog in dash_c for h in DASH_RISK.findall(prog)})

# S213 (Rab, Desk 17258df3, 2026-09-25T17:06:42Z, after he was shown what he gains and loses: "as in I gain from you doing
# the block, if so, why not. Small incrementals changes that make your work quality increase"): a `python -c` whose program
# holds a BACKSLASH or a `$` is now REFUSED, not warned. The form is never necessary (a file does all it does), and the
# warning alone did not hold (19 warnings in S213, 7 of them this case; at least one read printed nothing and was taken for
# a result). Exactly the scope he was offered: a backtick alone still only warns, and the heredoc case (ERR-009) keeps
# warning exactly as he signed on 2026-08-27. Bash only, like the rest of this hook: a PowerShell call is not seen.
block_hits = sorted({h for prog in dash_c for h in re.findall(r"\\|\$", prog)})
if block_hits:
    reason = ("ERR-054 (QUOTING) BLOCKED: this Bash call puts a program with {s} inside a `python -c` string. Since "
              "2026-09-25 (Rab, Desk 17258df3) that form is refused, not warned: write the program to a FILE with the Write "
              "tool and run the file by its path.").format(s=", ".join(repr(h) for h in block_hits))
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}))
    sys.exit(0)

if not marks and not dash_hits:
    sys.exit(0)

# Risky content, drawn from the three ERR-009 instances rather than invented:
#   \\  \(  \|  \'  \"      escape sequences the shell or Python may eat
#   (?<! (?= (?:            regex constructs that carry backslashes
RISK = re.compile(r"\\[\\()|'\"nrt]|\(\?[<=:!]")
hits = RISK.findall(cmd) if marks else []
if not hits and not dash_hits:
    sys.exit(0)

if hits:
    delims = ", ".join(sorted({m.group(1) for m in marks}))
    sample = ", ".join(sorted(set(hits))[:6])
    msg = (
        "ERR-009 (QUOTING): this Bash call puts backslash escapes or regex inside a "
        "heredoc (<<{d}). Found: {s}. That exact combination has failed at least five "
        "times today, twice AFTER the rule was filed. ERR-009's own remedy: write it to "
        "a file with the Write tool and run the file. Not blocking - if you have already "
        "considered this, proceed."
    ).format(d=delims, s=sample)
else:
    msg = (
        "ERR-054 (QUOTING): this Bash call puts a program with {s} inside a `python -c` string. "
        "ERR-053/054's own rule: no path, Markdown or code text in a `python -c` — anything with a "
        "backslash, a backtick or a $ is a FILE written with the Write tool and run by its path. "
        "Not blocking - if you have already considered this, proceed."
    ).format(s=", ".join(repr(h) for h in dash_hits))

print(json.dumps({
    "systemMessage": msg,
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": msg,
    },
}))
