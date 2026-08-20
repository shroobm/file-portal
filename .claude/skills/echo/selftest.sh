#!/usr/bin/env bash
# .claude/skills/echo/selftest.sh — the echo skill's tripwire. A guard born today gets its
# tripwire today. Read-only against the real repo except one temp fixture for the fail-loud
# case. Exit 0 only on all-green; each case prints PASS/FAIL with the evidence.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
pass=0; total=0
check() { # name, condition-result (0 ok)
  total=$((total+1))
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); printf 'PASS %d — %s\n' "$total" "$1";
  else printf 'FAIL %d — %s\n' "$total" "$1"; fi
}

# 1 — sweep runs green on the real repo and prints every core label
out="$(bash "$HERE/sweep.sh" 2>&1)"; rc=$?
ok=1
if [ $rc -eq 0 ]; then
  ok=0
  for label in LEDGER LEVERS PIPELINE REGISTER SYM DOCS LEXICON; do
    printf '%s' "$out" | grep -q "$label" || ok=1
  done
fi
check "sweep.sh exit 0 on real repo + all core labels present" $ok

# 2 — term mode: a term row and at least one hit for a word that must exist
out="$(bash "$HERE/sweep.sh" muster 2>&1)"; rc=$?
printf '%s' "$out" | grep -q 'TERM muster' && printf '%s' "$out" | grep -Eq 'TERM muster +repo [1-9]'
check "term sweep emits 'TERM muster' with nonzero repo hits" $?

# 3 — fail-loud: an empty FP_REPO must exit nonzero and say UNREAD, never look clean
tmp="$(mktemp -d)"
out="$(FP_REPO="$tmp" bash "$HERE/sweep.sh" 2>&1)"; rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'UNREAD'
check "empty repo → nonzero exit + UNREAD rows (no silent clean)" $?
rmdir "$tmp" 2>/dev/null || true

# 4 — lexicon parses: >=10 data rows, every data row has >=4 cells
n="$(grep -cE '^\| [^|]' "$HERE/lexicon.md")"
bad="$(grep -E '^\| [^|]' "$HERE/lexicon.md" | awk -F'|' 'NF < 6 {c++} END {print c+0}')"
[ "$n" -ge 11 ] && [ "$bad" -eq 0 ]   # 11 = header + >=10 data rows; NF>=6 = 4 cells
check "lexicon: $((n-1)) data rows (>=10) and every row 4-celled" $?

# 5 — the stop rule survives edits to the judgment half
grep -q 'your word commits one reading' "$HERE/SKILL.md" && grep -q 'No work commits before alignment' "$HERE/SKILL.md"
check "SKILL.md still carries the stop rule + the no-work-before-alignment law" $?

printf '════ echo selftest: %d/%d ════\n' "$pass" "$total"
[ "$pass" -eq "$total" ]
