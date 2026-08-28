#!/usr/bin/env python
"""PreToolUse/Bash — C3's mechanical half, for ERROR-BIN ERR-009.

ERR-009's own remedy, in its words: "anything containing backslashes or nested
quotes goes in a FILE via Write, never a heredoc." That rule was filed at 02:40
and broken at least twice afterwards, in the same session, including inside the
run that documented it. A rule I have to remember is not a rule; this is the
half a machine can hold.

It WARNS. It never blocks — most heredocs are fine, and a gate that fires on
every one would be tuned away within a day (close.sh's own DEBT comment says so).

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
if not marks:
    sys.exit(0)

# Risky content, drawn from the three ERR-009 instances rather than invented:
#   \\  \(  \|  \'  \"      escape sequences the shell or Python may eat
#   (?<! (?= (?:            regex constructs that carry backslashes
RISK = re.compile(r"\\[\\()|'\"nrt]|\(\?[<=:!]")
hits = RISK.findall(cmd)
if not hits:
    sys.exit(0)

delims = ", ".join(sorted({m.group(1) for m in marks}))
sample = ", ".join(sorted(set(hits))[:6])

msg = (
    "ERR-009 (QUOTING): this Bash call puts backslash escapes or regex inside a "
    "heredoc (<<{d}). Found: {s}. That exact combination has failed at least five "
    "times today, twice AFTER the rule was filed. ERR-009's own remedy: write it to "
    "a file with the Write tool and run the file. Not blocking - if you have already "
    "considered this, proceed."
).format(d=delims, s=sample)

print(json.dumps({
    "systemMessage": msg,
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": msg,
    },
}))
