#!/usr/bin/env bash
# selftest.sh — the circle skill's tripwire (J37, S157 E14). The property: the three S108 rules are IN the skill and the
# retired verdict word is OUT of its vocabulary. Each case violates the property on a planted copy and watches the check
# fire; case 0 is the positive control (the real file passes), and a negative control plants "HELD" back as a verdict
# and asserts the check goes red. Exit 0 all fired · 1 any tripwire silent.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL="$HERE/SKILL.md"
pass=0; failed=0; skipped=0
# S194 E1: a case whose object is ABSENT on this platform reads SKIP — its own tally, never a pass and never a fail (the mirror
# case read UNREAD-and-failed on the CI runner, where no user-level ~/.claude exists). CIRCLE_MIRROR names the mirror for the
# controls: absent → SKIP; present and differing → still FAIL (a skip is for absence, not for difference).
skip() { printf '  SKIP %s — %s\n' "$1" "$2"; skipped=$((skipped+1)); }
ok()  { printf '  ok   %s\n' "$1"; pass=$((pass+1)); }
bad() { printf '  BAD  %s — %s\n' "$1" "$2"; failed=$((failed+1)); }

# the check itself — a function so the negative controls can run it on a planted copy
check_skill() {  # $1 = path; prints reasons, returns 1 on any
  local f="$1" rc=0
  grep -q 'Frozen-commit immutable audit records' "$f" || { echo "rule 1 (frozen-commit records) missing"; rc=1; }
  grep -q 'The aborted-lane law' "$f"                 || { echo "rule 2 (the aborted-lane law) missing"; rc=1; }
  grep -q '"HELD" is retired as a verdict word' "$f"  || { echo "rule 3 (HELD retired) missing"; rc=1; }
  # the verdict vocabulary: a bullet that BEGINS a verdict with HELD is the retired use; the rule's own sentence names the
  # word inside prose and is allowed
  if grep -qE '^- \*\*HELD\*\*' "$f"; then echo "HELD is still a verdict bullet"; rc=1; fi
  grep -qE '^- \*\*WITHSTOOD\*\*' "$f" || { echo "WITHSTOOD is not a verdict bullet"; rc=1; }
  grep -qE '^- \*\*BLOCKED\*\*' "$f"   || { echo "BLOCKED is not a verdict bullet"; rc=1; }
  return $rc
}

# CASE 0 — positive control: the tracked skill passes
if out=$(check_skill "$SKILL"); then ok "the tracked skill carries the three rules and no HELD verdict"; else bad "the tracked skill" "$out"; fi

# CASE 1 — the mirror: the user-level copy is byte-identical to the tracked one (UNREAD when absent, never a pass)
MIRROR="${CIRCLE_MIRROR:-$HOME/.claude/skills/circle/SKILL.md}"
if [[ -f "$MIRROR" ]]; then
  # compared with CR stripped: the tracked copy may be checked out CRLF while the mirror stays LF (the text is the contract)
  if cmp -s <(tr -d "\r" < "$SKILL") <(tr -d "\r" < "$MIRROR"); then ok "the user-level mirror is identical to the tracked skill (CR-stripped)"; else bad "the mirror" "differs from the tracked copy — re-copy it"; fi
else
  skip "the user-level mirror" "absent at $MIRROR — no mirror to compare on this platform (not a pass, not a fail)"
fi

# CASE 2 — NEGATIVE CONTROL: plant HELD back as a verdict bullet on a copy; the check must go red for that reason
W="$(mktemp -d)"; trap 'rm -rf "$W"' EXIT
sed 's/^- \*\*WITHSTOOD\*\*/- **HELD**/' "$SKILL" > "$W/planted.md"
if out=$(check_skill "$W/planted.md"); then bad "negative control (HELD planted)" "the check stayed green"; else
  if printf '%s' "$out" | grep -q 'HELD is still a verdict bullet'; then ok "negative control: HELD planted as a verdict bullet reds the check"; else bad "negative control" "red for the wrong reason: $out"; fi
fi

# CASE 3 — NEGATIVE CONTROL: a copy without the aborted-lane law reds for that reason
grep -v 'The aborted-lane law' "$SKILL" > "$W/norule.md"
if out=$(check_skill "$W/norule.md"); then bad "negative control (rule 2 removed)" "the check stayed green"; else
  if printf '%s' "$out" | grep -q 'rule 2'; then ok "negative control: the aborted-lane law removed reds the check"; else bad "negative control" "red for the wrong reason: $out"; fi
fi

printf '\n'
if [[ "$failed" -eq 0 ]]; then printf 'ALL TRIPWIRES FIRED — %s/%s · fired %s / skipped %s / silent 0\n' "$pass" "$((pass+failed))" "$pass" "$skipped"; exit 0
else printf 'TRIPWIRES DISARMED — %s failed of %s · fired %s / skipped %s / silent %s\n' "$failed" "$((pass+failed))" "$pass" "$skipped" "$failed"; exit 1; fi
