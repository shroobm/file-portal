#!/usr/bin/env bash
# coordination/selftest.sh — the tripwire for the relay protocol + the claim convention.
# ⟨claimed: Fable · S100 · 2026-08-20⟩
#
# Proves the protocol's rules are MECHANICALLY checkable, not just prose: entry shape, UTC
# stamps, the three required parts, the concordance amendment's presence, the carry-selection
# rule (newest addressed to me; never re-carry what my lane already answered), and the ledger
# row format whose violation this project already caught once (S99 §10a).
#
# Read-only against the real repo; fixtures live in a temp dir and are removed.
# CRLF: repo markdown is CRLF (SYM-029) — every read normalizes with `tr -d '\r'` before
# matching, and case 9 proves the parser survives a CRLF fixture.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
RELAY="$HERE/relay.md"
AUTHORSHIP="$HERE/authorship.md"
README="$REPO/CLAUDE_README.md"

pass=0; total=0
check() { total=$((total+1)); if [ "$2" -eq 0 ]; then pass=$((pass+1)); printf 'PASS %d — %s\n' "$total" "$1"; else printf 'FAIL %d — %s\n' "$total" "$1"; fi; }
norm() { tr -d '\r' < "$1"; }

# ── the parser under test ───────────────────────────────────────────────────
# An entry header: ## <YYYY-MM-DDTHH:MMZ> · ⟨from: X⟩ → ⟨to: Y⟩
HDR='^## 2[0-9]{3}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}Z · ⟨from: (Fable|Codex)⟩ → ⟨to: (Fable|Codex)⟩$'
headers() { norm "$1" | grep -E '^## 2[0-9]{3}-' || true; }
# newest entry addressed to $2 (ISO UTC sorts lexically — that is why UTC is the rule)
newest_for() { headers "$1" | grep -E "⟨to: $2⟩" | tail -1; }
# entries addressed to me that are NEWER than my own last written entry (= not yet answered)
unread_for() {
  local f="$1" me="$2" mine
  mine="$(headers "$f" | grep -E "⟨from: $me⟩" | tail -1 | grep -oE '^## [^ ]+' | cut -d' ' -f2)"
  headers "$f" | grep -E "⟨to: $me⟩" | while read -r h; do
    ts="$(printf '%s' "$h" | grep -oE '^## [^ ]+' | cut -d' ' -f2)"
    if [ -z "$mine" ] || [ "$ts" \> "$mine" ]; then printf '%s\n' "$h"; fi
  done
}
# an entry is well-formed if header matches AND its body carries all three parts
validate() { # file
  local f="$1" bad=0 n
  n="$(headers "$f" | grep -cE "$HDR" || true)"
  [ "$n" -eq "$(headers "$f" | grep -c . || true)" ] || bad=1        # every header well-formed
  for part in 'RECAP' 'FOR RAB' 'SUGGESTED PROMPT'; do
    [ "$(norm "$f" | grep -c "\*\*$part" || true)" -ge "$n" ] || bad=1  # >= one per entry
  done
  return $bad
}

# ── 1–3: the real relay file ────────────────────────────────────────────────
n_entries="$(headers "$RELAY" | grep -c . || true)"
[ "$n_entries" -ge 1 ]
check "real relay.md holds $n_entries entr(y|ies)" $?

validate "$RELAY"
check "real relay.md: every header UTC+from+to well-formed; every entry has RECAP / FOR RAB / SUGGESTED PROMPT" $?

amend=0
for rule in 'Must-quote' 'concordance label' 'must name the probe' 'Never impersonate'; do
  norm "$RELAY" | grep -qi -- "$rule" || amend=1
done
check "concordance amendment present: must-quote · label · probe-naming · no-impersonation" $amend

# ── 4: the claim convention names its parser-safe ledger format (S99 §10a) ──
norm "$AUTHORSHIP" | grep -q 'stamp goes AFTER the colon'
check "authorship.md still prescribes the parser-safe ledger row (stamp after S<n>:)" $?

# ── 5: every SESSION-NAMING ledger row parses with muster's S<n>: key ───────
# Not every row: rows 1–21 predate session numbering (task ids L1–L4, W5, W6, July 2026) and
# name no session at all — muster reports them as "21 discarded", correctly. The regression
# this guards is S99 §10a: a row that HAS a session number but not in parseable position.
# (First draft of this case asserted the universal property and went red on those 21 — the
# test's own bug, caught by running it. Recorded rather than quietly rewritten.)
rowsf="$(norm "$README" | grep -E '^\| 20[0-9]{2}-[0-9]{2}-[0-9]{2} \|')"
named="$(printf '%s\n' "$rowsf" | grep -cE '\bS[0-9]+\b' || true)"
keyed="$(printf '%s\n' "$rowsf" | grep -E '\bS[0-9]+\b' | grep -cE '\| S[0-9]+:' || true)"
[ "$named" -eq "$keyed" ] && [ "$named" -gt 0 ]
check "all $named session-naming ledger rows carry the parseable S<n>: key — the S99 regression guard" $?

# ── 6: that guard actually BITES — the S99-shaped row must be flagged ───────
badrow='| 2026-08-20 | Desktop | S99 (Fable): the stamp before the colon |'
printf '%s\n' "$badrow" | grep -qE '\bS[0-9]+\b' && ! printf '%s\n' "$badrow" | grep -qE '\| S[0-9]+:'
check "the guard bites: an S99-shaped row (stamp before the colon) is flagged as unparseable" $?

# ── 7: muster's ledger census is COMPLETE — every row accounted, none silent ─
census="$(grep -E '^\| 20[0-9][0-9]-' "$README" | awk -F'|' '
  { for (i=1;i<=NF;i++) gsub(/^[ \t\r]+|[ \t\r]+$/,"",$i)
    s=""; for (i=1;i<=NF;i++) if ($i ~ /^S[0-9]+:/) { s=1; break }
    if (s=="") skip++; else if ($3!="Desktop") lane++; else ok++ }
  END { print ok+0, lane+0, skip+0, NR }')"
set -- $census
[ $(( $1 + $2 + $3 )) -eq "$4" ] && [ "$4" -gt 0 ]
check "muster census complete: ok $1 + lane $2 + discarded $3 == $4 rows (no row silently unaccounted)" $?

# ── fixtures ────────────────────────────────────────────────────────────────
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
cat > "$TMP/good.md" <<'EOF'
## 2026-08-20T10:00Z · ⟨from: Fable⟩ → ⟨to: Codex⟩
**RECAP.** a
**FOR RAB.** b
**SUGGESTED PROMPT** c
## 2026-08-20T11:00Z · ⟨from: Codex⟩ → ⟨to: Fable⟩
**RECAP.** a
**FOR RAB.** b
**SUGGESTED PROMPT** c
## 2026-08-20T12:00Z · ⟨from: Fable⟩ → ⟨to: Codex⟩
**RECAP.** a
**FOR RAB.** b
**SUGGESTED PROMPT** c
## 2026-08-20T13:00Z · ⟨from: Codex⟩ → ⟨to: Fable⟩
**RECAP.** a
**FOR RAB.** b
**SUGGESTED PROMPT** c
EOF

# ── 6: carry-selection picks the NEWEST entry addressed to me ───────────────
newest_for "$TMP/good.md" Fable | grep -q '13:00Z'
check "carry-selection: newest entry addressed to Fable is 13:00Z (not 11:00Z)" $?

# ── 7: never re-carry what my lane already answered ─────────────────────────
# Fable's own last entry is 12:00Z → 11:00Z is answered, 13:00Z is not.
u="$(unread_for "$TMP/good.md" Fable)"
printf '%s' "$u" | grep -q '13:00Z' && ! printf '%s' "$u" | grep -q '11:00Z'
check "carry-selection: 11:00Z (older than my own 12:00Z entry) is NOT re-carried; 13:00Z is" $?

# ── 8: fail-loud on a local-time header and on a missing FOR RAB ────────────
sed 's/2026-08-20T13:00Z/2026-08-20 9:00pm EDT/' "$TMP/good.md" > "$TMP/bad-ts.md"
validate "$TMP/bad-ts.md"; ts_rc=$?
grep -v 'FOR RAB' "$TMP/good.md" > "$TMP/bad-part.md"
validate "$TMP/bad-part.md"; part_rc=$?
[ "$ts_rc" -ne 0 ] && [ "$part_rc" -ne 0 ]
check "fail-loud: non-UTC header rejected AND missing FOR RAB rejected" $?

# ── 9: the parser survives CRLF (SYM-029) ───────────────────────────────────
sed 's/$/\r/' "$TMP/good.md" > "$TMP/crlf.md"
validate "$TMP/crlf.md" && newest_for "$TMP/crlf.md" Fable | grep -q '13:00Z'
check "CRLF fixture parses identically (SYM-029 hazard covered)" $?

printf '════ coordination selftest: %d/%d ════\n' "$pass" "$total"
[ "$pass" -eq "$total" ]
