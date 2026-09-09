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
#
# S120 fixes (B1, B2, B3's history clause — sessions/S120-desktop-2026-09-09.md §6):
#   B1 — the concordance-amendment check used `grep -q` in a pipeline under `set -o pipefail`;
#        on a long stream, `grep -q` closes its stdin the instant it finds a match, `tr` (still
#        writing) gets SIGPIPE, and the pipeline reports 141 — a PRESENT string then reads
#        ABSENT. Fixed by switching to count form (`grep -c`, which reads to EOF and never
#        closes early), never `-q` inside a pipefail pipeline.
#   B2 — the header regex predated the gate's `· ⟨msg: MSG-(FAB|CDX)-NNNN⟩` suffix. Fixed by
#        making the suffix optional, and by grandfathering the six 2026-08-24 headers that read
#        "⟨to: Fable, and the record⟩" (pre-gate shape) by their exact UTC stamp, not by shape —
#        a legacy-shaped header at any OTHER stamp still fails. The grandfathered count is
#        printed as a number, never a checkmark; a real failure names the first offending header.
#   B3 — relay.md is append-only, so "every entry ever written has all three envelope slots"
#        can never go green (most of history predates the slots being mandatory). Fixed with
#        ENVELOPE_CUTOFF: entries stamped at/after it MUST carry RECAP/FOR RAB/SUGGESTED PROMPT
#        (fails loud, names the first offender); entries before it are only counted, printed as
#        "legacy entries before cutoff lacking a slot: N/M".
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
# An entry header: ## <YYYY-MM-DDTHH:MMZ> · ⟨from: X⟩ → ⟨to: Y⟩, optionally · ⟨msg: MSG-FAB|CDX-NNNN⟩
HDR='^## 2[0-9]{3}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}Z · ⟨from: (Fable|Codex)⟩ → ⟨to: (Fable|Codex)⟩( · ⟨msg: MSG-(FAB|CDX)-[0-9]{4}⟩)?$'
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

# B2: the six pre-gate 2026-08-24 headers that read "⟨to: X, and the record⟩" — grandfathered
# by their exact UTC stamp only. A legacy-shaped header at any other stamp still fails.
GRAND_TS='2026-08-24T02:49Z 2026-08-24T06:21Z 2026-08-24T06:23Z 2026-08-24T06:39Z 2026-08-24T06:40Z 2026-08-24T06:41Z'
is_grandfathered() { local ts="$1" g; for g in $GRAND_TS; do [ "$ts" = "$g" ] && return 0; done; return 1; }

# header-only validity (B2): every header either matches HDR or is grandfathered by stamp.
# Sets VALIDATE_GRAND (count grandfathered) and VALIDATE_OFFENDING (first real offender).
VALIDATE_GRAND=0
VALIDATE_OFFENDING=""
validate_header() { # file
  local f="$1" bad=0 grand=0 offending="" h ts
  while IFS= read -r h; do
    [ -z "$h" ] && continue
    if printf '%s\n' "$h" | grep -qE "$HDR"; then continue; fi
    ts="$(printf '%s\n' "$h" | grep -oE '^## [^ ]+' | cut -d' ' -f2)"
    if is_grandfathered "$ts"; then
      grand=$((grand+1))
    else
      bad=1
      [ -z "$offending" ] && offending="$h"
    fi
  done < <(headers "$f")
  VALIDATE_GRAND=$grand
  VALIDATE_OFFENDING="$offending"
  return $bad
}

# an entry is well-formed if header matches (via validate_header) AND its body carries all
# three parts at least once per entry — a generic small-fixture check, NOT cutoff-aware (that
# is b3_check below); used only against complete synthetic fixtures, never the real history.
validate() { # file
  local f="$1" bad=0 n
  n="$(headers "$f" | grep -c . || true)"
  validate_header "$f" || bad=1
  for part in 'RECAP' 'FOR RAB' 'SUGGESTED PROMPT'; do
    [ "$(norm "$f" | grep -c "\*\*$part" || true)" -ge "$n" ] || bad=1  # >= one per entry
  done
  return $bad
}

# B3: per-entry slot census — timestamp + which of the three slots that entry's body carries.
entry_slot_census() { # file -> lines "<ts> <recap 0|1> <forrab 0|1> <prompt 0|1>"
  norm "$1" | awk '
    /^## 2[0-9][0-9][0-9]-/ {
      if (ts != "") print ts, recap, forrab, prompt
      ts = $2; recap = 0; forrab = 0; prompt = 0
      next
    }
    ts != "" && /\*\*RECAP/ { recap = 1 }
    ts != "" && /\*\*FOR RAB/ { forrab = 1 }
    ts != "" && /\*\*SUGGESTED PROMPT/ { prompt = 1 }
    END { if (ts != "") print ts, recap, forrab, prompt }
  '
}

# the moment gate.py post began refusing bodies without the envelope, S120 (the coordinator may
# move this forward as the enforcement point is revisited).
ENVELOPE_CUTOFF='2026-09-09T20:00Z'

B3_OFFENDER=""
B3_LEGACY_MISSING=0
B3_LEGACY_TOTAL=0
b3_check() { # file — entries at/after cutoff MUST have all 3 slots; before cutoff, only counted
  local f="$1" bad=0 offender="" legacy_total=0 legacy_missing=0 ts recap forrab prompt
  while read -r ts recap forrab prompt; do
    [ -z "$ts" ] && continue
    if [ "$ts" \> "$ENVELOPE_CUTOFF" ] || [ "$ts" = "$ENVELOPE_CUTOFF" ]; then
      if [ "$recap" -eq 0 ] || [ "$forrab" -eq 0 ] || [ "$prompt" -eq 0 ]; then
        bad=1
        [ -z "$offender" ] && offender="$ts"
      fi
    else
      legacy_total=$((legacy_total+1))
      if [ "$recap" -eq 0 ] || [ "$forrab" -eq 0 ] || [ "$prompt" -eq 0 ]; then
        legacy_missing=$((legacy_missing+1))
      fi
    fi
  done < <(entry_slot_census "$f")
  B3_OFFENDER="$offender"
  B3_LEGACY_MISSING=$legacy_missing
  B3_LEGACY_TOTAL=$legacy_total
  return $bad
}

# ── 1–3: the real relay file ────────────────────────────────────────────────
n_entries="$(headers "$RELAY" | grep -c . || true)"
[ "$n_entries" -ge 1 ]
check "real relay.md holds $n_entries entr(y|ies)" $?

validate_header "$RELAY"; hdr_rc=$?
check "real relay.md: every header UTC+from+to (+optional ⟨msg:⟩) well-formed" $hdr_rc
printf 'grandfathered legacy headers (2026-08-24, "and the record"): %d\n' "$VALIDATE_GRAND"
if [ "$hdr_rc" -ne 0 ] && [ -n "$VALIDATE_OFFENDING" ]; then
  printf 'first offending header: %s\n' "$VALIDATE_OFFENDING"
fi

b3_check "$RELAY"; b3_rc=$?
check "real relay.md: entries at/after $ENVELOPE_CUTOFF carry RECAP / FOR RAB / SUGGESTED PROMPT" $b3_rc
printf 'legacy entries before cutoff lacking a slot: %d/%d\n' "$B3_LEGACY_MISSING" "$B3_LEGACY_TOTAL"
if [ "$b3_rc" -ne 0 ] && [ -n "$B3_OFFENDER" ]; then
  printf 'first offending post-cutoff entry: %s\n' "$B3_OFFENDER"
fi

# B1: count form only — `grep -c` reads to EOF and cannot SIGPIPE `tr` under pipefail (never
# `grep -q` inside a pipefail pipeline; see the fixture checks below for the negative control).
amend=0
for rule in 'Must-quote' 'concordance label' 'must name the probe' 'Never impersonate'; do
  cnt="$(norm "$RELAY" | grep -ci -- "$rule")"
  [ "${cnt:-0}" -ge 1 ] || amend=1
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

# ── carry-selection picks the NEWEST entry addressed to me ──────────────────
newest_for "$TMP/good.md" Fable | grep -q '13:00Z'
check "carry-selection: newest entry addressed to Fable is 13:00Z (not 11:00Z)" $?

# ── never re-carry what my lane already answered ────────────────────────────
# Fable's own last entry is 12:00Z → 11:00Z is answered, 13:00Z is not.
u="$(unread_for "$TMP/good.md" Fable)"
printf '%s' "$u" | grep -q '13:00Z' && ! printf '%s' "$u" | grep -q '11:00Z'
check "carry-selection: 11:00Z (older than my own 12:00Z entry) is NOT re-carried; 13:00Z is" $?

# ── fail-loud on a local-time header and on a missing FOR RAB ───────────────
sed 's/2026-08-20T13:00Z/2026-08-20 9:00pm EDT/' "$TMP/good.md" > "$TMP/bad-ts.md"
validate "$TMP/bad-ts.md"; ts_rc=$?
grep -v 'FOR RAB' "$TMP/good.md" > "$TMP/bad-part.md"
validate "$TMP/bad-part.md"; part_rc=$?
[ "$ts_rc" -ne 0 ] && [ "$part_rc" -ne 0 ]
check "fail-loud: non-UTC header rejected AND missing FOR RAB rejected" $?

# ── the parser survives CRLF (SYM-029) ───────────────────────────────────────
sed 's/$/\r/' "$TMP/good.md" > "$TMP/crlf.md"
validate "$TMP/crlf.md" && newest_for "$TMP/crlf.md" Fable | grep -q '13:00Z'
check "CRLF fixture parses identically (SYM-029 hazard covered)" $?

# ── B1 tripwire: the SIGPIPE hazard is real, and the count-form fix survives it ──
# A large (>200 KB) file with the four amendment strings at the TOP, so the OLD `grep -q`
# form closes the pipe while `tr` still has ~250 KB left to write into it.
BIG="$TMP/big-amend.md"
{
  printf '## fixture header\n'
  printf 'Must-quote everything you assert.\n'
  printf 'concordance label goes here.\n'
  printf 'must name the probe in every check.\n'
  printf 'Never impersonate the other lane.\n'
  yes 'padding line to bulk the fixture past 200 KB so grep -q races tr on a long stream' | head -c 250000
} > "$BIG"

# negative control: reproduce the OLD buggy form and show it SIGPIPEs (141) even though every
# string is present — this is the hazard B1 fixes, demonstrated live, not asserted from memory.
norm "$BIG" | grep -qi -- 'Must-quote'
old_rc=$?
[ "$old_rc" -eq 141 ]
check "B1 negative control: the OLD grep -q form SIGPIPEs (rc 141) on a large top-loaded fixture — the hazard is real" $?

# the fix: count form on the same large fixture must PASS (every string genuinely present)
amend_big=0
for rule in 'Must-quote' 'concordance label' 'must name the probe' 'Never impersonate'; do
  cnt="$(norm "$BIG" | grep -ci -- "$rule")"
  [ "${cnt:-0}" -ge 1 ] || amend_big=1
done
check "B1 fix: count-form check PASSES on the large fixture (all four strings genuinely present)" $amend_big

# the fix must still correctly FAIL when a string is genuinely absent
sed '/concordance label/d' "$BIG" > "$TMP/big-amend-missing.md"
amend_missing=0
for rule in 'Must-quote' 'concordance label' 'must name the probe' 'Never impersonate'; do
  cnt="$(norm "$TMP/big-amend-missing.md" | grep -ci -- "$rule")"
  [ "${cnt:-0}" -ge 1 ] || amend_missing=1
done
[ "$amend_missing" -eq 1 ]
check "B1 fix: count-form check correctly FAILS when a string is genuinely absent" $?

# ── B2 tripwire: gate-form header, grandfathered legacy, non-grandfathered legacy ───────────
cat > "$TMP/msg-suffix.md" <<'EOF'
## 2026-09-09T20:05Z · ⟨from: Fable⟩ → ⟨to: Codex⟩ · ⟨msg: MSG-FAB-0079⟩
**RECAP.** a
**FOR RAB.** b
**SUGGESTED PROMPT** c
EOF
validate_header "$TMP/msg-suffix.md"
check "B2 fix: a header with the gate's ⟨msg: MSG-FAB-NNNN⟩ suffix parses as well-formed" $?

cat > "$TMP/legacy-grandfathered.md" <<'EOF'
## 2026-08-24T02:49Z · ⟨from: Fable⟩ → ⟨to: Fable, and the record⟩
**RECAP.** a
**FOR RAB.** b
**SUGGESTED PROMPT** c
EOF
validate_header "$TMP/legacy-grandfathered.md"; leg_rc=$?
[ "$leg_rc" -eq 0 ] && [ "$VALIDATE_GRAND" -eq 1 ]
check "B2 fix: the legacy 'and the record' header at a grandfathered stamp passes (grandfathered=1)" $?

cat > "$TMP/legacy-not-grandfathered.md" <<'EOF'
## 2026-08-25T00:00Z · ⟨from: Fable⟩ → ⟨to: Fable, and the record⟩
**RECAP.** a
**FOR RAB.** b
**SUGGESTED PROMPT** c
EOF
validate_header "$TMP/legacy-not-grandfathered.md"; leg2_rc=$?
[ "$leg2_rc" -ne 0 ]
check "B2 negative control: a legacy-shaped header NOT on the grandfather list still FAILS" $?

# case 8 already re-proves the local-time-header rejection (ts_rc above) under the new HDR.

# ── B3 tripwire: post-cutoff missing slot fails; the same, pre-cutoff, is only counted ──────
cat > "$TMP/b3-post-missing.md" <<'EOF'
## 2026-09-09T20:05Z · ⟨from: Fable⟩ → ⟨to: Codex⟩
**RECAP.** a
**SUGGESTED PROMPT** c
EOF
b3_check "$TMP/b3-post-missing.md"; rc=$?
[ "$rc" -ne 0 ] && [ "$B3_OFFENDER" = "2026-09-09T20:05Z" ]
check "B3 fix: a post-cutoff entry missing FOR RAB FAILs, naming the offending stamp" $?

cat > "$TMP/b3-pre-missing.md" <<'EOF'
## 2026-09-09T19:55Z · ⟨from: Fable⟩ → ⟨to: Codex⟩
**RECAP.** a
**SUGGESTED PROMPT** c
EOF
b3_check "$TMP/b3-pre-missing.md"; rc=$?
[ "$rc" -eq 0 ] && [ "$B3_LEGACY_TOTAL" -eq 1 ] && [ "$B3_LEGACY_MISSING" -eq 1 ]
check "B3 fix: the SAME entry stamped before the cutoff is counted as legacy, not failed" $?

printf '════ coordination selftest: %d/%d ════\n' "$pass" "$total"
[ "$pass" -eq "$total" ]
