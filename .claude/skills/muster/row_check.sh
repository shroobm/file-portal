#!/usr/bin/env bash
# .claude/skills/muster/row_check.sh — J69 (S132): THE LEDGER ROW IS VALIDATED BY ITS READER BEFORE THE PUSH.
# ⟨claimed: Fable · Claude Opus 5 · S132 · 2026-09-12⟩
#
#   FP_REPO=<repo> [MUSTER_LANE=Desktop] bash .claude/skills/muster/row_check.sh <N>     # N = this session, e.g. 132
#
# Why it exists. close.sh runs BEFORE the row exists (the row names the closing SHA), so nothing on the close path ever
# parsed a row: S130's row had three cells with the SHA in prose, and the next open's [3b] read `no-sha`, selected the
# previous session and declared an INCIDENT (SYM-113, ERR-085). S131 then ran the parse by hand and gated on the CLOCKS —
# which cannot agree before the memory lockstep — so the right row was refused for the wrong reason. The check is the
# PARSE and the SHA, nothing else.
#
# One grammar, two doors: the awk below is muster.sh [3b]'s, copied verbatim at build time; selftest.sh case 51 asserts
# the two bodies are byte-identical, so a change to one without the other is a red, not a drift.
#
# Exit 0  the newest <lane> row is S<N>, no unparsed row sits in the last five, and its last cell is a 7–40-hex SHA that
#         is a commit in FP_REPO and an ancestor of HEAD.
# Exit 1  a MEASURED red — the row and the reason are named. The close chain stops on it (SKILL.md step 4b: a documented
#         step the closer runs, NOT a hook — wiring it into guard_git's push path is J71).
# Exit 2  usage / CONFIG — never a verdict about the row (a shallow clone cannot vouch for a SHA: CONFIG, not a typo).
set -u
FP_REPO="${FP_REPO:-$HOME/Projects/file-portal}"
README="$FP_REPO/CLAUDE_README.md"
LANE="${MUSTER_LANE:-Desktop}"
N="${1:-}"
if ! [[ "$N" =~ ^[0-9]+$ ]]; then echo "row_check: usage: row_check.sh <session-number>"; exit 2; fi
if [[ ! -f "$README" ]]; then echo "row_check: CONFIG — no ledger at $README"; exit 2; fi
if ! git -C "$FP_REPO" rev-parse --git-dir >/dev/null 2>&1; then echo "row_check: CONFIG — not a git repo: $FP_REPO"; exit 2; fi
if [[ "$(git -C "$FP_REPO" rev-parse --is-shallow-repository 2>/dev/null)" == "true" ]]; then
  echo "row_check: CONFIG — $FP_REPO is a shallow clone; a SHA outside its depth is not a verdict about the row"; exit 2
fi
N=$((10#$N))   # "0132" and "132" are the same session; the ledger never zero-pads, the caller might

# ── the parse: muster.sh [3b]'s awk, verbatim (see case 51) ──
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

rows_total=$(printf '%s\n' "$parsed" | awk '$1 == "rows" { print $2 }')
# 1. no unparsed row in the tail — the same window muster.sh [3b] alarms on
tail_skips=$(printf '%s\n' "$parsed" | awk -v tot="${rows_total:-0}" '$1 == "skip" && $2 > tot - 5 { print "row" $2 "(" $3 ")" }' | tr '\n' ' ')
if [[ -n "$tail_skips" ]]; then
  echo "row_check: ✗ UNPARSED ROW in the last 5: ${tail_skips}— the reader (muster.sh [3b]) will select an OLDER session; five cells, the SHA alone in the last cell"
  exit 1
fi
# 2. the newest <lane> row is S<N> — and there is exactly ONE row for that session (a duplicate is a red: the ledger
#    is one row per session; a corrected row replaces its predecessor in place, as S130's reshape did — it never sits
#    beside it, or the reader's tie-break decides by hex order which SHA "the close" was)
oks=$(printf '%s\n' "$parsed" | awk '$1 == "ok" { print $3, $4, $2 }')
if [[ -z "$oks" ]]; then echo "row_check: ✗ no parsed $LANE row at all in $README"; exit 1; fi
max_sess=$(printf '%s\n' "$oks" | sort -k1,1n | tail -n 1 | awk '{ print $1 }')
dupes=$(printf '%s\n' "$oks" | awk -v s="$max_sess" '$1 == s { print "row" $3 "(" $2 ")" }' | tr '\n' ' ')
if [[ "$(printf '%s\n' "$oks" | awk -v s="$max_sess" '$1 == s' | grep -c .)" -gt 1 ]]; then
  echo "row_check: ✗ TWO rows for S$max_sess: ${dupes}— one ledger row per session; the correction replaces its predecessor in place"
  exit 1
fi
newest=$(printf '%s\n' "$oks" | awk -v s="$max_sess" '$1 == s')
sess=$(printf '%s' "$newest" | awk '{ print $1 }'); sha=$(printf '%s' "$newest" | awk '{ print $2 }'); nr=$(printf '%s' "$newest" | awk '{ print $3 }')
if (( 10#$sess != N )); then
  echo "row_check: ✗ newest $LANE row is S$sess ($sha, row $nr) — expected S$N: the S$N row is absent or did not parse"
  exit 1
fi
# 3. the SHA is a commit in this repo and an ancestor of HEAD
if ! git -C "$FP_REPO" cat-file -e "${sha}^{commit}" 2>/dev/null; then
  echo "row_check: ✗ S$N row's SHA $sha is not a commit in $FP_REPO (a typo, or the closing commit was never made)"
  exit 1
fi
if ! git -C "$FP_REPO" merge-base --is-ancestor "$sha" HEAD 2>/dev/null; then
  echo "row_check: ✗ S$N row's SHA $sha is not an ancestor of HEAD (the row names a commit this branch does not contain)"
  exit 1
fi
echo "row_check: ✓ ROW OK — S$N $sha (row $nr of $rows_total; lane $LANE; a commit, an ancestor of HEAD)"
exit 0
