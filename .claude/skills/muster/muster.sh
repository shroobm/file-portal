#!/usr/bin/env bash
# ~/.claude/muster.sh — the Session Muster, executable form.
# Verifies memory is loaded and the two timekeeping clocks reconcile.
#   exit 0 = CLEAN ; exit 1 = INCIDENT (a SessionStart hook can gate on this).
# Paths use forward slashes (safe in Git Bash / MinTTY / WSL). Override via env:
#   MEMORY_LIB=/path/to/memory  FP_REPO=/path/to/file-portal
set -uo pipefail

MEMORY_LIB="${MEMORY_LIB:-$HOME/.claude/projects/C--Users-Bndit-Documents-Claude-Code-Memory-Backup/memory}"
FP_REPO="${FP_REPO:-$HOME/Projects/file-portal}"
MEM="$MEMORY_LIB/MEMORY.md"
TALLY="$MEMORY_LIB/cookie-tally.md"
README="$FP_REPO/CLAUDE_README.md"

fail=0
hex='[0-9a-f]{7,40}'

printf '──────── MUSTER · %s ────────\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# [1] memory loaded?
if [[ -f "$MEM" ]]; then
  printf '[1] MEMORY ....... ✓ %s\n' "$MEM"
else
  printf '[1] MEMORY ....... ✗ BLIND — index not found at %s\n' "$MEM"; fail=1
fi

# THE TIME-STATE ANCHOR — read once, used by BOTH clocks below.
#
# S78: every value muster reads out of MEMORY.md is now bound to the TIME-STATE line, never to
# "the first match anywhere in the file". The soft clock used to be
#   grep 'received N / given M' MEMORY.md | head -1
# and MEMORY.md holds TWO matches: the live TIME-STATE header, and a stale one-line description
# of cookie-tally.md ~130 lines further down that still says `received 55 / given 3`. It read the
# right one only because the header happens to sit above the index — a memory-consolidation pass
# that reorders the file would have made muster cry cookie-ledger incident over a line that is not
# a clock at all. Same positional fault the ledger's old `tail -1` had (see [3]), same cure.
#
# The window is deliberately SMALL — the anchor plus a few continuation lines, not "to end of
# file". A TIME-STATE that LOSES its cookie count must read EMPTY and fail loudly, not silently
# reach past the entry and pick up the stale description below. The entry is 3 lines today;
# 6 leaves slack for a longer close without ever reaching the index.
TS_WINDOW=6
#
# S78: the window arms ONCE. It used to re-arm on EVERY line matching the token, so a second
# mention anywhere in the file appended a second block — and the very edit that removed the
# stale `received 55` from the index put the word TIME-STATE there instead, re-planting the
# fault it was written to cure. A fixture then showed [2] printing a green `✓ 71` read off an
# index bullet while the real TIME-STATE entry carried no count at all: the anchored check
# passing over an unanchored clock, which is the whole defect twice over. `armed` makes the
# first match the only match, so a mention below can never stand in for the entry above.
#
# S79: the window is bound to the entry's STRUCTURE, not to a line distance. `n <= w` alone is a
# distance proxy for "still inside the TIME-STATE entry", and the proxy is held in place by an
# editorial convention rather than by anything mechanical: it works today only because MEMORY.md's
# index line was deliberately scrubbed of both a count and the token, and because the entry
# happens to run longer than six lines. A consolidation pass, or simply a SHORT close — which is
# exactly the "TIME-STATE that loses its cookie count" case this comment says must fail loudly —
# lets the window reach past the entry and read a number that is not a clock. Proven by fixture
# (selftest.sh case 3): a 1-line entry plus an index bullet four lines below produced `hook=99`
# read off the bullet. The entry is a blockquote; every continuation line begins `>`; the index
# bullets do not. So the block ends where the blockquote ends, and `w` stays only as a cap.
ts_block=$(awk -v w="$TS_WINDOW" '
  !armed && /TIME-STATE/ { armed = 1; n = 1; print; next }
  armed && ended { next }
  armed && /^[[:space:]]*>/ && n < w { print; n++; next }
  armed { ended = 1 }' "$MEM" 2>/dev/null)

# [2] SOFT clock — tally header must match the MEMORY.md hook / TIME-STATE
soft_hdr=$(grep -oE 'Received from user: [0-9]+' "$TALLY" 2>/dev/null | grep -oE '[0-9]+')
soft_hook=$(printf '%s\n' "$ts_block" | grep -oE 'received [0-9]+ / given [0-9]+' | head -1 | grep -oE '[0-9]+' | head -1)
if [[ -z "$ts_block" ]]; then
  printf '[2] SOFT clock ... ✗ no TIME-STATE line in %s — the soft clock has no anchor\n' "$MEM"; fail=1
elif [[ -n "$soft_hdr" && "$soft_hdr" == "$soft_hook" ]]; then
  printf '[2] SOFT clock ... ✓ %s (tally == hook)\n' "$soft_hdr"
else
  printf '[2] SOFT clock ... ✗ DRIFT tally=%s hook=%s (hook read within %s lines of TIME-STATE)\n' \
    "$soft_hdr" "$soft_hook" "$TS_WINDOW"; fail=1
fi

# [3] HARD clock — expected session+SHA read dynamically from TIME-STATE (NOT hardcoded),
#     cross-checked against the newest ledger row and HEAD.
#
# S78: the newest row is chosen by MAX SESSION NUMBER, never by position. The old `tail -1`
# assumed the ledger is append-ordered; S75 prepended above S74 and S76/S77 copied it, so for
# three sessions `tail -1` returned S74's row and the check reported a phantom SHA mismatch —
# an ordering fault wearing a rewind's clothing. Position is now derived, and its violation is
# reported as its own distinct fault so the two can never again be confused.
exp_sha=$(printf '%s\n' "$ts_block" | grep -oiE "$hex" | head -1)
exp_sess=$(printf '%s\n' "$ts_block" | grep -oE 'S[0-9]+' | head -1)

# One pass over every ledger row -> "<seq> <session-number> <sha>" in FILE ORDER.
# Session = first cell matching ^S<n>: ; SHA = last non-empty cell (robust to `|` in prose).
#
# S78: rows that do NOT parse are no longer dropped in silence — every row is emitted with a
# verdict (ok / skip + why) and the discards are counted in [3b]. They used to vanish with no
# count and no warning: 21 of 83 rows here are historical (pre-S16, before the `S<n>:` convention)
# and legitimately unparseable, but the SAME silence would swallow a NEW row whose closer forgot
# the `S<n>:` prefix or the SHA cell. Muster would then select the PREVIOUS row and report a
# phantom SHA mismatch — a bad close wearing a rewind's clothing, i.e. the exact misdiagnosis the
# [3a] guard was built to prevent, arriving by another door.
#
# S86: the ledger is MULTI-LANE. The machine column (cell 2) names whose clock a row belongs to.
# At the 2026-08-16 fork merge, ThinkPad rows S78/S79 joined a table whose Desktop lane stood at
# S85 — same numbers, different lanes, both legitimate (each side derived its next number from
# the newest record it could see; the Desktop's 52-commit unpushed backlog made theirs stale).
# A row from another machine parses fine but must never enter THIS clock: selection is by max
# session number, so the moment another lane's number passed ours, muster would adopt their row
# and report a phantom mismatch — a lane fault wearing a rewind's clothing, the same family as
# SYM-028. Lane rows get their own verdict (never "skip"): they are counted and NAMED in [3b],
# so a Desktop row that mistypes its machine cell shows up as a named lane discard, not silence,
# and they are exempt from the [3b] tail alarm, because a foreign row near the tail is the
# EXPECTED shape after a merge, not a malformed close.
LANE="${MUSTER_LANE:-Desktop}"
parsed=$(grep -E '^\| 20[0-9][0-9]-' "$README" 2>/dev/null | awk -F'|' -v lane="$LANE" '
  {
    for (i = 1; i <= NF; i++) gsub(/^[ \t\r]+|[ \t\r]+$/, "", $i)
    sess = ""; sha = ""
    for (i = 1; i <= NF; i++) if ($i ~ /^S[0-9]+:/) { sess = substr($i, 2, index($i, ":") - 2); break }
    for (i = NF; i >= 1; i--) if ($i != "") { sha = $i; break }
    if (sess != "" && sha ~ /^[0-9a-fA-F]{7,40}$/) {
      if ($3 != lane) { print "lane", NR, $3 "-S" sess; next }
      print "ok", NR, sess, sha; next
    }
    why = (sess == "" ? "no-S<n>" : "")
    if (sha !~ /^[0-9a-fA-F]{7,40}$/) why = (why == "" ? "no-sha" : why "+no-sha")
    print "skip", NR, why
  }
  END { print "rows", NR }')

ledger=$(printf '%s\n' "$parsed" | awk '$1 == "ok"   { print $2, $3, $4 }')
skipped=$(printf '%s\n' "$parsed" | awk '$1 == "skip" { print $2, $3 }')
lanes=$(printf '%s\n' "$parsed" | awk '$1 == "lane" { print $3 }')
rows_total=$(printf '%s\n' "$parsed" | awk '$1 == "rows" { print $2 }')
rows_ok=$(printf '%s\n' "$ledger"  | grep -c .)
rows_skip=$(printf '%s\n' "$skipped" | grep -c .)
rows_lane=$(printf '%s\n' "$lanes" | grep -c .)
lane_note=""
[[ "$rows_lane" -gt 0 ]] && lane_note=$(printf ' · %s other-lane: %s' "$rows_lane" "$(printf '%s' "$lanes" | tr '\n' ' ' | sed 's/ $//')")

led_sess=$(printf '%s\n' "$ledger" | sort -k2,2n | tail -1 | awk '{print "S" $2}')
led_sha=$(printf '%s\n' "$ledger" | sort -k2,2n | tail -1 | awk '{print $3}')

# [3a] LEDGER ORDER — session numbers must ascend in file order. A violation is not a rewind.
#
# S78: this check now prints when it PASSES. It used to print only on failure, so a clean run and
# a run where the ledger parsed to ZERO rows — no order to check, nothing guarded — looked
# identical from the outside. A guard born of an observability failure was itself unobservable.
order_bad=$(printf '%s\n' "$ledger" | awk '{ if (NR > 1 && $2 <= prev) print prev "->" $2 ; prev = $2 }')
if [[ -n "$order_bad" ]]; then
  printf '[3a] LEDGER ORDER  ✗ rows out of sequence: %s — append below, never prepend\n' \
    "$(printf '%s' "$order_bad" | tr '\n' ' ')"; fail=1
elif [[ "$rows_ok" -eq 0 ]]; then
  printf '[3a] LEDGER ORDER  ✗ 0 parseable rows — no order was checked (ledger missing or unreadable?)\n'; fail=1
else
  printf '[3a] LEDGER ORDER  ✓ %s %s-lane rows ascend (S%s → S%s)\n' \
    "$rows_ok" "$LANE" "$(printf '%s\n' "$ledger" | head -1 | awk '{print $2}')" \
    "$(printf '%s\n' "$ledger" | tail -1 | awk '{print $2}')"
fi

# [3b] LEDGER PARSE — discarded rows are COUNTED, and a discard near the TAIL is its own loud fault.
#
# The tail is the last TAIL_ROWS table rows. Justification: the ledger is append-below (that is
# what [3a] enforces), so the only rows a live close can malform are the newest ones — and a
# malformed newest row is precisely what silently demotes the selection to the previous session.
# 5 covers a bad close plus the rows around it while staying far clear of the historical head
# (rows 1-21 of 83 in this repo), which must never trip this alarm.
TAIL_ROWS=5
tail_bad=$(printf '%s\n' "$skipped" | awk -v t="$rows_total" -v w="$TAIL_ROWS" 'NF && $1 > t - w { printf "row%s(%s) ", $1, $2 }')
if [[ -n "$tail_bad" ]]; then
  printf '[3b] LEDGER PARSE  ✗ UNPARSEABLE ROW IN THE LAST %s: %s— a NEW row failed to parse; the\n' "$TAIL_ROWS" "$tail_bad"
  printf '                     selected session %s is the row BEFORE it, not the newest. Fix the row.\n' "$led_sess"; fail=1
elif [[ "$rows_skip" -eq 0 ]]; then
  printf '[3b] LEDGER PARSE  ✓ %s/%s rows parsed · 0 discarded%s\n' "$rows_ok" "$rows_total" "$lane_note"
else
  # Name the NEWEST discard, not just the count: that is the one that would move if the rot
  # ever crept toward the tail, and a count alone cannot show it moving.
  printf '[3b] LEDGER PARSE  ✓ %s/%s rows parsed · %s discarded, newest at row %s · tail = last %s%s\n' \
    "$rows_ok" "$rows_total" "$rows_skip" "$(printf '%s\n' "$skipped" | tail -1 | awk '{print $1}')" "$TAIL_ROWS" "$lane_note"
fi

# S78: a missing or non-git FP_REPO used to fall through `merge-base --is-ancestor ... 2>/dev/null`
# into the else branch and be announced as "not an ancestor of HEAD (rewind/fork?)" — a
# CONFIGURATION fault wearing a rewind's clothing, the third instance of that pattern in this file.
# Resolve the repo BEFORE asking git anything about ancestry.
repo_git=0
git -C "$FP_REPO" rev-parse --git-dir >/dev/null 2>&1 && repo_git=1

if [[ ! -d "$FP_REPO" ]]; then
  printf '[3] HARD clock ... ✗ CONFIG — FP_REPO does not exist: %s (NOT a rewind)\n' "$FP_REPO"; fail=1
elif [[ "$repo_git" -eq 0 ]]; then
  printf '[3] HARD clock ... ✗ CONFIG — not a git repo: %s (NOT a rewind)\n' "$FP_REPO"; fail=1
elif [[ -z "$exp_sha" || -z "$led_sha" ]]; then
  printf '[3] HARD clock ... ✗ could not read a SHA (TIME-STATE=%s ledger=%s)\n' "$exp_sha" "$led_sha"; fail=1
elif [[ "$exp_sha" != "$led_sha"* && "$led_sha" != "$exp_sha"* ]]; then
  printf '[3] HARD clock ... ✗ SHA mismatch: TIME-STATE %s vs ledger %s\n' "$exp_sha" "$led_sha"; fail=1
elif [[ -n "$exp_sess" && "$exp_sess" != "$led_sess" ]]; then
  printf '[3] HARD clock ... ✗ session mismatch: TIME-STATE %s vs ledger %s\n' "$exp_sess" "$led_sess"; fail=1
elif ! git -C "$FP_REPO" cat-file -e "$exp_sha^{commit}" 2>/dev/null; then
  printf '[3] HARD clock ... ✗ CONFIG — %s is not a commit in %s (wrong clone / unfetched — NOT a rewind)\n' \
    "$exp_sha" "$FP_REPO"; fail=1
elif git -C "$FP_REPO" merge-base --is-ancestor "$exp_sha" HEAD 2>/dev/null; then
  printf '[3] HARD clock ... ✓ %s (%s) mirrors ledger, ancestor of HEAD\n' "$exp_sha" "$exp_sess"
else
  printf '[3] HARD clock ... ✗ %s not an ancestor of HEAD (rewind/fork?)\n' "$exp_sha"; fail=1
fi

# working tree context
if [[ "$repo_git" -eq 1 ]]; then
  dirty=$(git -C "$FP_REPO" status --porcelain 2>/dev/null | grep -c .)
  branch=$(git -C "$FP_REPO" rev-parse --abbrev-ref HEAD 2>/dev/null)
  printf '    WORKING TREE . %s uncommitted · %s\n' "$dirty" "$branch"
else
  printf '    WORKING TREE . n/a — %s is not a git working tree\n' "$FP_REPO"
fi

if [[ "$fail" -eq 0 ]]; then
  printf 'VERDICT .......... ✓ CLEAN — clocks reconcile\n'
else
  printf 'VERDICT .......... ✗ INCIDENT — reconcile before work\n'
fi
exit "$fail"
