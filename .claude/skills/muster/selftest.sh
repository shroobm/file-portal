#!/usr/bin/env bash
# .claude/skills/muster/selftest.sh — the tripwires.
#
# docs/32 §5, rule 2: "A guard ships with a tripwire that violates the property. A guard nobody
# has watched fire is not a guard; it is a proxy with a reputation."
#
# Every case below VIOLATES the property the guard stands for and asserts the guard fires. That
# is the only test that measures the proxy→property correlation itself rather than assuming it.
# Rab's words for the method: "trip wire is like stepping into it, and see if it explodes or it
# was disarmed by the fix… that risk is safe since this is a program, and not literal c4."
#
# CASE 0 is a positive control. Without it, every case could pass because the fixture is broken
# in some way nobody noticed, and a suite that cannot distinguish "the guard fired" from
# "everything always fires" is a tautology — S78 §10.2, shipped in exactly this position.
#
#   bash .claude/skills/muster/selftest.sh        exit 0 = every tripwire fired
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MUSTER="$HERE/muster.sh"
OPEN="$HERE/open.sh"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

pass=0; failed=0
ok()   { printf '  \033[32mok\033[0m   %s\n' "$1"; pass=$((pass+1)); }
bad()  { printf '  \033[31mFAIL\033[0m %s\n     %s\n' "$1" "$2"; failed=$((failed+1)); }
# S194 E1: a case whose probe CANNOT run on this platform reads SKIP — its own tally, never a pass and never a fail (S192 read
# three governance suites red in CI for platform reasons that every close had called green; SYM-075's shape one door over).
# The platform is uname's reading; MUSTER_SELFTEST_PLATFORM=linux|windows overrides it for the CONTROLS: on the platform that
# CAN run a case, the case still fires (the positive control); off it, the case is counted skipped, and the suite's exit reads
# the fired cases only. `skip <name> <why> <n>` counts n assertions not run.
skipped=0
skip() { printf '  \033[33mSKIP\033[0m %s (%s assertion(s) not run)\n     %s\n' "$1" "$3" "$2"; skipped=$((skipped+$3)); }
on_windows() { local p="${MUSTER_SELFTEST_PLATFORM:-$(uname -s 2>/dev/null)}"; case "$p" in windows|MINGW*|MSYS*|CYGWIN*) return 0;; *) return 1;; esac; }

# assert <name> <expected-exit: 0|1> <must-match regex|-> <actual-exit> <output>
assert() {
  local name="$1" want="$2" re="$3" got="$4" out="$5"
  if [[ "$want" == "1" && "$got" -eq 0 ]]; then bad "$name" "expected a FIRE (exit 1), got exit 0"; return; fi
  if [[ "$want" == "0" && "$got" -ne 0 ]]; then bad "$name" "expected exit 0, got $got: $(printf '%s' "$out" | grep '✗' | head -2)"; return; fi
  if [[ "$re" != "-" ]] && ! printf '%s' "$out" | grep -qE "$re"; then
    bad "$name" "fired, but not with the expected reason (want /$re/)"; return
  fi
  ok "$name"
}

# ── fixture builders ─────────────────────────────────────────────────────────
# A fixture is a throwaway memory library + a throwaway git repo. Deliberately NOT a copy of the
# real ones: a fixture that shares the real files' assumptions is one check, not two (SYM-001).

mklib() { # mklib <dir> <cookies> <session> <sha> [ts_line_override]
  local d="$1" cookies="$2" sess="$3" sha="$4" override="${5:-}"
  mkdir -p "$d"
  {
    printf '# Memory Index\n\n'
    if [[ -n "$override" ]]; then printf '%s\n' "$override"
    else printf '> - **TIME-STATE** last session **%s**, closing SHA **%s**, cookies\n>   **received %s / given 3** · 2026-01-01.\n' "$sess" "$sha" "$cookies"
    fi
    printf '\n## Index\n'
    printf -- '- [some-note](some-note.md) — a line far below the anchor\n'
    # THE DECOY. S78 §10.3: removing a stale count from MEMORY.md re-planted the word TIME-STATE
    # further down, muster's window re-armed on it, and a fixture printed a green count read off
    # an index bullet while the real clock sat blank. Every fixture here carries a plausible
    # decoy below the anchor, so "reads the anchor" is tested rather than assumed.
    printf -- '- [cookie-tally](cookie-tally.md) — the old TIME-STATE said received 99 / given 9\n'
  } > "$d/MEMORY.md"
  printf '**Received from user: %s**\n' "$cookies" > "$d/cookie-tally.md"
}

mkrepo() { # mkrepo <dir> <rows...>  → echoes HEAD sha
  local d="$1"; shift
  mkdir -p "$d"; git -C "$d" init -q 2>/dev/null
  git -C "$d" config user.email t@t; git -C "$d" config user.name t
  { printf '# CLAUDE_README\n\n## Change Ledger\n\n| Date | Machine | Milestone | SHA |\n|---|---|---|---|\n'
    for r in "$@"; do printf '%s\n' "$r"; done; } > "$d/CLAUDE_README.md"
  git -C "$d" add -A >/dev/null 2>&1; git -C "$d" commit -qm fixture >/dev/null 2>&1
  git -C "$d" rev-parse --short HEAD
}

run() { MEMORY_LIB="$1" FP_REPO="$2" bash "$MUSTER" 2>&1; }

printf '\n──── muster tripwires ────\n'

# CASE 0 — POSITIVE CONTROL. A clean fixture must pass. If this fails, no other result means
# anything: the suite would be reporting the fixture's brokenness as the guard's vigilance.
R="$WORK/c0"; sha=$(mkrepo "$R" '| 2026-01-01 | Desktop | S41: first | 1111111 |' '| 2026-01-02 | Desktop | S42: second | SHAPLACEHOLDER |')
sed -i "s/SHAPLACEHOLDER/$sha/" "$R/CLAUDE_README.md"
git -C "$R" commit -qam rows >/dev/null 2>&1
mklib "$WORK/l0" 12 S42 "$sha"
out=$(run "$WORK/l0" "$R"); rc=$?
assert "CONTROL: a clean fixture passes (exit 0)" 0 - "$rc" "$out"

# CASE 1 — SYM-028. Rows out of file order. The property: the newest row is the newest SESSION.
# The old proxy was `tail -1` (position). Violate order; [3a] must name it as a sequence fault
# and NOT as a rewind, because the two were confused for three sessions.
R="$WORK/c1"; sha=$(mkrepo "$R" '| 2026-01-02 | Desktop | S42: second | 2222222 |' '| 2026-01-01 | Desktop | S41: first | 1111111 |')
mklib "$WORK/l1" 12 S42 "$sha"
out=$(run "$WORK/l1" "$R"); rc=$?
assert "SYM-028: out-of-order rows fire [3a], not a rewind" 1 'LEDGER ORDER.*✗.*42->41' "$rc" "$out"

# CASE 2 — docs/31 §1.15. A NEW row that omits its SHA cell is silently discarded, the previous
# row is selected, and SYM-028 recurs by another door. Violate: malform the newest row.
R="$WORK/c2"; sha=$(mkrepo "$R" '| 2026-01-01 | Desktop | S41: first | 1111111 |' '| 2026-01-02 | Desktop | S42: no sha cell here |')
mklib "$WORK/l2" 12 S42 "$sha"
out=$(run "$WORK/l2" "$R"); rc=$?
assert "a malformed NEWEST row fires [3b], naming the row" 1 'LEDGER PARSE.*✗.*UNPARSEABLE' "$rc" "$out"

# CASE 3 — S78 §10.3, the two-anchor fault. The property: the soft clock is the count IN the
# TIME-STATE entry. Violate: strip the count from the entry while leaving a plausible one below.
# A guard that reaches past the empty anchor and reports the decoy is worse than no guard.
R="$WORK/c3"; sha=$(mkrepo "$R" '| 2026-01-02 | Desktop | S42: second | SHAPLACEHOLDER |')
sed -i "s/SHAPLACEHOLDER/$sha/" "$R/CLAUDE_README.md"; git -C "$R" commit -qam rows >/dev/null 2>&1
mklib "$WORK/l3" 12 S42 "$sha" "> - **TIME-STATE** last session **S42**, closing SHA **$sha**, cookies unstated."
out=$(run "$WORK/l3" "$R"); rc=$?
assert "a TIME-STATE with no count fires, and does NOT read the decoy" 1 'SOFT clock.*✗' "$rc" "$out"
if printf '%s' "$out" | grep -qE 'SOFT clock.*(✓|hook=99)'; then
  bad "…and specifically did not adopt the decoy 99" "the window reached past the anchor"; else ok "…and specifically did not adopt the decoy 99"; fi

# CASE 4 — docs/31 §1.15. A missing/non-git repo must be a CONFIG fault. Violate: point at a
# directory that is not a repo. Reporting "rewind/fork?" here is the exact misdiagnosis SYM-028
# exists to prevent, arriving by a third door.
mkdir -p "$WORK/c4"; cp "$WORK/c0/CLAUDE_README.md" "$WORK/c4/"
out=$(run "$WORK/l0" "$WORK/c4"); rc=$?
assert "a non-git repo says CONFIG, never rewind" 1 'CONFIG.*not a git repo' "$rc" "$out"
if printf '%s' "$out" | grep -q 'rewind/fork'; then bad "…and does not say rewind" "misdiagnosis reachable"; else ok "…and does not say rewind"; fi

# CASE 5 — the hard clock itself. Violate: a TIME-STATE SHA that is not in the repo at all.
R="$WORK/c5"; sha=$(mkrepo "$R" '| 2026-01-02 | Desktop | S42: second | 2222222 |')
mklib "$WORK/l5" 12 S42 "9999999"
out=$(run "$WORK/l5" "$R"); rc=$?
assert "a TIME-STATE SHA that is not the ledger's fires [3]" 1 'HARD clock.*✗' "$rc" "$out"

printf '\n──── open.sh tripwires ────\n'

# CASE 6 — F1, found 2026-08-15. The property: session identity comes from LEDGER ROWS. The
# proxy docs/21 §7 prescribes reads any `S<n>` token in the file, prose included. Violate: put a
# far-future session number in PROSE. Identity must ignore it and still derive S43 from the rows.
R="$WORK/c6"; sha=$(mkrepo "$R" '| 2026-01-01 | Desktop | S41: first | 1111111 |' '| 2026-01-02 | Desktop | S42: second | SHAPLACEHOLDER |')
sed -i "s/SHAPLACEHOLDER/$sha/" "$R/CLAUDE_README.md"
printf '\nA later note in prose mentioning S99 for no good reason.\n' >> "$R/CLAUDE_README.md"
git -C "$R" add -A >/dev/null 2>&1; git -C "$R" commit -qm prose >/dev/null 2>&1
mklib "$WORK/l6" 12 S42 "$sha"
out=$(MEMORY_LIB="$WORK/l6" FP_REPO="$R" PIPE_ROOT="$WORK/nope" VAULT_DIR="$WORK/nope" \
      WIDGET_EXE="$WORK/nope" MUSTER_NO_REMOTE=1 bash "$OPEN" 2>&1); rc=$?
if printf '%s' "$out" | grep -qE 'this session +S43'; then ok "identity ignores an S99 in prose, derives S43 from rows"
else bad "identity ignores an S99 in prose" "got: $(printf '%s' "$out" | grep 'this session')"; fi
if printf '%s' "$out" | grep -qE 'collision.*S43 is already named'; then
  bad "…and does not confuse the prose S99 with a collision on S43" "false collision"; else ok "…and reports no false collision on S43"; fi

# CASE 6b — THE LEVER THAT DECIDES SHIPPING SAYS SO (S145; ERR-102, C-024). The property: when
# `audit-mode.txt` is not `enforce`, the card prints its own `SHIPS ON VERDICT` line — the levers
# row alone printed `audit=report` at three opens and was read past; a failing book reached the
# vault. Violate: a library root whose lever reads `report`; assert the line. Negative control:
# `enforce` must print nothing — a line that fires on every value is case 0's tautology.
LEV="$WORK/lev"; mkdir -p "$LEV"; printf 'report' > "$LEV/audit-mode.txt"
out=$(MEMORY_LIB="$WORK/l6" FP_REPO="$R" PIPE_ROOT="$LEV" VAULT_DIR="$WORK/nope" \
      WIDGET_EXE="$WORK/nope" MUSTER_NO_REMOTE=1 bash "$OPEN" 2>&1); rc=$?
if printf '%s' "$out" | grep -qE 'SHIPS ON VERDICT +audit-mode=report'; then ok "S145: a lever reading report makes the card say SHIPS ON VERDICT"
else bad "S145: a lever reading report makes the card say SHIPS ON VERDICT" "got: $(printf '%s' "$out" | grep -E 'levers|SHIPS' | head -2)"; fi
printf 'enforce' > "$LEV/audit-mode.txt"
out=$(MEMORY_LIB="$WORK/l6" FP_REPO="$R" PIPE_ROOT="$LEV" VAULT_DIR="$WORK/nope" \
      WIDGET_EXE="$WORK/nope" MUSTER_NO_REMOTE=1 bash "$OPEN" 2>&1); rc=$?
if printf '%s' "$out" | grep -qE 'SHIPS ON VERDICT'; then bad "S145 control: enforce prints no SHIPS ON VERDICT line" "the line fired on enforce"
else ok "S145 control: enforce prints no SHIPS ON VERDICT line"; fi

# CASE 7 — THE FAILED-PROBE RULE, paid for by this script's own first run. The property: `down`
# is a reading. Violate: make the process probe fail (a `tasklist` on PATH that exits non-zero)
# and assert the card says UNREAD. If it says `down`, a broken probe is again being rendered as
# a negative observation — the bug that shipped in the first draft of open.sh.
mkdir -p "$WORK/fakebin"; printf '#!/bin/sh\nexit 9\n' > "$WORK/fakebin/tasklist"; chmod +x "$WORK/fakebin/tasklist"
out=$(PATH="$WORK/fakebin:$PATH" MEMORY_LIB="$WORK/l6" FP_REPO="$R" PIPE_ROOT="$WORK/nope" \
      VAULT_DIR="$WORK/nope" WIDGET_EXE="$WORK/nope" MUSTER_NO_REMOTE=1 bash "$OPEN" 2>&1)
if printf '%s' "$out" | grep -qE 'processes +UNREAD'; then ok "a FAILED process probe renders UNREAD, never 'down'"
else bad "a FAILED process probe renders UNREAD" "got: $(printf '%s' "$out" | grep -E 'widget|processes' | head -2)"; fi

# CASE 8 — the same rule on the remote half. An unreachable ThinkPad must be UNREAD, never a
# statement that staging is clean. Violate: point ssh at a host that cannot answer.
out=$(MEMORY_LIB="$WORK/l6" FP_REPO="$R" PIPE_ROOT="$WORK/nope" VAULT_DIR="$WORK/nope" \
      WIDGET_EXE="$WORK/nope" PATH="$WORK/fakebin:$PATH" bash -c '
        printf "#!/bin/sh\nexit 255\n" > '"$WORK"'/fakebin/ssh; chmod +x '"$WORK"'/fakebin/ssh
        bash "'"$OPEN"'" 2>&1')
if printf '%s' "$out" | grep -qE 'thinkpad +UNREAD'; then ok "an unreachable receiver renders UNREAD, never 'clean'"
else bad "an unreachable receiver renders UNREAD" "got: $(printf '%s' "$out" | grep thinkpad)"; fi

# CASE 9 — THE PARTIAL-OBSERVATION RULE, the mirror of case 7, paid for by S80's own open. Case 7
# guards a probe that FAILED being rendered as absence. This guards a probe that SUCCEEDED being
# rendered as the WHOLE truth when it saw only the first row: `awk '{print $2; exit}'` printed
# `widget 18856` while 18856 and 19536 were both alive, each with its own watcher on the same drop
# folder (SYM-033). Violate: a process table with TWO widget rows. The card must name both.
cat > "$WORK/fakebin/tasklist" <<'FAKE'
#!/bin/sh
cat <<'TBL'
Image Name                     PID Session Name        Session#    Mem Usage
========================= ======== ================ =========== ============
System Idle Process              0 Services                   0          8 K
explorer.exe                  5200 Console                    1     90,000 K
file-portal-widget.exe       18856 Console                    1     22,000 K
file-portal-widget.exe       19536 Console                    1     25,000 K
python.exe                    6420 Console                    1      3,000 K
ollama.exe                    9168 Console                    1     38,000 K
llama-server.exe             21240 Console                    1  1,500,000 K
TBL
FAKE
chmod +x "$WORK/fakebin/tasklist"
out=$(PATH="$WORK/fakebin:$PATH" MEMORY_LIB="$WORK/l6" FP_REPO="$R" PIPE_ROOT="$WORK/nope" \
      VAULT_DIR="$WORK/nope" WIDGET_EXE="$WORK/nope" MUSTER_NO_REMOTE=1 bash "$OPEN" 2>&1)
if printf '%s' "$out" | grep -qE 'widget +2 INSTANCES'; then ok "two widgets are reported as two, not as the first one"
else bad "two widgets are reported as two" "got: $(printf '%s' "$out" | grep -E ' widget ')"; fi
if printf '%s' "$out" | grep -q '18856' && printf '%s' "$out" | grep -q '19536'; then
  ok "…and BOTH pids are named, not just the first"
else bad "…and BOTH pids are named" "got: $(printf '%s' "$out" | grep -E ' widget ')"; fi
if printf '%s' "$out" | grep -qE 'llama-server +1 .*parent PID decides'; then
  ok "…and a llama-server is counted with its identity caveat, never identified by name"
else bad "llama-server identity caveat" "got: $(printf '%s' "$out" | grep 'llama-server')"; fi

# CASE 10 — the other direction, so the new row cannot pass by always shouting. One widget must
# still render as a bare pid: a guard that fires on every input is the tautology case 0 exists to
# catch, one row over.
sed -i '/19536/d' "$WORK/fakebin/tasklist"
out=$(PATH="$WORK/fakebin:$PATH" MEMORY_LIB="$WORK/l6" FP_REPO="$R" PIPE_ROOT="$WORK/nope" \
      VAULT_DIR="$WORK/nope" WIDGET_EXE="$WORK/nope" MUSTER_NO_REMOTE=1 bash "$OPEN" 2>&1)
if printf '%s' "$out" | grep -qE 'widget +18856 *$'; then ok "one widget still renders as a bare pid"
else bad "one widget still renders as a bare pid" "got: $(printf '%s' "$out" | grep -E ' widget ')"; fi

printf '\n──── lane + origin tripwires (born of the 2026-08-16 fork) ────\n'

# CASE 11 — THE LANE RULE. The property: the clock reads the Desktop lane. Violate: plant a
# ThinkPad row with a HIGHER session number mid-table. The old parser would adopt S99 as newest
# (phantom SHA mismatch) AND fail [3a] on 99->42. The new one must pass clean, select S42, and
# NAME the lane row rather than silently dropping it.
R="$WORK/c11"; sha=$(mkrepo "$R" '| 2026-01-01 | Desktop | S41: first | 1111111 |' '| 2026-01-05 | ThinkPad | S99: their newest | aaaaaaa |' '| 2026-01-02 | Desktop | S42: second | SHAPLACEHOLDER |')
sed -i "s/SHAPLACEHOLDER/$sha/" "$R/CLAUDE_README.md"; git -C "$R" commit -qam rows >/dev/null 2>&1
mklib "$WORK/l11" 12 S42 "$sha"
out=$(run "$WORK/l11" "$R"); rc=$?
assert "LANE: a ThinkPad S99 mid-table neither breaks order nor becomes the clock" 0 'HARD clock.*✓.*S42' "$rc" "$out"
if printf '%s' "$out" | grep -qE 'other-lane: ThinkPad-S99'; then ok "…and the lane row is NAMED on the card, not silently gone"
else bad "…and the lane row is NAMED on the card" "got: $(printf '%s' "$out" | grep 'LEDGER PARSE')"; fi

# CASE 12 — the same lane rule at IDENTITY. Violate with the same fixture: open.sh must derive
# S43 from the Desktop lane, never S100 from the ThinkPad's S99.
out=$(MEMORY_LIB="$WORK/l11" FP_REPO="$R" PIPE_ROOT="$WORK/nope" VAULT_DIR="$WORK/nope" \
      WIDGET_EXE="$WORK/nope" MUSTER_NO_REMOTE=1 bash "$OPEN" 2>&1)
if printf '%s' "$out" | grep -qE 'this session +S43'; then ok "IDENTITY: derives S43 from the Desktop lane, not S100 from the ThinkPad's"
else bad "IDENTITY derives from the Desktop lane" "got: $(printf '%s' "$out" | grep 'this session')"; fi

# CASE 13 — THE ORIGIN RULE. The property: the hard clock covers the SHARED record. Violate:
# fork a fixture origin (local ahead 1 / behind 1) and assert the card FAILS naming FORKED.
# ssh is stubbed to die fast so the receiver probe can neither slow nor rescue the card.
printf '#!/bin/sh\nexit 255\n' > "$WORK/fakebin/ssh"; chmod +x "$WORK/fakebin/ssh"
B13="$WORK/c13-bare"; git init -q --bare "$B13" 2>/dev/null
A13="$WORK/c13a"; sha=$(mkrepo "$A13" '| 2026-01-01 | Desktop | S41: first | 1111111 |' '| 2026-01-02 | Desktop | S42: second | SHAPLACEHOLDER |')
sed -i "s/SHAPLACEHOLDER/$sha/" "$A13/CLAUDE_README.md"; git -C "$A13" commit -qam rows >/dev/null 2>&1
sha=$(git -C "$A13" log --format=%h -2 2>/dev/null | tail -1)
git -C "$A13" remote add origin "$B13"; git -C "$A13" push -qu origin HEAD >/dev/null 2>&1
C13="$WORK/c13c"; git clone -q "$B13" "$C13" 2>/dev/null   # cloned NOW = behind-only later (case 14)
D13="$WORK/c13d"; git clone -q "$B13" "$D13" 2>/dev/null
git -C "$D13" config user.email t@t; git -C "$D13" config user.name t
printf 'their work\n' > "$D13/other.txt"; git -C "$D13" add -A >/dev/null 2>&1; git -C "$D13" commit -qm theirs >/dev/null 2>&1; git -C "$D13" push -q >/dev/null 2>&1
printf 'my work\n' > "$A13/mine.txt"; git -C "$A13" add -A >/dev/null 2>&1; git -C "$A13" commit -qm mine >/dev/null 2>&1
mklib "$WORK/l13" 12 S42 "$sha"
out=$(PATH="$WORK/fakebin:$PATH" MEMORY_LIB="$WORK/l13" FP_REPO="$A13" PIPE_ROOT="$WORK/nope" \
      VAULT_DIR="$WORK/nope" WIDGET_EXE="$WORK/nope" bash "$OPEN" 2>&1); rc=$?
assert "ORIGIN: a forked upstream FAILS the card, naming both counts" 1 'FORKED — ahead 1 / behind 1' "$rc" "$out"

# CASE 14 — the other directions, so the origin row cannot pass by always shouting: behind-only
# and ahead-only are ADVISORIES (exit 0), each named for what it is.
out=$(PATH="$WORK/fakebin:$PATH" MEMORY_LIB="$WORK/l13" FP_REPO="$C13" PIPE_ROOT="$WORK/nope" \
      VAULT_DIR="$WORK/nope" WIDGET_EXE="$WORK/nope" bash "$OPEN" 2>&1); rc=$?
assert "ORIGIN: behind-only is an advisory (pull before work), not an incident" 0 'behind 1 — new work on origin' "$rc" "$out"
printf 'unpushed\n' > "$D13/more.txt"; git -C "$D13" add -A >/dev/null 2>&1; git -C "$D13" commit -qm unpushed >/dev/null 2>&1
out=$(PATH="$WORK/fakebin:$PATH" MEMORY_LIB="$WORK/l13" FP_REPO="$D13" PIPE_ROOT="$WORK/nope" \
      VAULT_DIR="$WORK/nope" WIDGET_EXE="$WORK/nope" bash "$OPEN" 2>&1); rc=$?
assert "ORIGIN: ahead-only is an advisory (the close must push), not an incident" 0 'ahead 1 — unpushed local work' "$rc" "$out"

# ── CASES 15-18: close.sh, the mechanical close (S103) ──────────────────────────────────────
# The close is where two sessions reported clean on top of a red CI build, so its guard gets
# the same treatment as the open's: every case VIOLATES the property and asserts the fire.
CLOSE="$HERE/close.sh"

# CASE 15 - no pin at all. A guard that shrugs at a missing argument is how a close silently
# checks nothing at all.
out=$(bash "$CLOSE" 2>&1); rc=$?
assert "CLOSE: a missing pin is a red, not a shrug" 1 'MISSING' "$rc" "$out"

# CASE 16 - a pin that does not resolve. The dangerous failure is reading it as "nothing changed
# since"; the row must say UNRESOLVABLE and must never read as clean.
out=$(bash "$CLOSE" deadbeefdeadbeef 2>&1); rc=$?
assert "CLOSE: an unresolvable pin fails loud and never reads clean" 1 'UNRESOLVABLE' "$rc" "$out"

# CASE 17 - THE ONE THIS SCRIPT EXISTS FOR: a red CI must stop the close. Pointed at a REAL
# historical red run (534a6c0, red on Format check) rather than a mock, so the network path,
# the parse and the verdict mapping are all exercised on genuine data. Skipped honestly when
# GitHub is unreachable - an offline machine must not fail this suite, nor silently pass it.
probe=$(FP_CI_SHA=534a6c01 bash "$CLOSE" HEAD 2>&1)
if printf '%s' "$probe" | grep -q 'CI               UNREAD'; then
  printf 'SKIP - CI red-path case: GitHub unreachable (this is not a pass)
'
else
  rc=$(FP_CI_SHA=534a6c01 bash "$CLOSE" HEAD >/dev/null 2>&1; echo $?)
  assert "CLOSE: a RED CI run stops the close (real historical red 534a6c0)" 1 'CI               RED' "$rc" "$probe"
fi

# CASE 18 - the UNREAD discipline: an unreachable checker prints UNREAD and is NOT counted red.
# A close that dies because a tool is missing teaches people to skip the close.
CLEAN18="$WORK/clean18"; mkdir -p "$CLEAN18"
git -C "$CLEAN18" init -q 2>/dev/null; printf 'x
' > "$CLEAN18/f.txt"
git -C "$CLEAN18" add -A >/dev/null 2>&1
git -C "$CLEAN18" -c user.email=t@t -c user.name=t commit -qm base >/dev/null 2>&1
out=$(FP_PY="/no/such/python.exe" FP_REPO="$CLEAN18" bash "$CLOSE" HEAD 2>&1); rc=$?
assert "CLOSE: a missing checker is UNREAD, never a red and never a green" 0 'GLASS            UNREAD' "$rc" "$out"


# CASE 27 - the MODULARITY GATE (docs/18 SS2, signed Rab S106). A number that decides
# something is a lever, not a constant. Both directions, on a fixture the case builds:
# a bare threshold constant is NAMED, and the same constant with a waiver is not.
GATE="$WORK/gate"; mkdir -p "$GATE"
git -C "$GATE" init -q 2>/dev/null
printf 'x = 1\n' > "$GATE/m.py"
git -C "$GATE" add -A >/dev/null 2>&1
git -C "$GATE" -c user.email=t@t -c user.name=t commit -qm base >/dev/null 2>&1
base=$(git -C "$GATE" rev-parse HEAD)
printf 'x = 1\nVETO_SOMETHING = 0.42\n' > "$GATE/m.py"
git -C "$GATE" add -A >/dev/null 2>&1
git -C "$GATE" -c user.email=t@t -c user.name=t commit -qm add >/dev/null 2>&1
out=$(FP_PY="/no/such/python.exe" FP_REPO="$GATE" bash "$CLOSE" "$base" 2>&1); rc=$?
assert "CLOSE: the modularity gate NAMES a bare threshold constant added since the pin" 0 'VETO_SOMETHING' "$rc" "$out"

# ...and the waiver silences it. Without this half the gate could be a constant that always
# fires, which is the shape S105 Lane B caught in coordination/selftest.sh case 6.
printf 'x = 1\nVETO_SOMETHING = 0.42  # lever-waiver: Rab only; move it if a 3rd corpus disagrees\n' > "$GATE/m.py"
git -C "$GATE" add -A >/dev/null 2>&1
git -C "$GATE" -c user.email=t@t -c user.name=t commit -qm waive >/dev/null 2>&1
out=$(FP_PY="/no/such/python.exe" FP_REPO="$GATE" bash "$CLOSE" "$base" 2>&1); rc=$?
assert "CLOSE: a written lever-waiver silences the gate (it is not a constant that always fires)" 0 'LEVERS           no unlevered' "$rc" "$out"

# CASE 28 - DOCTOR parse and epistemic scope. Comments and inert strings are deliberately
# planted with quoted lever names: lexical grep will see them, but the card must never upgrade
# that occurrence to "consumed" or "read". A second declaration shape that the parser cannot
# understand must make the whole denominator UNREAD rather than disappear.
DOC28="$WORK/doctor28"; mkdir -p "$DOC28"
printf 'actually_read=10\ncomment_only=20\ndead_text=30\n' > "$DOC28/levers.txt"
cat > "$DOC28/consumer.py" <<'DOC'
value = settings.get("actually_read")
# "comment_only"
"""dead_text"""
DOC
out=$(FP_PY="/no/such/python.exe" FP_REPO="$GATE" FP_DOCTOR_LEVERS="$DOC28/levers.txt" \
      FP_DOCTOR_CODE="$DOC28/consumer.py" bash "$CLOSE" "$base" 2>&1); rc=$?
assert "CLOSE DOCTOR: lexical hits are labelled lexical and actual consumption stays UNREAD" 0 'lever lexical parity:.*quoted refs 3.*MISSING 0' "$rc" "$out"
if printf '%s' "$out" | grep -q 'consumed'; then
  bad "CLOSE DOCTOR: never calls a lexical occurrence consumed" "got: $(printf '%s' "$out" | grep DOCTOR)"
else ok "CLOSE DOCTOR: never calls a lexical occurrence consumed"; fi
assert "CLOSE DOCTOR: the card states lexical occurrence does not prove a read" 0 'lexical occurrence does NOT prove' "$rc" "$out"

printf 'actually_read=10\nexport silently_unparsed=40\n' > "$DOC28/levers.txt"
out=$(FP_PY="/no/such/python.exe" FP_REPO="$GATE" FP_DOCTOR_LEVERS="$DOC28/levers.txt" \
      FP_DOCTOR_CODE="$DOC28/consumer.py" bash "$CLOSE" "$base" 2>&1); rc=$?
assert "CLOSE DOCTOR: one unparsed declaration makes the whole denominator UNREAD" 0 'lever parse incomplete/ambiguous:.*rows 2.*parsed 1' "$rc" "$out"

printf '#!/bin/sh\nexit 2\n' > "$DOC28/grep-fails"; chmod +x "$DOC28/grep-fails"
printf 'actually_read=10\n' > "$DOC28/levers.txt"
out=$(FP_PY="/no/such/python.exe" FP_REPO="$GATE" FP_DOCTOR_LEVERS="$DOC28/levers.txt" \
      FP_DOCTOR_CODE="$DOC28/consumer.py" FP_DOCTOR_GREP="$DOC28/grep-fails" \
      bash "$CLOSE" "$base" 2>&1); rc=$?
assert "CLOSE DOCTOR: a failed reference probe is UNREAD, never 'missing'" 0 'consumer reference probe exited 2' "$rc" "$out"

# ARMED 2026-09-05 (S116, S108 sign sheet item 9): a lever the operator file NAMES and the
# consumer never quotes is a MEASURED red, exit 1. The three UNREAD shapes above (unparsed
# declaration, failed probe) keep asserting exit 0 — arming must not turn a failed probe into
# a fail. The positive control (MISSING 0 → exit 0) is case 28's first assertion.
printf 'actually_read=10\nnever_quoted=20\n' > "$DOC28/levers.txt"
out=$(FP_PY="/no/such/python.exe" FP_REPO="$GATE" FP_DOCTOR_LEVERS="$DOC28/levers.txt" \
      FP_DOCTOR_CODE="$DOC28/consumer.py" bash "$CLOSE" "$base" 2>&1); rc=$?
assert "CLOSE DOCTOR (armed): a named lever the consumer never quotes is a red — exit 1" 1 'MISSING: never_quoted' "$rc" "$out"
assert "CLOSE DOCTOR (armed): the red still says a lexical hit is not proof of a read" 1 'does NOT prove' "$rc" "$out"

# CASE 29 - CENSUS must reconcile three independent-looking surfaces: declared IDs, actual
# control-flow markers, and the suite's banner numerator/denominator. Each fixture is disposable;
# close remains warn-only and the fixture suites write nowhere.
CEN29="$WORK/census29"; mkdir -p "$CEN29"
cat > "$CEN29/good.sh" <<'CEN'
#!/usr/bin/env bash
# ---- T1: first
# ---- T2: second
echo 'TRIPWIRE T1 FIRED'
echo 'TRIPWIRE T2 FIRED'
echo 'ALL TRIPWIRES FIRED — 2/2, exit 0'
CEN
cat > "$CEN29/zero-two.sh" <<'CEN'
#!/usr/bin/env bash
# ---- T1: first
# ---- T2: second
echo 'TRIPWIRE T1 FIRED'
echo 'TRIPWIRE T2 FIRED'
echo 'ALL TRIPWIRES FIRED — 0/2, exit 0'
CEN
cat > "$CEN29/shared-lie.sh" <<'CEN'
#!/usr/bin/env bash
# ---- T1: first
# ---- T2: declared but never reached
echo 'TRIPWIRE T1 FIRED'
echo 'ALL TRIPWIRES FIRED — 2/2, exit 0'
CEN
cat > "$CEN29/huge.sh" <<'CEN'
#!/usr/bin/env bash
# ---- T1: first
# ---- T2: second
echo 'TRIPWIRE T1 FIRED'
echo 'TRIPWIRE T2 FIRED'
echo 'ALL TRIPWIRES FIRED — 2/999999999999999999999999999999, exit 0'
CEN
chmod +x "$CEN29"/*.sh

out=$(FP_PY="/no/such/python.exe" FP_REPO="$GATE" FP_CENSUS_SUITE="$CEN29/good.sh" bash "$CLOSE" "$base" 2>&1); rc=$?
assert "CLOSE CENSUS control: declared = FIRED = banner passes" 0 'declared 2 = FIRED 2 = banner 2/2' "$rc" "$out"
# ARMED 2026-09-05 (S116, S108 sign sheet item 9 signed by Rab): the two RED shapes below now
# EXIT 1. Until today they asserted exit 0 — a gate whose own tripwire pins the warn-only exit
# code would have kept certifying the unarmed behaviour after the arming, which is the shape
# of a guard that decays without anyone re-reading it (close.sh's own CI probe, S109).
out=$(FP_PY="/no/such/python.exe" FP_REPO="$GATE" FP_CENSUS_SUITE="$CEN29/zero-two.sh" bash "$CLOSE" "$base" 2>&1); rc=$?
assert "CLOSE CENSUS (armed): 0/2 can never green a two-tripwire suite — exit 1" 1 'RED.*banner 0/2' "$rc" "$out"
out=$(FP_PY="/no/such/python.exe" FP_REPO="$GATE" FP_CENSUS_SUITE="$CEN29/shared-lie.sh" bash "$CLOSE" "$base" 2>&1); rc=$?
assert "CLOSE CENSUS (armed): a declared-but-unreached tripwire is a red — exit 1" 1 'RED.*declaration/flight mismatch' "$rc" "$out"
assert "CLOSE CENSUS: the missing tripwire ID is visible" 1 'MISSING FIRED: T2' "$rc" "$out"
out=$(FP_PY="/no/such/python.exe" FP_REPO="$GATE" FP_CENSUS_SUITE="$CEN29/huge.sh" bash "$CLOSE" "$base" 2>&1); rc=$?
assert "CLOSE CENSUS: an oversized integer is UNREAD, never a numeric false green" 0 'banner integers exceed the bounded parser' "$rc" "$out"

# R3 (S116 verify fleet, lane B, 2026-09-05): arming must not turn "the suite could not RUN"
# into a red. A present file that dies before its first case (interpreter/permission/syntax) is
# a failed probe — UNREAD, exit 0 (SYM-031). A suite that fired a tripwire and still exited
# non-zero has measured a broken tripwire — RED, exit 1. Both shapes, so the boundary is watched.
cat > "$CEN29/cannot-run.sh" <<'CEN'
#!/usr/bin/env bash
# ---- T1: first
# ---- T2: second
exit 127
CEN
cat > "$CEN29/ran-and-failed.sh" <<'CEN'
#!/usr/bin/env bash
# ---- T1: first
# ---- T2: second
echo 'TRIPWIRE T1 FIRED'
exit 1
CEN
chmod +x "$CEN29"/cannot-run.sh "$CEN29"/ran-and-failed.sh
out=$(FP_PY="/no/such/python.exe" FP_REPO="$GATE" FP_CENSUS_SUITE="$CEN29/cannot-run.sh" bash "$CLOSE" "$base" 2>&1); rc=$?
assert "CLOSE CENSUS (armed, R3): a suite that could not run is UNREAD — exit 0, never a green" 0 'UNREAD.*could not run.*exit 127.*no tripwire output' "$rc" "$out"
out=$(FP_PY="/no/such/python.exe" FP_REPO="$GATE" FP_CENSUS_SUITE="$CEN29/ran-and-failed.sh" bash "$CLOSE" "$base" 2>&1); rc=$?
assert "CLOSE CENSUS (armed, R3): a suite that fired and then failed is a red — exit 1" 1 'RED.*exited 1 after firing 1' "$rc" "$out"

# ── REGISTER gate, ARMED 2026-09-06 (S117, Rab's "arm REGISTER") ─────────────────────────────
# Property: a session that never wrote OPEN-TASKS.md is a MEASURED red; one that wrote it is
# not; a repo with no register at all stays UNREAD (exit 0). Three shapes, one fixture repo.
REG="$WORK/register"; mkdir -p "$REG"
git -C "$REG" init -q 2>/dev/null
printf '| A1 | first |\n' > "$REG/OPEN-TASKS.md"; printf 'x = 1\n' > "$REG/m.py"
git -C "$REG" add -A >/dev/null 2>&1
git -C "$REG" -c user.email=t@t -c user.name=t commit -qm base >/dev/null 2>&1
regbase=$(git -C "$REG" rev-parse HEAD)
printf 'x = 2\n' > "$REG/m.py"
git -C "$REG" add -A >/dev/null 2>&1
git -C "$REG" -c user.email=t@t -c user.name=t commit -qm "code only" >/dev/null 2>&1
out=$(FP_PY="/no/such/python.exe" FP_REPO="$REG" bash "$CLOSE" "$regbase" 2>&1); rc=$?
assert "CLOSE REGISTER (armed): OPEN-TASKS.md untouched since the pin is a red — exit 1" 1 'REGISTER.*RED.*UNTOUCHED' "$rc" "$out"
printf '| A1 | first |\n| A2 | second |\n' > "$REG/OPEN-TASKS.md"
git -C "$REG" add -A >/dev/null 2>&1
git -C "$REG" -c user.email=t@t -c user.name=t commit -qm "register written" >/dev/null 2>&1
out=$(FP_PY="/no/such/python.exe" FP_REPO="$REG" bash "$CLOSE" "$regbase" 2>&1); rc=$?
assert "CLOSE REGISTER (armed) control: a written register is not a red — exit 0" 0 'REGISTER.*written this session' "$rc" "$out"
# the no-register shape is case 18/27's fixture repos (no OPEN-TASKS.md) — they assert exit 0 above.


# ── CASES 30-32: THE DESCENDANT RULE (S109 — proposed by Claude Opus 5, work authorised by
# Rab's blanket "I sign on everything..."; he did NOT author it. The earlier "Rab's, signed"
# attribution here was a fabricated signature, corrected — see muster.sh's block) ────────────
#
# PROVENANCE: these three cases were written SINGLE-LANE by Claude agents with NO cross-vendor
# check — the Codex lane was out of budget. Nothing here has been read by a second model.
#
# The property: the two clocks agree when the LEDGER SHA IS AN ANCESTOR OF THE TIME-STATE SHA.
# The old proxy was byte-equality, and the row-vs-final gap makes that unreachable by
# construction (muster.sh [3] carries the S108 specimen). Three cases, because a rule with only
# its happy path is a blanket green: 30 asserts the descendant case now RECONCILES, 31 asserts a
# GENUINE FORK still fires, 32 asserts an out-of-repo ledger SHA still fires as CONFIG.

# CASE 30 — the S108 shape, built commit by commit: the closing commit (which the row names),
# then the row itself, then a gate-forced commit AFTER the row (which TIME-STATE names), then
# later work. Under byte-equality this fixture is an INCIDENT; under the rule it reconciles, and
# the card must print the GAP rather than a bare checkmark.
R="$WORK/c30"
sha_row=$(mkrepo "$R" '| 2026-01-01 | Desktop | S41: first | 1111111 |' '| 2026-01-02 | Desktop | S42: the closing commit | SHAPLACEHOLDER |')
sed -i "s/SHAPLACEHOLDER/$sha_row/" "$R/CLAUDE_README.md"
git -C "$R" commit -qam 'docs: the ledger row, naming the SHA it could see' >/dev/null 2>&1
printf 'a lever waiver the close forced\n' > "$R/gate.txt"
git -C "$R" add -A >/dev/null 2>&1
git -C "$R" commit -qm 'close-phase: a gate fired AFTER the row was written' >/dev/null 2>&1
sha_final=$(git -C "$R" rev-parse --short HEAD)
printf 'post-close work\n' > "$R/later.txt"
git -C "$R" add -A >/dev/null 2>&1
git -C "$R" commit -qm 'work landing after the close, same line' >/dev/null 2>&1
mklib "$WORK/l30" 12 S42 "$sha_final"
out=$(run "$WORK/l30" "$R"); rc=$?
assert "S109 DESCENDANT: a TIME-STATE AHEAD of its ledger row reconciles (exit 0)" 0 'HARD clock.*✓.*2 commit\(s\) AHEAD of ledger' "$rc" "$out"
if printf '%s' "$out" | grep -qE 'SHA mismatch'; then
  bad "…and the old byte-equality verdict is gone" "still reporting 'SHA mismatch' on a descendant"
else ok "…and the old byte-equality verdict is gone"; fi

# CASE 31 — THE NEGATIVE HALF, and the reason case 30 is not a blanket green. Two commits off a
# shared base, on divergent lines: the ledger names one, TIME-STATE names the other, neither
# contains the other. This is what an actual fork or rewind looks like and it must still exit 1 —
# and it must fire on the ANCESTRY verdict, not on some leftover equality test, or the new rule
# is untested and the old one is doing the work.
R="$WORK/c31"; mkdir -p "$R"
git -C "$R" init -q 2>/dev/null
git -C "$R" config user.email t@t; git -C "$R" config user.name t
printf 'base\n' > "$R/f.txt"
git -C "$R" add -A >/dev/null 2>&1; git -C "$R" commit -qm base >/dev/null 2>&1
main31=$(git -C "$R" rev-parse --abbrev-ref HEAD)
git -C "$R" checkout -q -b forklane
printf 'the other line\n' > "$R/a.txt"
git -C "$R" add -A >/dev/null 2>&1; git -C "$R" commit -qm 'the commit the ledger row names' >/dev/null 2>&1
sha_fork=$(git -C "$R" rev-parse --short HEAD)
git -C "$R" checkout -q "$main31"
printf 'this line\n' > "$R/b.txt"
git -C "$R" add -A >/dev/null 2>&1; git -C "$R" commit -qm 'the commit TIME-STATE names' >/dev/null 2>&1
sha_ts=$(git -C "$R" rev-parse --short HEAD)
{ printf '# CLAUDE_README\n\n## Change Ledger\n\n| Date | Machine | Milestone | SHA |\n|---|---|---|---|\n'
  printf '| 2026-01-01 | Desktop | S41: first | 1111111 |\n'
  printf '| 2026-01-02 | Desktop | S42: closed on the other line | %s |\n' "$sha_fork"; } > "$R/CLAUDE_README.md"
git -C "$R" add -A >/dev/null 2>&1; git -C "$R" commit -qm ledger >/dev/null 2>&1
mklib "$WORK/l31" 12 S42 "$sha_ts"
out=$(run "$WORK/l31" "$R"); rc=$?
# The reason string changed when D3 split this branch three ways (a LAGGING clock is on the SAME
# line and must not be called a fork). This fixture IS a genuine fork - two divergent lines - so
# the CODE was right and this regex was stale. Re-anchored on the new wording, and deliberately
# still anchored on a REASON rather than the exit code: matching only rc==1 would pass on any
# failure at all and turn the case into a tautology.
assert "S109 NEGATIVE: a genuine fork (ledger NOT an ancestor) STILL exits 1" 1 'HARD clock.*✗ FORK/REWIND — ledger .* and TIME-STATE .* share no ancestry' "$rc" "$out"
# …and the mirror of case 34: a real fork must NOT be softened into "your clock is merely behind".
if printf '%s' "$out" | grep -q 'TIME-STATE LAGS'; then
  bad "S109 NEGATIVE: …and a fork is NOT softened into a lag" "divergent history reported as a lag"
else ok "S109 NEGATIVE: …and a fork is NOT softened into a lag"; fi

# CASE 32 — the other way the rule can be handed a question it cannot answer: a ledger SHA that
# is not in this repo at all. Ancestry on a missing object is unanswerable, and an unanswerable
# ancestry check must never fall through to green. CONFIG, not rewind — the distinction this
# file has had to relearn four times.
R="$WORK/c32"; sha=$(mkrepo "$R" '| 2026-01-01 | Desktop | S41: first | 1111111 |' '| 2026-01-02 | Desktop | S42: second | deadbee |')
mklib "$WORK/l32" 12 S42 "$sha"
out=$(run "$WORK/l32" "$R"); rc=$?
assert "S109: an out-of-repo LEDGER SHA is CONFIG and still exits 1, never green" 1 'HARD clock.*✗ CONFIG — ledger deadbee is not a commit' "$rc" "$out"
if printf '%s' "$out" | grep -q 'rewind/fork'; then
  bad "…and does not say rewind" "a missing object misdiagnosed as a rewind"; else ok "…and does not say rewind"; fi
# ── CASES 33-35: THE TWO HOLES THIS FLEET'S OWN VERIFIER FOUND IN CASES 30-32 ────────────────
# Both were shipped by the lane that wrote the descendant rule and neither was disclosed in its
# report. They are tripwired here because a rule that loosened a guard without a test to bound it
# is exactly the shape this file exists to refuse.

# CASE 33 — D2, THE UNBOUNDED GREEN. The descendant rule as first written had no ceiling: a ledger
# row 61 commits stale rendered ✓ CLEAN at exit 0, a green the OLD byte-equality caught. The
# legitimate gap is the handful of commits a close's own gates force after its row (S108's was 3);
# a row hundreds behind means a close never wrote one, which is a different fault and must not ride
# in on this exemption.
R="$WORK/c33"; base=$(mkrepo "$R" '| 2026-01-02 | Desktop | S42: second | SHAPLACEHOLDER |')
sed -i "s/SHAPLACEHOLDER/$base/" "$R/CLAUDE_README.md"; git -C "$R" commit -qam rows >/dev/null 2>&1
for i in $(seq 1 15); do printf 'c%s\n' "$i" > "$R/f$i.txt"; git -C "$R" add -A >/dev/null 2>&1; git -C "$R" commit -qm "c$i" >/dev/null 2>&1; done
mklib "$WORK/l33" 12 S42 "$(git -C "$R" rev-parse --short HEAD)"
out=$(run "$WORK/l33" "$R"); rc=$?
assert "S109 D2: a ledger row far past the gap lever is STALE, not a green" 1 'LEDGER STALE' "$rc" "$out"

# CASE 33b — THE CONTROL, and without it case 33 is satisfied by a rule that refuses every gap.
# A gap inside the lever must still RECONCILE, because that gap is the whole reason the rule exists.
mklib "$WORK/l33b" 12 S42 "$(git -C "$R" rev-parse --short HEAD~12)"
sed -i "s/| 2026-01-02 | Desktop | S42: second | [0-9a-f]* |/| 2026-01-02 | Desktop | S42: second | $(git -C "$R" rev-parse --short HEAD~15) |/" "$R/CLAUDE_README.md"
git -C "$R" commit -qam ctl >/dev/null 2>&1
out=$(run "$WORK/l33b" "$R"); rc=$?
assert "S109 D2 control: a gap INSIDE the lever still reconciles" 0 'AHEAD of ledger' "$rc" "$out"

# CASE 34 — D3, THE FALSE DIAGNOSIS. The first cut printed FORK/REWIND for both directions of a
# failed ancestry test. Git contradicts that: a TIME-STATE that merely LAGS its ledger row is on
# the SAME line of history, and the remedy is "advance the clock", not "reconcile a fork". The
# comment above claimed to close the fourth instance of a config fault wearing a rewind's clothing
# while shipping a fifth.
R="$WORK/c34"; base=$(mkrepo "$R" '| 2026-01-02 | Desktop | S42: second | SHAPLACEHOLDER |')
for i in 1 2 3 4 5; do printf 'c%s\n' "$i" > "$R/g$i.txt"; git -C "$R" add -A >/dev/null 2>&1; git -C "$R" commit -qm "g$i" >/dev/null 2>&1; done
newer=$(git -C "$R" rev-parse --short HEAD)
sed -i "s/SHAPLACEHOLDER/$newer/" "$R/CLAUDE_README.md"; git -C "$R" commit -qam rows >/dev/null 2>&1
mklib "$WORK/l34" 12 S42 "$base"
out=$(run "$WORK/l34" "$R"); rc=$?
assert "S109 D3: a LAGGING TIME-STATE is named as lagging, and still exits 1" 1 'TIME-STATE LAGS' "$rc" "$out"
if printf '%s' "$out" | grep -q 'FORK/REWIND'; then
  bad "S109 D3: …and is NOT called a fork" "same line of history reported as a fork — git says otherwise"
else ok "S109 D3: …and is NOT called a fork"; fi


# CASE 35 - the REGISTER COUNT class, 2026-08-27. The property: [2b]'s open-tasks count must
# see EVERY open row in OPEN-TASKS.md whatever letter its id starts with, and must NOT count
# struck rows. Violated in production for three sessions: the class was [A-F] while section J
# holds J1..J18, so the card read 94 against a file of 112. Same shape as J15 - a counter that
# reads one spelling of a marker - and it erred in the direction that flatters.
# The fixture mixes all three cases so ONE number falsifies all three at once.
R="$WORK/c35"; sha=$(mkrepo "$R" '| 2026-01-02 | Desktop | S42: second | SHAPLACEHOLDER |')
sed -i "s/SHAPLACEHOLDER/$sha/" "$R/CLAUDE_README.md"
printf '%s\r\n' '# OPEN TASKS' '' '| A1 | open a-row | x |' '| A2 | open a-row | x |' '| ~~A3~~ **STRUCK** | resolved - must NOT be counted | x |' '| B1 | open b-row | x |' '| J1 | open j-row | x |' '| J2 | open j-row | x |' '| unread-surfaces/named-open | a named ticket (S141) | open |' '| ~~services/named-struck~~ | a struck named ticket - must NOT be counted | done |' > "$R/OPEN-TASKS.md"
printf '%s\r\n' '| SYM-001 | s | c | S1 | `open` | g |' > "$R/SYMPTOM-INDEX.md"
git -C "$R" add -A >/dev/null 2>&1; git -C "$R" commit -qm reg >/dev/null 2>&1
mklib "$WORK/l35" 12 S42 "$sha"
out=$(MEMORY_LIB="$WORK/l35" FP_REPO="$R" PIPE_ROOT="$WORK/nope" VAULT_DIR="$WORK/nope" WIDGET_EXE="$WORK/nope" MUSTER_NO_REMOTE=1 bash "$OPEN" 2>&1)
if printf '%s' "$out" | grep -qE 'open-tasks +6 item\(s\)'; then
  ok "REGISTER COUNT: A-rows, B-rows, J-rows AND named ids all counted; struck excluded (6)"
else
  bad "REGISTER COUNT: open-tasks must read 6 (2 A + 1 B + 2 J + 1 named; struck A3 and the struck named id excluded)" "got: $(printf '%s' "$out" | grep -E 'open-tasks' | head -1)"
fi
# NEGATIVE CONTROL, same fixture: 8 id-bearing rows exist (S141 E11: 6 open + 2 struck, one of each named). A
# counter that ignored the strike would read 8 (or 7, ignoring one of the two strikes). So neither must appear -
# this is what stops the fix degenerating into "count every row", which would satisfy the assertion above
# for entirely the wrong reason.
if printf '%s' "$out" | grep -qE 'open-tasks +[78] item\(s\)'; then
  bad "REGISTER COUNT negative control: a struck row was counted" "read 7 or 8, so a struck id (~~A3~~ or the struck named id) was counted"
else ok "…and a struck row is never counted (never reads 7 or 8)"; fi

# CASE 36 - the ERROR BIN must be READ AT THE OPEN, 2026-08-27. The property: [2b] surfaces
# ERROR-BIN.md with a COUNT, and a MISSING one reads UNREAD rather than silence. The file's own
# section D.6 is the reason: zero of its thirteen rows name it in the 'how it was caught'
# column, so it was a diary. A register nothing forces you through is a shrine, not a spine -
# the same finding section I made about OPEN-TASKS.md at S109.
R="$WORK/c36"; sha=$(mkrepo "$R" '| 2026-01-02 | Desktop | S42: second | SHAPLACEHOLDER |')
sed -i "s/SHAPLACEHOLDER/$sha/" "$R/CLAUDE_README.md"
printf '%s\r\n' '| A1 | a | x |' > "$R/OPEN-TASKS.md"
printf '%s\r\n' '| SYM-001 | s | c | S1 | `open` | g |' > "$R/SYMPTOM-INDEX.md"
printf '%s\r\n' '# ERROR BIN' '' '| ERR-2026-01-01-001 | X | a | b | c | d |' '| ERR-2026-01-01-002 | Y | a | b | c | d |' > "$R/ERROR-BIN.md"
git -C "$R" add -A >/dev/null 2>&1; git -C "$R" commit -qm reg >/dev/null 2>&1
mklib "$WORK/l36" 12 S42 "$sha"
out=$(MEMORY_LIB="$WORK/l36" FP_REPO="$R" PIPE_ROOT="$WORK/nope" VAULT_DIR="$WORK/nope" WIDGET_EXE="$WORK/nope" MUSTER_NO_REMOTE=1 bash "$OPEN" 2>&1)
if printf '%s' "$out" | grep -qE 'error-bin +2 row\(s\)'; then
  ok "ERROR BIN: the open surfaces it with a count, so it is read at the START of a task"
else
  bad "ERROR BIN: [2b] must print 'error-bin 2 row(s)'" "got: $(printf '%s' "$out" | grep -E 'error-bin' | head -1)"
fi
# NEGATIVE CONTROL: delete it. An ABSENT register is UNREAD - never silence, and never a
# statement that nothing is open. Violating this is how a missing file reads as a clean one.
rm -f "$R/ERROR-BIN.md"; git -C "$R" add -A >/dev/null 2>&1; git -C "$R" commit -qm rm >/dev/null 2>&1
out=$(MEMORY_LIB="$WORK/l36" FP_REPO="$R" PIPE_ROOT="$WORK/nope" VAULT_DIR="$WORK/nope" WIDGET_EXE="$WORK/nope" MUSTER_NO_REMOTE=1 bash "$OPEN" 2>&1)
if printf '%s' "$out" | grep -qE 'error-bin +UNREAD'; then
  ok "…and a DELETED error bin reads UNREAD, never silence"
else
  bad "a deleted error bin must read UNREAD" "got: $(printf '%s' "$out" | grep -E 'error-bin' | head -1)"
fi

# CASE 37 - J15, THE SYMPTOM COUNTER, 2026-08-27. The property: [2b]'s open-symptom count must
# see EVERY spelling of the open marker in the STATUS COLUMN, and must NOT count a marker that
# merely appears inside another row's prose. Violated in production: the counter read only
# `` | `open` `` while the index carries 4 of those and 12 bold **OPEN**, so the card printed
# 4 against 14 - under-reporting by 3.5x, in the flattering direction, on every open for days.
# The fixture's 4th row is the control: `fixed` in the status column but **OPEN** later in the
# SAME row. A whole-line grep counts it and reads 4; a status-column-anchored one reads 3.
R="$WORK/c37"; sha=$(mkrepo "$R" '| 2026-01-02 | Desktop | S42: second | SHAPLACEHOLDER |')
sed -i "s/SHAPLACEHOLDER/$sha/" "$R/CLAUDE_README.md"
printf '%s\r\n' '| A1 | a | x |' > "$R/OPEN-TASKS.md"
printf '%s\r\n' '| SYM-001 | s | c | S1 | `open` | g |' '| SYM-002 | s | c | S1 | **OPEN** | g |' '| SYM-003 | s | c | S1 | **OPEN.** more text | g |' '| SYM-004 | s | c | S1 | `fixed` — see SYM-002 which is **OPEN** | g |' > "$R/SYMPTOM-INDEX.md"
printf '%s\r\n' '# ERROR BIN' '| ERR-2026-01-01-001 | X | a | b | c | d |' > "$R/ERROR-BIN.md"
git -C "$R" add -A >/dev/null 2>&1; git -C "$R" commit -qm sym >/dev/null 2>&1
mklib "$WORK/l37" 12 S42 "$sha"
out=$(MEMORY_LIB="$WORK/l37" FP_REPO="$R" PIPE_ROOT="$WORK/nope" VAULT_DIR="$WORK/nope" WIDGET_EXE="$WORK/nope" MUSTER_NO_REMOTE=1 bash "$OPEN" 2>&1)
if printf '%s' "$out" | grep -qE 'symptoms +4 row\(s\), 3 open'; then
  ok 'J15: both `open` and **OPEN** counted, and a prose mention is NOT (3 of 4)'
else
  bad "J15: symptoms must read '4 row(s), 3 open'" "got: $(printf '%s' "$out" | grep -E 'symptoms' | head -1)"
fi
# NEGATIVE CONTROL: reading 1 means only the backtick spelling was seen - the original bug.
# Reading 4 means a prose mention was counted - the bug a careless fix would introduce.
if printf '%s' "$out" | grep -qE 'symptoms +4 row\(s\), (1|4) open'; then
  bad "J15 negative control" "read 1 (only backticks) or 4 (counted prose) - both wrong"
else ok "…and it reads neither 1 (backticks only) nor 4 (prose counted)"; fi
# CASE 38 — SYM-071, filed S114. The property: the soft-clock hook is read off the TIME-STATE
# entry as ONE JOINED unit, so a re-wrap of "received N / given M" across two continuation lines
# — a memory-consolidation pass reflowing prose, not an edit to the count — cannot defeat the
# match. THE OLD PROXY: `grep -oE` matches PER LINE; "received" ending one line while its number
# opened the next put the phrase on two lines, and a line-wise regex cannot see across the break.
# Watched failing pre-fix: this exact fixture, against the muster.sh SYM-071 shipped with, printed
#   [2] SOFT clock ... ✗ DRIFT tally=84 hook=
# — an empty parse rendered as a fork between two records that in fact agree. Violate the same
# way; the fix must now read it as agreement.
R="$WORK/c38"; sha=$(mkrepo "$R" '| 2026-01-02 | Desktop | S42: second | SHAPLACEHOLDER |')
sed -i "s/SHAPLACEHOLDER/$sha/" "$R/CLAUDE_README.md"; git -C "$R" commit -qam rows >/dev/null 2>&1
mklib "$WORK/l38" 84 S42 "$sha" \
"> - **TIME-STATE** last session **S42**, closing SHA **$sha**, cookies
>   **received
>   84 / given 3** · 2026-01-01."
out=$(run "$WORK/l38" "$R"); rc=$?
assert "SYM-071: a hook wrapped across continuation lines still reads (tally == hook)" 0 'SOFT clock \.\.\. ✓ 84 \(tally == hook\)' "$rc" "$out"

# CASE 39 — SYM-071's second half. Rule 4 (SKILL.md): a failed probe is never a negative
# observation. An UNREADABLE hook and a REAL disagreement are different failures and must not
# share a message — the S114 defect rendered both as "DRIFT". Violate the DRIFT side first: a
# CONTIGUOUS phrase (no wrap at all — join is not the variable under test here) that simply
# disagrees with the tally.
R="$WORK/c39"; sha=$(mkrepo "$R" '| 2026-01-02 | Desktop | S42: second | SHAPLACEHOLDER |')
sed -i "s/SHAPLACEHOLDER/$sha/" "$R/CLAUDE_README.md"; git -C "$R" commit -qam rows >/dev/null 2>&1
mklib "$WORK/l39" 84 S42 "$sha" \
"> - **TIME-STATE** last session **S42**, closing SHA **$sha**, cookies
>   **received 85 / given 3** · 2026-01-01."
out=$(run "$WORK/l39" "$R"); rc=$?
assert "SYM-071: a real mismatch still fires DRIFT" 1 'DRIFT tally=84 hook=85' "$rc" "$out"
if printf '%s' "$out" | grep -q 'UNREAD'; then
  bad "…and does not say UNREAD for a real mismatch" "printed UNREAD where DRIFT was expected"
else ok "…and does not say UNREAD for a real mismatch"; fi

# NEGATIVE CONTROL for CASE 39: no 'received' phrase anywhere in the entry — the hook is
# genuinely unreadable (not merely wrapped), and this must read UNREAD, never DRIFT. Pre-fix this
# fixture printed `DRIFT tally=84 hook=` — the exact message SYM-071 names as indistinguishable
# from a real fork; UNREAD did not exist as a message at all.
mklib "$WORK/l39n" 84 S42 "$sha" \
"> - **TIME-STATE** last session **S42**, closing SHA **$sha**, cookies given 3, no count stated."
out=$(run "$WORK/l39n" "$R"); rc=$?
assert "…and no 'received' phrase at all fires UNREAD, not DRIFT" 1 'UNREAD hook unreadable' "$rc" "$out"
if printf '%s' "$out" | grep -q 'DRIFT'; then
  bad "…and does not say DRIFT when there is no hook at all" "printed DRIFT where UNREAD was expected"
else ok "…and does not say DRIFT when there is no hook at all"; fi
# S194 E1: cases 40–43 plant `S43-desktop-*.md` and open.sh names the machine from uname — off Windows the file reads as
# another machine's (a COLLISION by design), so the eight assertions are Windows-shaped: SKIPPED off it, fired on it.
# (The first cut closed the function after case 44 — the CLOSE B7 block, platform-independent — and the linux control
#  read 13 assertions unrun where 7 were typed; the count below is READ from the span by e1_fix_span.py.)
windows_cases_40_43() {
# CASE 40 — SYM-072, filed S114. The property: [3] PIN tells CONTINUITY from COLLISION by the
# file's own ⟨claimed:⟩ stamp and machine, not by the date in its name. Violate the old way: the
# fixture's ledger ends at S42, so this session is S43 and today's closeout would be
# S43-desktop-<today>.md; plant S43-desktop-2026-01-05.md (an EARLIER day, i.e. a multi-day
# session's own file, opened 01-05) carrying ⟨claimed: Fable lane · S43⟩. Pre-fix this printed
# "COLLISION — a closeout for S43 exists under a different machine/date" and exit 1, on every
# open from day two of S114 onward (observed 2026-09-03).
mkopen43() { # mkopen43 <workdir-suffix> → sets R, sha
  R="$WORK/c$1"; sha=$(mkrepo "$R" '| 2026-01-02 | Desktop | S42: second | SHAPLACEHOLDER |')
  sed -i "s/SHAPLACEHOLDER/$sha/" "$R/CLAUDE_README.md"; git -C "$R" commit -qam rows >/dev/null 2>&1
  mkdir -p "$R/sessions"; mklib "$WORK/l$1" 12 S42 "$sha"
}
runopen() { MEMORY_LIB="$WORK/l$1" FP_REPO="$R" PIPE_ROOT="$WORK/nope" VAULT_DIR="$WORK/nope" WIDGET_EXE="$WORK/nope" MUSTER_NO_REMOTE=1 bash "$OPEN" 2>&1; }
mkopen43 40
printf '# S43\n\n⟨claimed: Fable lane · occupant: t · S43 · 2026-01-05⟩\n\n## 1. Intent\n' > "$R/sessions/S43-desktop-2026-01-05.md"
out=$(runopen 40); rc=$?
assert "SYM-072: a same-machine EARLIER-day closeout with a ⟨claimed: S43⟩ stamp is OPEN, not a collision" 0 'OPEN — this session.s closeout exists: S43-desktop-2026-01-05.md \(opened 2026-01-05\)' "$rc" "$out"
if printf '%s' "$out" | grep -q 'COLLISION'; then bad "…and does not also say COLLISION" "printed COLLISION for the session's own file"
else ok "…and does not also say COLLISION"; fi

# NEGATIVE CONTROL for CASE 40: the same filename with NO ⟨claimed:⟩ stamp. A fix that trusts
# the machine+date in the NAME alone would accept this; the stamp is the evidence of continuity.
mkopen43 40n
printf '# S43\n\nno stamp here\n' > "$R/sessions/S43-desktop-2026-01-05.md"
out=$(runopen 40n); rc=$?
assert "…and the same name WITHOUT a stamp is still a COLLISION (exit 1), naming why" 1 'COLLISION — S43-desktop-2026-01-05.md \(no ⟨claimed: … S43⟩ stamp\)' "$rc" "$out"

# CASE 41 — SYM-072's second shape: a PEER-LANE record under the same number
# (S114-ledger-diag-codex.md; the S113 -fable-lane- precedent). Pre-fix: COLLISION, exit 1.
# The fix must NAME it as a lane record and exit 0.
mkopen43 41
printf '# S43 diag\n\n⟨claimed: Codex · S43 · 2026-01-06 UTC⟩\n' > "$R/sessions/S43-ledger-diag-codex.md"
out=$(runopen 41); rc=$?
assert "SYM-072: a peer-lane record ⟨claimed: Codex · S43⟩ is a named LANE RECORD (exit 0)" 0 'LANE RECORD — S43-ledger-diag-codex.md ' "$rc" "$out"

# CASE 42 — the guard must still FIRE on a genuine collision, or cases 40/41 pass by always
# saying yes. A closeout for S43 on ANOTHER machine, stamp and all: exit 1.
mkopen43 42
printf '# S43\n\n⟨claimed: Fable lane · S43 · 2026-01-05⟩\n' > "$R/sessions/S43-thinkpad-2026-01-05.md"
out=$(runopen 42); rc=$?
assert "SYM-072: a closeout for S43 on another machine, STAMP AND ALL, is still a COLLISION (exit 1)" 1 'COLLISION — S43-thinkpad-2026-01-05.md \(another machine.s closeout\)' "$rc" "$out"
# …and a stamp for the WRONG number does not count as this session's: S430 is not S43.
mkopen43 42b
printf '# S430\n\n⟨claimed: Fable lane · S430 · 2026-01-05⟩\n' > "$R/sessions/S43-desktop-2026-01-05.md"
out=$(runopen 42b); rc=$?
assert "…and a ⟨claimed: S430⟩ stamp does not satisfy S43 (prefix is not identity)" 1 'COLLISION — S43-desktop-2026-01-05.md \(no ⟨claimed: … S43⟩ stamp\)' "$rc" "$out"

# CASE 43 — fleet wf_1e69e60b-b45 lane C (2026-09-04). The property: the DELIMITED ⟨claimed:⟩ stamp
# decides, not the first line that happens to contain the word 'claimed:'. Violate: a closeout whose
# first 'claimed:' occurrence is PROSE quoting another session ("the S42 record said claimed: …") and
# whose real delimited stamp names S43 further down. Pre-fix (bare-word grep -m1) read the prose line,
# found no S43, and called the session's own file a COLLISION.
mkopen43 43
printf '# S43\n\nthe S42 record said claimed: Fable lane · S42, which is not this file.\n\n⟨claimed: Fable lane · occupant: t · S43 · 2026-01-05⟩\n' > "$R/sessions/S43-desktop-2026-01-05.md"
out=$(runopen 43); rc=$?
assert "SYM-072: a prose 'claimed:' quoting S42 before the real ⟨claimed: … S43⟩ stamp still reads OPEN" 0 'OPEN — this session.s closeout exists: S43-desktop-2026-01-05.md' "$rc" "$out"
# NEGATIVE CONTROL: the bare word alone, with NO delimited stamp anywhere, is not continuity.
mkopen43 43n
printf '# S43\n\nclaimed: Fable lane · S43 · 2026-01-05 (no delimiters)\n' > "$R/sessions/S43-desktop-2026-01-05.md"
out=$(runopen 43n); rc=$?
assert "…and a bare 'claimed: … S43' with no ⟨ ⟩ delimiters is still a COLLISION (no stamp)" 1 'COLLISION — S43-desktop-2026-01-05.md \(no ⟨claimed: … S43⟩ stamp\)' "$rc" "$out"

}
if on_windows; then windows_cases_40_43; else skip "CASES 40–43 (SYM-072): the fixture's S43-desktop-*.md reads as another machine's off Windows" "platform $(uname -s 2>/dev/null) (MUSTER_SELFTEST_PLATFORM=${MUSTER_SELFTEST_PLATFORM:-unset})" 8; fi
# ── CASE 44: close.sh DIFF, B7 (S120) — attribute every dirty tracked file to a writer ───────
# Two lanes (Fable/Codex) share one checkout. Pre-fix, close.sh's [1] DIFF counted EVERY tracked
# change as this lane's ("dirty = every tracked change; dirty > 0 -> red"), so a Fable close went
# red on bytes that are not Fable's to commit — Codex keeps its own sidecar and session files
# uncommitted by its own word (MSG-CDX-0048: "do not absorb either file into a Fable close
# commit"), and S119 closed exit 1 for exactly this. The fix must attribute each dirty tracked
# file to FP_LANE or its peer and red ONLY on this lane's own; peer-owned files are STATED on
# the row, never silent, never absorbed. A relay.md hunk is peer-owned only when it is PURELY
# append-only (no "-" lines) and EVERY added "## " header reads "⟨from: <peer>⟩" — a hunk mixing
# both writers' headers is MINE (shared), and the row must name the remedy (gate.py stage).
CLOSE="$HERE/close.sh"
B7="$WORK/b7"; mkdir -p "$B7/coordination"
git -C "$B7" init -q 2>/dev/null
git -C "$B7" config user.email t@t; git -C "$B7" config user.name t
printf 'base\n' > "$B7/f.txt"
printf '## 2026-01-01T00:00Z · ⟨from: Fable⟩ → ⟨to: Codex⟩ · ⟨msg: MSG-FAB-0001⟩\nbody\n' > "$B7/coordination/relay.md"
printf 'fable\n' > "$B7/coordination/ack-fable.json"
printf 'codex\n' > "$B7/coordination/ack-codex.json"
git -C "$B7" add -A >/dev/null 2>&1
git -C "$B7" commit -qm base >/dev/null 2>&1
B7PIN=$(git -C "$B7" rev-parse HEAD)

# 44a — POSITIVE CONTROL: only a peer-owned tracked file (Codex's sidecar) dirty must NOT force
# red — the DIFF row is not the thing forcing it red (docs/47 negative-control law).
printf 'fable\nmore\n' >> "$B7/coordination/ack-codex.json"
out=$(FP_REPO="$B7" FP_PY="/no/such/python.exe" bash "$CLOSE" "$B7PIN" 2>&1); rc=$?
assert "CLOSE B7a: only a peer-owned dirty tracked file does not force red" 0 'DIFF .*dirty 1 = mine 0 · peer-owned 1 \(coordination/ack-codex\.json\)' "$rc" "$out"
git -C "$B7" checkout -q -- coordination/ack-codex.json

# 44b — NEGATIVE CONTROL: a Fable-written tracked file dirty (no lane name in its path) must
# still red — the attribution fix must not become a blanket "never red".
printf 'base\nfable edit\n' > "$B7/f.txt"
out=$(FP_REPO="$B7" FP_PY="/no/such/python.exe" bash "$CLOSE" "$B7PIN" 2>&1); rc=$?
assert "CLOSE B7b: a lane's own dirty tracked file forces red" 1 'DIFF .*dirty 1 = mine 1' "$rc" "$out"
git -C "$B7" checkout -q -- f.txt

# 44c — a relay.md hunk carrying a Fable header (this lane's own append) is MINE, red.
printf '## 2026-01-01T02:00Z · ⟨from: Fable⟩ → ⟨to: Codex⟩ · ⟨msg: MSG-FAB-0002⟩\nbody3\n' >> "$B7/coordination/relay.md"
out=$(FP_REPO="$B7" FP_PY="/no/such/python.exe" bash "$CLOSE" "$B7PIN" 2>&1); rc=$?
assert "CLOSE B7c: a relay.md hunk carrying a Fable header is MINE, red" 1 'DIFF .*dirty 1 = mine 1 · peer-owned 0' "$rc" "$out"
git -C "$B7" checkout -q -- coordination/relay.md

# 44d — a relay.md hunk with ONLY Codex headers (pure append-only, no "-" lines) is peer-owned,
# not red — the mirror of 44c, so 44c cannot pass by always calling relay.md MINE.
printf '## 2026-01-01T01:00Z · ⟨from: Codex⟩ → ⟨to: Fable⟩ · ⟨msg: MSG-CDX-0001⟩\nbody2\n' >> "$B7/coordination/relay.md"
out=$(FP_REPO="$B7" FP_PY="/no/such/python.exe" bash "$CLOSE" "$B7PIN" 2>&1); rc=$?
assert "CLOSE B7d: a relay.md hunk with only Codex headers is peer-owned, not red" 0 'DIFF .*dirty 1 = mine 0 · peer-owned 1 \(coordination/relay\.md\)' "$rc" "$out"
git -C "$B7" checkout -q -- coordination/relay.md

# 44e — a MIXED relay.md hunk (headers from BOTH writers) is MINE, red, and the row names the
# remedy — the case a pure-append rule alone could not tell from 44d.
printf '## 2026-01-01T03:00Z · ⟨from: Codex⟩ → ⟨to: Fable⟩ · ⟨msg: MSG-CDX-0002⟩\nbody4\n## 2026-01-01T04:00Z · ⟨from: Fable⟩ → ⟨to: Codex⟩ · ⟨msg: MSG-FAB-0003⟩\nbody5\n' >> "$B7/coordination/relay.md"
out=$(FP_REPO="$B7" FP_PY="/no/such/python.exe" bash "$CLOSE" "$B7PIN" 2>&1); rc=$?
assert "CLOSE B7e: a MIXED relay.md hunk (both writers) is MINE, red" 1 'DIFF .*dirty 1 = mine 1 · peer-owned 0' "$rc" "$out"
assert "CLOSE B7e: the row names the shared-hunk remedy (gate.py stage)" 1 'shared hunk — run gate\.py stage --as Fable' "$rc" "$out"
git -C "$B7" checkout -q -- coordination/relay.md

# CASE 45 — J57 (Rab, signed 2026-09-10, S125). The property: the `widget autostart` row is a READING of the
# scheduled task, never a remembered fact. Violate twice: (a) a powershell probe that FAILS must render UNREAD,
# never ABSENT (the failed-probe rule, case 7's shape); (b) a probe that answers must be read back as its state.
R="$WORK/c45"; sha=$(mkrepo "$R" '| 2026-01-01 | Desktop | S41: first | 1111111 |' '| 2026-01-02 | Desktop | S42: second | SHAPLACEHOLDER |')
sed -i "s/SHAPLACEHOLDER/$sha/" "$R/CLAUDE_README.md"
git -C "$R" add -A >/dev/null 2>&1; git -C "$R" commit -qm c45 >/dev/null 2>&1
mklib "$WORK/l45" 12 S42 "$sha"
# S194 E1: the `widget autostart` row is a desktop-only powershell probe (open.sh prints it for machine=desktop) — the five
# assertions of cases 45–46 are Windows-shaped: SKIPPED off it, fired on it. The c45 fixture above stays: case 47 reads it.
windows_cases_45_46() {
mkdir -p "$WORK/fakeps45a"; printf '#!/bin/sh\nexit 9\n' > "$WORK/fakeps45a/ps.sh"; chmod +x "$WORK/fakeps45a/ps.sh"
out=$(FP_PS_EXE="$WORK/fakeps45a/ps.sh" MEMORY_LIB="$WORK/l45" FP_REPO="$R" PIPE_ROOT="$WORK/nope" \
      VAULT_DIR="$WORK/nope" WIDGET_EXE="$WORK/nope" MUSTER_NO_REMOTE=1 bash "$OPEN" 2>&1)
if printf '%s' "$out" | grep -qE 'widget autostart +UNREAD'; then ok "J57: a FAILED task probe renders UNREAD, never ABSENT"
else bad "J57: a FAILED task probe renders UNREAD" "got: $(printf '%s' "$out" | grep -E 'widget autostart' | head -1)"; fi
mkdir -p "$WORK/fakeps45b"; printf '#!/bin/sh\necho STATE=Disabled\n' > "$WORK/fakeps45b/ps.sh"; chmod +x "$WORK/fakeps45b/ps.sh"
out=$(FP_PS_EXE="$WORK/fakeps45b/ps.sh" MEMORY_LIB="$WORK/l45" FP_REPO="$R" PIPE_ROOT="$WORK/nope" \
      VAULT_DIR="$WORK/nope" WIDGET_EXE="$WORK/nope" MUSTER_NO_REMOTE=1 bash "$OPEN" 2>&1)
if printf '%s' "$out" | grep -qE "widget autostart +task 'File Portal widget \(J57\)' Disabled"; then ok "J57: the task's STATE is read back verbatim (Disabled is not present)"
else bad "J57: the task's STATE is read back verbatim" "got: $(printf '%s' "$out" | grep -E 'widget autostart' | head -1)"; fi
# CASE 46 — S127 (Rab: "auto-logon to finish J57"). The property: the auto-logon half is a READING of the registry
# beside the task, never assumed from the task's presence. (a) a probe that answers the task but not the auto-logon
# field renders `auto-logon UNREAD` (the fake above prints no AUTOLOGON line); (b) AUTOLOGON=1 reads ON with the user;
# (c) an empty AUTOLOGON reads OFF and names the hand that remains.
if printf '%s' "$out" | grep -qE "auto-logon UNREAD"; then ok "J62: no AUTOLOGON line from the probe renders auto-logon UNREAD, never OFF"
else bad "J62: a missing AUTOLOGON line renders UNREAD" "got: $(printf '%s' "$out" | grep -E 'widget autostart' | head -1)"; fi
mkdir -p "$WORK/fakeps46b"; printf '#!/bin/sh\necho STATE=Ready\necho "AUTOLOGON=1 USER=Bndit"\n' > "$WORK/fakeps46b/ps.sh"; chmod +x "$WORK/fakeps46b/ps.sh"
out=$(FP_PS_EXE="$WORK/fakeps46b/ps.sh" MEMORY_LIB="$WORK/l45" FP_REPO="$R" PIPE_ROOT="$WORK/nope" \
      VAULT_DIR="$WORK/nope" WIDGET_EXE="$WORK/nope" MUSTER_NO_REMOTE=1 bash "$OPEN" 2>&1)
if printf '%s' "$out" | grep -qE "auto-logon ON \(Bndit\)"; then ok "J62: AUTOLOGON=1 reads ON with the user named"
else bad "J62: AUTOLOGON=1 reads ON" "got: $(printf '%s' "$out" | grep -E 'widget autostart' | head -1)"; fi
mkdir -p "$WORK/fakeps46c"; printf '#!/bin/sh\necho STATE=Ready\necho "AUTOLOGON= USER="\n' > "$WORK/fakeps46c/ps.sh"; chmod +x "$WORK/fakeps46c/ps.sh"
out=$(FP_PS_EXE="$WORK/fakeps46c/ps.sh" MEMORY_LIB="$WORK/l45" FP_REPO="$R" PIPE_ROOT="$WORK/nope" \
      VAULT_DIR="$WORK/nope" WIDGET_EXE="$WORK/nope" MUSTER_NO_REMOTE=1 bash "$OPEN" 2>&1)
if printf '%s' "$out" | grep -qE "auto-logon OFF"; then ok "J62: an empty AUTOLOGON reads OFF (the hand that remains, named)"
else bad "J62: an empty AUTOLOGON reads OFF" "got: $(printf '%s' "$out" | grep -E 'widget autostart' | head -1)"; fi
}
if on_windows; then windows_cases_45_46; else skip "CASES 45–46 (J57/J62): the widget-autostart row is a desktop-only powershell probe, absent off Windows" "platform $(uname -s 2>/dev/null) (MUSTER_SELFTEST_PLATFORM=${MUSTER_SELFTEST_PLATFORM:-unset})" 5; fi

# CASE 47 — J63 (S127). The property: the open PUBLISHES the session number for the hooks. After open.sh on the c45
# fixture (Desktop rows S41, S42 → this session S43), coordination/private/session.current must hold `S43`, and the
# card must NAME the marker. Violate the absence: remove the marker first, run the open, read it back.
mkdir -p "$R/coordination"; rm -f "$R/coordination/private/session.current"  # a File Portal-shaped fixture (the guards exempt a root without coordination/)
out=$(FP_PS_EXE="$WORK/fakeps46c/ps.sh" MEMORY_LIB="$WORK/l45" FP_REPO="$R" PIPE_ROOT="$WORK/nope" \
      VAULT_DIR="$WORK/nope" WIDGET_EXE="$WORK/nope" MUSTER_NO_REMOTE=1 bash "$OPEN" 2>&1)
if [[ -f "$R/coordination/private/session.current" ]] && head -c 4 "$R/coordination/private/session.current" | grep -q '^S43'; then ok "J63: the open writes coordination/private/session.current = S43"
else bad "J63: the open writes the session marker" "got: $(cat "$R/coordination/private/session.current" 2>/dev/null || echo '(absent)')"; fi
if printf '%s' "$out" | grep -qE 'session marker +coordination/private/session.current = S43'; then ok "J63: the card names the marker it wrote"
else bad "J63: the card names the marker" "got: $(printf '%s' "$out" | grep -E 'session marker' | head -1)"; fi


# CASE 48–52 — J69 (S132). The property: the ledger row is validated by ITS READER before the push. S130's three-cell
# row opened a mock muster on an INCIDENT (SYM-113); S131's hand-check then gated on the clocks, which cannot agree before
# the memory lockstep. row_check.sh parses with [3b]'s own awk and checks the SHA against the repo — nothing else.
ROWCHECK="$(dirname "$MUSTER")/row_check.sh"
addrow() { # addrow <dir> <row> → commits the appended row, echoes HEAD sha
  printf '%s\n' "$2" >> "$1/CLAUDE_README.md"; git -C "$1" add -A >/dev/null 2>&1; git -C "$1" commit -qm row >/dev/null 2>&1; git -C "$1" rev-parse --short HEAD
}
# 48 — POSITIVE CONTROL: a proper five-cell row whose SHA is the fixture's own earlier commit → exit 0.
R="$WORK/c48"; s1=$(mkrepo "$R" '| 2026-01-01 | Desktop | S41: first | one file | 1111111 |')
addrow "$R" "| 2026-01-02 | Desktop | S42: the close. Closeout: sessions/S42.md | two files | $s1 |" >/dev/null
out=$(FP_REPO="$R" bash "$ROWCHECK" 42 2>&1); rc=$?
assert "J69 CONTROL: a five-cell S42 row naming a real ancestor passes (exit 0)" 0 'ROW OK — S42' "$rc" "$out"
# 49 — S130's shape: three cells, the SHA inside the prose → exit 1 naming no-sha.
R="$WORK/c49"; s1=$(mkrepo "$R" '| 2026-01-01 | Desktop | S41: first | one file | 1111111 |')
addrow "$R" "| 2026-01-02 | Desktop | S42: the close, SHA $s1 in the prose, no cell. |" >/dev/null
out=$(FP_REPO="$R" bash "$ROWCHECK" 42 2>&1); rc=$?
assert "J69: a three-cell row with the SHA in prose fires, naming no-sha (S130's row)" 1 'UNPARSED ROW.*no-sha' "$rc" "$out"
# 50 — five cells but a SHA that is no commit here (a typo) → exit 1.
R="$WORK/c50"; s1=$(mkrepo "$R" '| 2026-01-01 | Desktop | S41: first | one file | 1111111 |')
addrow "$R" "| 2026-01-02 | Desktop | S42: the close | two files | deadbee |" >/dev/null
out=$(FP_REPO="$R" bash "$ROWCHECK" 42 2>&1); rc=$?
assert "J69: a well-formed row whose SHA is not a commit here fires" 1 'not a commit' "$rc" "$out"
# 51 — ONE GRAMMAR, TWO DOORS: row_check.sh's awk must be byte-identical to muster.sh [3b]'s.
a=$(tr -d '\r' < "$MUSTER"   | sed -n "/awk -F'|' -v lane=\"\$LANE\" '/,/^  END { print \"rows\", NR }')/p" | sed '1d;$d')
b=$(tr -d '\r' < "$ROWCHECK" | sed -n "/awk -F'|' -v lane=\"\$LANE\" '/,/^  END { print \"rows\", NR }')/p" | sed '1d;$d')
if [[ -n "$a" && "$a" == "$b" ]]; then ok "J69: row_check.sh's awk is byte-identical to muster.sh [3b]'s ($(printf '%s\n' "$a" | wc -l | tr -d ' ') lines)"
else bad "J69: row_check.sh's awk drifted from muster.sh [3b]'s" "$(diff <(printf '%s\n' "$a") <(printf '%s\n' "$b") | head -3)"; fi
# 52 — the row that was never written: the newest row is S42, the session says 43 → exit 1 naming both.
out=$(FP_REPO="$WORK/c48" bash "$ROWCHECK" 43 2>&1); rc=$?
assert "J69: an absent S43 row fires, naming the S42 it found instead" 1 'newest Desktop row is S42.*expected S43' "$rc" "$out"

# CASE 53–56 — the review fleet's findings on J69 (wf_39d7d910-024, S132), each a case FIRST.
# 53 — the real ledger is CRLF; every fixture above is LF. The same fixture as 48, CRLF-terminated → still exit 0.
R="$WORK/c53"; s1=$(mkrepo "$R" '| 2026-01-01 | Desktop | S41: first | one file | 1111111 |')
addrow "$R" "| 2026-01-02 | Desktop | S42: the close | two files | $s1 |" >/dev/null
sed -i 's/$/\r/' "$R/CLAUDE_README.md"
out=$(FP_REPO="$R" bash "$ROWCHECK" 42 2>&1); rc=$?
assert "J69: a CRLF ledger (the real one's shape) still passes" 0 'ROW OK — S42' "$rc" "$out"
# 54 — a REAL commit that is NOT an ancestor of HEAD (a sibling branch): exists, so cat-file passes; merge-base must fire.
R="$WORK/c54"; s1=$(mkrepo "$R" '| 2026-01-01 | Desktop | S41: first | one file | 1111111 |')
git -C "$R" checkout -q -b sibling; printf 'x\n' > "$R/x"; git -C "$R" add -A >/dev/null 2>&1; git -C "$R" commit -qm sibling >/dev/null 2>&1; sib=$(git -C "$R" rev-parse --short HEAD)
git -C "$R" checkout -q - 2>/dev/null || git -C "$R" checkout -q master 2>/dev/null || git -C "$R" checkout -q main
addrow "$R" "| 2026-01-02 | Desktop | S42: the close | two files | $sib |" >/dev/null
out=$(FP_REPO="$R" bash "$ROWCHECK" 42 2>&1); rc=$?
assert "J69: a real commit that is NOT an ancestor of HEAD fires (a sibling branch's SHA)" 1 'not an ancestor of HEAD' "$rc" "$out"
# 55 — exit 2 is CONFIG, never a verdict: no argument; a non-git FP_REPO. (assert() knows 0/1; exit 2 is checked by hand.)
out=$(FP_REPO="$WORK/c48" bash "$ROWCHECK" 2>&1); rc=$?
if [[ "$rc" -eq 2 ]] && printf '%s' "$out" | grep -q 'usage'; then ok "J69: no argument is usage (exit 2), not a verdict"; else bad "J69: no argument is usage (exit 2)" "got exit $rc: $out"; fi
mkdir -p "$WORK/c55notgit"; printf '| 2026-01-01 | Desktop | S41: x | y | 1111111 |\n' > "$WORK/c55notgit/CLAUDE_README.md"
out=$(FP_REPO="$WORK/c55notgit" bash "$ROWCHECK" 41 2>&1); rc=$?
if [[ "$rc" -eq 2 ]] && printf '%s' "$out" | grep -q 'CONFIG'; then ok "J69: a non-git FP_REPO is CONFIG (exit 2), not a verdict"; else bad "J69: a non-git FP_REPO is CONFIG (exit 2)" "got exit $rc: $out"; fi
# 56 — a duplicate row for one session is a red (the reader's tie-break would pick by hex order); and no lane row at all.
R="$WORK/c56"; s1=$(mkrepo "$R" '| 2026-01-01 | Desktop | S41: first | one file | 1111111 |')
s2=$(addrow "$R" "| 2026-01-02 | Desktop | S42: first write | two files | $s1 |")
addrow "$R" "| 2026-01-02 | Desktop | S42: second write | two files | $s2 |" >/dev/null
out=$(FP_REPO="$R" bash "$ROWCHECK" 42 2>&1); rc=$?
assert "J69: two rows for one session fire, naming both" 1 'TWO rows for S42' "$rc" "$out"
R="$WORK/c56b"; mkrepo "$R" '| 2026-01-01 | ThinkPad | S41: first | one file | 1111111 |' >/dev/null
out=$(FP_REPO="$R" bash "$ROWCHECK" 41 2>&1); rc=$?
assert "J69: a ledger with no Desktop row at all fires, saying so" 1 'no parsed Desktop row' "$rc" "$out"

# CASE 57 — S141 (unread-surfaces/watcher-stuck-drop-file). The property: the card's `intake` row is the WATCHER'S receipt
# read back, never a mtime guess. (a) no receipt renders UNREAD, never "0 waiting"; (b) a PDF waiting > 1 h with no active
# convert renders STUCK; (c) a receipt older than 60 s renders STALE (the loop rewrites it every poll).
R="$WORK/c57"; sha=$(mkrepo "$R" '| 2026-01-01 | Desktop | S41: first | 1111111 |' '| 2026-01-02 | Desktop | S42: second | SHAPLACEHOLDER |')
sed -i "s/SHAPLACEHOLDER/$sha/" "$R/CLAUDE_README.md"
git -C "$R" add -A >/dev/null 2>&1; git -C "$R" commit -qm c57 >/dev/null 2>&1
mklib "$WORK/l57" 12 S42 "$sha"
P57="$WORK/pipe57"; mkdir -p "$P57/drop"
out=$(MEMORY_LIB="$WORK/l57" FP_REPO="$R" PIPE_ROOT="$P57" VAULT_DIR="$WORK/nope" WIDGET_EXE="$WORK/nope" MUSTER_NO_REMOTE=1 bash "$OPEN" 2>&1)
if printf '%s' "$out" | grep -qE 'intake +UNREAD'; then ok "S141 intake: no receipt renders UNREAD, never a count"
else bad "S141 intake: no receipt renders UNREAD" "got: $(printf '%s' "$out" | grep -E '^ +intake' | head -1)"; fi
now57=$(date -u +%Y-%m-%dT%H:%M:%S.000Z)
printf '{"v":1,"writer_pid":4242,"written_at":"%s","wake_mode":"reconcile","card_state":"idle","active":null,"waiting":1,"items":[{"name":"old.pdf","bytes":1,"mtime_ns":1,"phase":"ready","first_seen_at":"2026-01-01T00:00:00Z","wait_s":7200,"quiet_s":5.0}]}\n' "$now57" > "$P57/.intake-state.json"
out=$(MEMORY_LIB="$WORK/l57" FP_REPO="$R" PIPE_ROOT="$P57" VAULT_DIR="$WORK/nope" WIDGET_EXE="$WORK/nope" MUSTER_NO_REMOTE=1 bash "$OPEN" 2>&1)
if printf '%s' "$out" | grep -E '^ +intake' | grep -q 'STUCK' && printf '%s' "$out" | grep -E '^ +intake' | grep -q 'waiting 1 · oldest 7200s'; then ok "S141 intake: a PDF waiting > 1 h with no active convert renders STUCK, with the numbers"
else bad "S141 intake: waiting > 1 h renders STUCK" "got: $(printf '%s' "$out" | grep -E '^ +intake' | head -1)"; fi
if printf '%s' "$out" | grep -E '^ +intake' | grep -q 'STALE'; then bad "S141 intake: a fresh receipt must NOT read STALE" "got: $(printf '%s' "$out" | grep -E '^ +intake' | head -1)"
else ok "S141 intake: a fresh receipt does not read STALE (negative control)"; fi
printf '{"v":1,"writer_pid":4242,"written_at":"2026-01-01T00:00:00.000Z","wake_mode":"reconcile","card_state":"idle","active":null,"waiting":0,"items":[]}\n' > "$P57/.intake-state.json"
out=$(MEMORY_LIB="$WORK/l57" FP_REPO="$R" PIPE_ROOT="$P57" VAULT_DIR="$WORK/nope" WIDGET_EXE="$WORK/nope" MUSTER_NO_REMOTE=1 bash "$OPEN" 2>&1)
if printf '%s' "$out" | grep -E '^ +intake' | grep -q 'STALE'; then ok "S141 intake: a receipt older than 60 s renders STALE (the watcher rewrites it every poll)"
else bad "S141 intake: an old receipt renders STALE" "got: $(printf '%s' "$out" | grep -E '^ +intake' | head -1)"; fi

# CASE 37 — J36 (S157 E12), THE ADOPTION RECEIPT. The property: the card compares the newest adopted receipt to the
# exe it measured. Violate three ways: (a) a receipt that matches a planted exe must read MATCH; (b) a receipt naming a
# different hash must read DRIFT (the guard must be able to shout); (c) no receipt file must read UNREAD, never "no
# adoption" and never MATCH.
printf 'planted widget bytes\n' > "$WORK/fake.exe"
fake8=$(sha256sum "$WORK/fake.exe" | cut -c1-8 | tr 'a-f' 'A-F')
mkdir -p "$R/coordination"
printf '{"ts": "2026-09-15T07:00:00Z", "state": "adopted", "sha8": "%s", "by": "rab", "evidence": "fixture"}\n' "$fake8" > "$R/coordination/adoptions.jsonl"
out=$(MEMORY_LIB="$WORK/l6" FP_REPO="$R" PIPE_ROOT="$WORK/nope" VAULT_DIR="$WORK/nope" WIDGET_EXE="$WORK/fake.exe" MUSTER_NO_REMOTE=1 bash "$OPEN" 2>&1)
if printf '%s' "$out" | grep -qE "adoption +$fake8 .*installed $fake8 — MATCH"; then ok "J36 (a): a receipt matching the installed exe reads MATCH"
else bad "J36 (a): MATCH" "got: $(printf '%s' "$out" | grep -E '^ +adoption' | head -1)"; fi
printf '{"ts": "2026-09-15T07:00:00Z", "state": "adopted", "sha8": "DEADBEEF", "by": "rab", "evidence": "fixture"}\n' > "$R/coordination/adoptions.jsonl"
out=$(MEMORY_LIB="$WORK/l6" FP_REPO="$R" PIPE_ROOT="$WORK/nope" VAULT_DIR="$WORK/nope" WIDGET_EXE="$WORK/fake.exe" MUSTER_NO_REMOTE=1 bash "$OPEN" 2>&1)
if printf '%s' "$out" | grep -qE "adoption +DEADBEEF .*installed $fake8 — \*\*\* DRIFT"; then ok "J36 (b): a receipt naming another hash reads DRIFT"
else bad "J36 (b): DRIFT" "got: $(printf '%s' "$out" | grep -E '^ +adoption' | head -1)"; fi
rm -f "$R/coordination/adoptions.jsonl"
out=$(MEMORY_LIB="$WORK/l6" FP_REPO="$R" PIPE_ROOT="$WORK/nope" VAULT_DIR="$WORK/nope" WIDGET_EXE="$WORK/fake.exe" MUSTER_NO_REMOTE=1 bash "$OPEN" 2>&1)
if printf '%s' "$out" | grep -qE 'adoption +UNREAD' && ! printf '%s' "$out" | grep -qE 'adoption +.*MATCH'; then ok "J36 (c): no receipt file reads UNREAD, never MATCH"
else bad "J36 (c): UNREAD" "got: $(printf '%s' "$out" | grep -E '^ +adoption' | head -1)"; fi

# ── CASES 53–54: B33 (S157 E42) — the two S111 close-gate evidence boundaries ────────────────
# CASE 53 — SYM-064. The property: an INTERACTIVE credential helper cannot hang the close. Violate: a fixture repo whose
# credential.helper sleeps past the bound; close.sh must return inside FP_CRED_TIMEOUT_S and say the lookup did not return.
# The global helper (the stored credential) is shut out with GIT_CONFIG_GLOBAL=/dev/null, else it answers before the fixture's.
# Negative control: with the same fixture and a helper that answers at once, the row does NOT claim a hang.
B33=$(mktemp -d "$WORK/b33.XXXX"); git -C "$B33" init -q; git -C "$B33" config user.email t@t; git -C "$B33" config user.name t
printf 'x\n' > "$B33/f"; git -C "$B33" add f; git -C "$B33" commit -q -m one
git -C "$B33" config credential.helper '!f() { sleep 30; }; f'
t0=$(date +%s)
out=$(GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 FP_PY="/no/such/python.exe" FP_CRED_TIMEOUT_S=2 MEMORY_LIB="$WORK/l6" FP_REPO="$B33" bash "$CLOSE" HEAD 2>&1)
dt=$(( $(date +%s) - t0 ))
if printf '%s' "$out" | grep -qE 'CI +UNREAD — the credential lookup did not return in 2s' && [ "$dt" -lt 20 ]; then ok "B33 (SYM-064): a blocking credential helper is BOUNDED — the close returns in ${dt}s and names the hang as UNREAD"
else bad "B33 (SYM-064): a blocking helper must be bounded and named" "took ${dt}s; got: $(printf '%s' "$out" | grep -E '^ +CI' | head -1)"; fi
git -C "$B33" config credential.helper '!f() { echo password=; }; f'
out=$(GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 FP_PY="/no/such/python.exe" FP_CRED_TIMEOUT_S=2 MEMORY_LIB="$WORK/l6" FP_REPO="$B33" bash "$CLOSE" HEAD 2>&1)
if printf '%s' "$out" | grep -qE 'CI +UNREAD — no stored credential'; then ok "B33 NEGATIVE CONTROL: a helper that answers at once is not called a hang"
else bad "B33 NEGATIVE CONTROL: a prompt helper must not read as a hang" "got: $(printf '%s' "$out" | grep -E '^ +CI' | head -1)"; fi

# CASE 54 — SYM-063. The property: git REFUSING the memory library over ownership reads as ownership, not as "not a git
# repo". Violate: a git shim on PATH that answers `dubious ownership` for one path and delegates everything else to the
# real git. Negative control: the same shim with a plain non-repo path — the row must still read "not a git repo".
REALGIT=$(command -v git); mkdir -p "$WORK/fakebin54"
printf '#!/bin/sh\nfor a in "$@"; do case "$a" in *l54dubious*) echo "fatal: detected dubious ownership in repository at '"'"'$a'"'"'" >&2; exit 128;; esac; done\nexec "%s" "$@"\n' "$REALGIT" > "$WORK/fakebin54/git"
chmod +x "$WORK/fakebin54/git"; mkdir -p "$WORK/l54dubious" "$WORK/l54plain"
out=$(PATH="$WORK/fakebin54:$PATH" FP_PY="/no/such/python.exe" FP_CRED_TIMEOUT_S=2 MEMORY_LIB="$WORK/l54dubious" FP_REPO="$B33" bash "$CLOSE" HEAD 2>&1)
if printf '%s' "$out" | grep -qE 'MEMORY +UNREAD — git REFUSES the memory library \(ownership'; then ok "B33 (SYM-063): a dubious-ownership refusal is named as ownership, still UNREAD"
else bad "B33 (SYM-063): ownership refusal must be named" "got: $(printf '%s' "$out" | grep -E '^ +MEMORY' | head -1)"; fi
out=$(PATH="$WORK/fakebin54:$PATH" FP_PY="/no/such/python.exe" FP_CRED_TIMEOUT_S=2 MEMORY_LIB="$WORK/l54plain" FP_REPO="$B33" bash "$CLOSE" HEAD 2>&1)
if printf '%s' "$out" | grep -qE 'MEMORY +UNREAD — memory library is not a git repo'; then ok "B33 NEGATIVE CONTROL: a plain non-repo still reads 'not a git repo'"
else bad "B33 NEGATIVE CONTROL: a non-repo must not read as ownership" "got: $(printf '%s' "$out" | grep -E '^ +MEMORY' | head -1)"; fi

# CASE E60a/E60b — S157 E60 (the E47 Circle's recommendation). The property: a row corrupted BEYOND the tail — which
# the push gate (J71) never reads — is visible at the open as a discard count that MOVED against the ledger's own
# close. Fixture: commit Z (an empty README — the close every row names; its blob holds no rows, so the count at
# the close is a clean 0), then seven rows all naming Z. Violate: row 1 loses its SHA cell in the working tree —
# beyond the tail of 5, so [3b]'s tail alarm stays silent by design; the reading must say "+1 — an OLDER row
# changed since the close" and the exit must STAY 0 (a reading, never a verdict). Control first: untouched → "unchanged".
R="$WORK/c57"; mkdir -p "$R"; git -C "$R" init -q 2>/dev/null
git -C "$R" config user.email t@t; git -C "$R" config user.name t
printf '# CLAUDE_README\n' > "$R/CLAUDE_README.md"
git -C "$R" add -A >/dev/null 2>&1; git -C "$R" commit -qm 'Z: the close every row names' >/dev/null 2>&1
z57=$(git -C "$R" rev-parse --short HEAD)
{ printf '# CLAUDE_README\n\n## Change Ledger\n\n| Date | Machine | Milestone | SHA |\n|---|---|---|---|\n'
  for n in 1 2 3 4 5 6 7; do printf '| 2026-01-%02d | Desktop | S%s: row | %s |\n' "$n" "$((40 + n))" "$z57"; done; } > "$R/CLAUDE_README.md"
git -C "$R" add -A >/dev/null 2>&1; git -C "$R" commit -qm 'seven rows, all naming Z' >/dev/null 2>&1
mklib "$WORK/l57" 12 S47 "$z57"
out=$(run "$WORK/l57" "$R"); rc=$?
if printf '%s' "$out" | grep -qE '\[3b\] LEDGER PARSE.*unchanged since the close'; then ok "CASE E60b NEGATIVE CONTROL: an untouched ledger reads 'unchanged since the close'"
else bad "CASE E60b NEGATIVE CONTROL: must read 'unchanged since the close'" "got: $(printf '%s' "$out" | grep -E '^\[3b\]' | head -1)"; fi
sed -i "s/| S41: row | $z57 |/| S41: row | |/" "$R/CLAUDE_README.md"
out=$(run "$WORK/l57" "$R"); rc=$?
if printf '%s' "$out" | grep -qE '\[3b\] LEDGER PARSE.*\+1 — an OLDER row changed since the close'; then ok "CASE E60a: an OLDER row corrupted after the close moves the discard count (+1) at the open"
else bad "CASE E60a: the discard reading must say +1" "got: $(printf '%s' "$out" | grep -E '^\[3b\]' | head -1)"; fi
if [[ "$rc" -eq 0 ]]; then ok "CASE E60a: …and the exit stays 0 — a reading, never a verdict (warn-only by construction)"
else bad "CASE E60a: the reading must not change the exit code" "exit $rc: $(printf '%s' "$out" | grep '✗' | head -2)"; fi

# ── CASES 61–63: close.sh [3c] CONVERTER (S164, register row close/run-the-hermetic-converter-suites) ─────────
# The property: when this session touched windows-converter/ or prototypes/repair-bench/, the close RUNS the converter's
# hermetic suites and a red suite is SEEN as a red row — but the row is WARN-ONLY (the S108 standard): the exit code does
# not move until Rab arms it. Three fixtures, each violating one side: a planted FAILING suite must print RED and keep
# exit 0 (61); a passing suite must read clean (62, the positive control); an untouched converter must read skipped and
# run nothing (63). The interpreter is the fixture's own python (FP_PY) so no marker-env is needed to fire the guard.
CLOSE="$HERE/close.sh"
CONV="$WORK/conv"; mkdir -p "$CONV/windows-converter"
git -C "$CONV" init -q 2>/dev/null
printf 'x\n' > "$CONV/f.txt"
git -C "$CONV" add -A >/dev/null 2>&1
git -C "$CONV" -c user.email=t@t -c user.name=t commit -qm base >/dev/null 2>&1
conv_pin=$(git -C "$CONV" rev-parse HEAD)
printf 'y = 1\n' > "$CONV/windows-converter/thing.py"
printf 'import sys\nprint("planted RED")\nsys.exit(1)\n' > "$CONV/windows-converter/fail_selftest.py"
printf 'print("GREEN (3/3)")\n' > "$CONV/windows-converter/ok_selftest.py"
git -C "$CONV" add -A >/dev/null 2>&1
git -C "$CONV" -c user.email=t@t -c user.name=t commit -qm touch >/dev/null 2>&1
# The fixture's interpreter: a REAL python (the marker-env one where it exists, else the uv python, else PATH's) — bare
# `python`/`python3` on this desktop can be the Store stub that exits 49 (the muster skill's own note), and a stub makes
# a planted RED pass for the wrong reason; CASE 62's positive control is what catches that, and did on the first run.
FIXPY="$HOME/ml/marker-env/Scripts/python.exe"
[ -f "$FIXPY" ] || FIXPY="$(ls "$HOME"/AppData/Roaming/uv/python/cpython-3.*/python.exe 2>/dev/null | head -1)"
[ -n "$FIXPY" ] && [ -f "$FIXPY" ] || FIXPY="$(command -v python3 || command -v python)"
# CASE 61 — the planted failing suite: the row reads RED, the exit stays 0 (warn-only), and the RED says so.
out=$(FP_PY="$FIXPY" FP_REPO="$CONV" FP_CONV_SUITES="windows-converter/fail_selftest.py" bash "$CLOSE" "$conv_pin" 2>&1); rc=$?
if printf '%s' "$out" | grep -q 'CONV fail_selftest  *RED (warn-only'; then ok "CASE 61: a planted failing converter suite reads RED on its row"
else bad "CASE 61: the failing suite must read RED on its row" "got: $(printf '%s' "$out" | grep -E 'CONV' | head -2)"; fi
if printf '%s' "$out" | grep -q 'CONVERTER  *RED but WARN-ONLY'; then ok "CASE 61: …and the summary row says WARN-ONLY out loud (SYM-046: a 0 is not the suites green)"
else bad "CASE 61: the summary row must say WARN-ONLY" "got: $(printf '%s' "$out" | grep -E 'CONVERTER' | head -2)"; fi
rc_fail=$rc
FP_PY="$FIXPY" FP_REPO="$CONV" FP_CONV_SUITES="windows-converter/ok_selftest.py" bash "$CLOSE" "$conv_pin" >/dev/null 2>&1; rc_ok=$?
if [[ "$rc_fail" -eq "$rc_ok" ]]; then ok "CASE 61: …and the exit code is the SAME with the red suite as with a green one (warn-only by construction — the differential reading, whatever the fixture's other rows say)"
else bad "CASE 61: a warn-only red must not move the exit code" "exit with the red suite $rc_fail vs with a green one $rc_ok"; fi
# CASE 61b — ARMED: the same fixture with FP_CONV_ARMED=1 must exit 1 — the arming is the one line that gives the row teeth.
out=$(FP_PY="$FIXPY" FP_REPO="$CONV" FP_CONV_SUITES="windows-converter/fail_selftest.py" FP_CONV_ARMED=1 bash "$CLOSE" "$conv_pin" 2>&1); rc=$?
assert "CASE 61b: ARMED (FP_CONV_ARMED=1), the same red suite stops the close" 1 'CONVERTER  *RED — a suite is red and the row is ARMED' "$rc" "$out"
# CASE 62 — the positive control: a passing suite reads clean with its own tally.
out=$(FP_PY="$FIXPY" FP_REPO="$CONV" FP_CONV_SUITES="windows-converter/ok_selftest.py" bash "$CLOSE" "$conv_pin" 2>&1)
if printf '%s' "$out" | grep -q 'CONV ok_selftest  *clean — GREEN (3/3)'; then ok "CASE 62 POSITIVE CONTROL: a passing suite reads clean with its tally"
else bad "CASE 62: a passing suite must read clean with its tally" "got: $(printf '%s' "$out" | grep -E 'CONV' | head -2)"; fi
# CASE 63 — nothing under the two dirs changed since the pin: the row reads skipped and no suite runs.
out=$(FP_PY="$FIXPY" FP_REPO="$CONV" FP_CONV_SUITES="windows-converter/fail_selftest.py" bash "$CLOSE" HEAD 2>&1)
if printf '%s' "$out" | grep -q 'CONVERTER  *skipped — no windows-converter/' && ! printf '%s' "$out" | grep -q 'planted RED'; then ok "CASE 63: an untouched converter reads skipped and runs no suite"
else bad "CASE 63: the untouched case must read skipped and run nothing" "got: $(printf '%s' "$out" | grep -E 'CONV' | head -2)"; fi

# ── CASES 64–65: close.sh [3c] CONVERTER, the node suite (S165) ───────────────────────────────────────────────
# The same property for the one non-python suite (the bench's test_table_health.js): a planted failing suite reads RED,
# warn-only (64); a passing one reads clean with its tally (64b, the positive control); and a runner that is not there
# reads UNREAD, never clean (65 — the rule of case 7 applied to this row). The runner is FP_CONV_NODE; the fixture points
# it at the fixture's own python so the row's LOGIC is under test whether or not node is on this machine's PATH — the
# real node run is the live close's (S165's own close ran it against the real suite), not this suite's.
mkdir -p "$CONV/prototypes/repair-bench"
printf 'import sys\nprint("planted RED")\nsys.exit(1)\n' > "$CONV/prototypes/repair-bench/fail.js"
printf 'print("TABLE HEALTH: 2/2 ok")\n' > "$CONV/prototypes/repair-bench/ok.js"
git -C "$CONV" add -A >/dev/null 2>&1
git -C "$CONV" -c user.email=t@t -c user.name=t commit -qm node-fixtures >/dev/null 2>&1
out=$(FP_PY="$FIXPY" FP_REPO="$CONV" FP_CONV_SUITES="windows-converter/ok_selftest.py" FP_CONV_NODE="$FIXPY" FP_CONV_NODE_SUITES="prototypes/repair-bench/fail.js" bash "$CLOSE" "$conv_pin" 2>&1); rc_nfail=$?
if printf '%s' "$out" | grep -q 'CONV fail  *RED (warn-only'; then ok "CASE 64: a planted failing node suite reads RED on its row"
else bad "CASE 64: the failing node suite must read RED on its row" "got: $(printf '%s' "$out" | grep -E 'CONV' | head -3)"; fi
if printf '%s' "$out" | grep -q 'CONVERTER  *RED but WARN-ONLY'; then ok "CASE 64: …and the summary row says WARN-ONLY (the python rows were green — one red suite of any kind is the row's red)"
else bad "CASE 64: the summary row must say WARN-ONLY" "got: $(printf '%s' "$out" | grep -E 'CONVERTER' | head -2)"; fi
out=$(FP_PY="$FIXPY" FP_REPO="$CONV" FP_CONV_SUITES="windows-converter/ok_selftest.py" FP_CONV_NODE="$FIXPY" FP_CONV_NODE_SUITES="prototypes/repair-bench/ok.js" bash "$CLOSE" "$conv_pin" 2>&1); rc_nok=$?
if printf '%s' "$out" | grep -q 'CONV ok  *clean — TABLE HEALTH: 2/2 ok'; then ok "CASE 64b POSITIVE CONTROL: a passing node suite reads clean with its tally"
else bad "CASE 64b: a passing node suite must read clean with its tally" "got: $(printf '%s' "$out" | grep -E 'CONV ok' | head -2)"; fi
if [[ "$rc_nfail" -eq "$rc_nok" ]]; then ok "CASE 64: …and the exit code is the SAME with the red node suite as with a green one (warn-only, the differential reading)"
else bad "CASE 64: a warn-only red must not move the exit code" "exit with the red suite $rc_nfail vs with a green one $rc_nok"; fi
# CASE 65 — the runner is not there: UNREAD on the row, never clean, and the exit unchanged.
out=$(FP_PY="$FIXPY" FP_REPO="$CONV" FP_CONV_SUITES="windows-converter/ok_selftest.py" FP_CONV_NODE="$WORK/no-such-runner" FP_CONV_NODE_SUITES="prototypes/repair-bench/ok.js" bash "$CLOSE" "$conv_pin" 2>&1); rc_nun=$?
if printf '%s' "$out" | grep -q 'CONV ok  *UNREAD — runner not found' && ! printf '%s' "$out" | grep -q 'CONV ok  *clean'; then ok "CASE 65: a missing runner reads UNREAD on the node row, never clean (a failed probe is not a green)"
else bad "CASE 65: a missing runner must read UNREAD, never clean" "got: $(printf '%s' "$out" | grep -E 'CONV ok' | head -2)"; fi
if [[ "$rc_nun" -eq "$rc_nok" ]]; then ok "CASE 65: …and UNREAD does not move the exit code (UNREAD never blocks and never claims clean)"
else bad "CASE 65: UNREAD must not move the exit code" "exit with the missing runner $rc_nun vs with a green one $rc_nok"; fi

# ── CASE 66: the REAL CONVERTER lists name files that exist (S170) ───────────────────────────────────────────
# Cases 61–65 plant their own lists through FP_CONV_SUITES / FP_CONV_NODE_SUITES; nothing read the real defaults. A typo or
# a moved suite on the real line reads UNREAD at a close — never clean, but never caught until a close touched the converter.
# This case reads both default lists out of close.sh and asserts every path exists under this checkout; the NEGATIVE CONTROL
# appends a name that does not exist to a COPY of the list and watches the same reading go red.
REAL_LISTS="$(grep -oE 'FP_CONV(_NODE)?_SUITES:-[^}]*' "$CLOSE" | sed -E 's/^FP_CONV(_NODE)?_SUITES:-//' | tr ' ' '\n' | sed '/^$/d')"
missing66=""
n66=0
while IFS= read -r p; do
  [[ -z "$p" ]] && continue
  n66=$((n66 + 1))
  [[ -f "$HERE/../../../$p" ]] || missing66="$missing66 $p"
done <<< "$REAL_LISTS"
if [[ "$n66" -ge 9 && -z "$missing66" ]]; then ok "CASE 66: every path on close.sh's REAL converter lists exists in this checkout ($n66 suites)"
else bad "CASE 66: a name on the real converter list has no file" "read $n66 name(s); missing:$missing66"; fi
missing66b=""
while IFS= read -r p; do
  [[ -z "$p" ]] && continue
  [[ -f "$HERE/../../../$p" ]] || missing66b="$missing66b $p"
done <<< "$REAL_LISTS
windows-converter/no_such_selftest.py"
if [[ "$missing66b" == " windows-converter/no_such_selftest.py" ]]; then ok "CASE 66 NEGATIVE CONTROL: a planted name with no file is the one the reading names"
else bad "CASE 66 NEGATIVE CONTROL: the planted name must be named missing" "got:$missing66b"; fi

# ── CASE 67: close.sh [5] LEVERS, the AST sub-row (S184, SYM-096) ────────────────────────────────────────
# The property: a numeric literal the regex gate cannot see (a call default, a dict value, a tuple element, a comparison
# operand) ADDED since the pin is LISTED beneath the LEVERS row by observability/lever_census.py, warn-only — and a fixture
# where the census cannot run reads UNREAD, never clean (the rule of case 7 applied to this sub-row). The fixture repo is
# the CONV one (its windows-converter/thing.py is an added file); the census module is copied in for (a) and absent for (b).
mkdir -p "$CONV/observability"
cp "$HERE/../../../observability/lever_census.py" "$CONV/observability/lever_census.py"
printf 'def g(x, floor=0.77):\n    return x < floor\n' >> "$CONV/windows-converter/thing.py"
git -C "$CONV" add -A >/dev/null 2>&1
git -C "$CONV" -c user.email=t@t -c user.name=t commit -qm lever-plant >/dev/null 2>&1
out=$(FP_PY="$FIXPY" FP_REPO="$CONV" FP_CONV_SUITES="windows-converter/ok_selftest.py" bash "$CLOSE" "$conv_pin" 2>&1); rc_lit=$?
if printf '%s' "$out" | grep -q 'lever census (AST, warn-only): 1 numeric literal'; then ok "CASE 67: a call-default literal added since the pin is LISTED beneath LEVERS (1 numeric literal)"
else bad "CASE 67: the AST sub-row must list the planted literal" "got: $(printf '%s' "$out" | grep -E 'lever census|LEVERS' | head -3)"; fi
if printf '%s' "$out" | grep -q 'LEVERS  *no unlevered threshold constants'; then ok "CASE 67: …while the regex row above it still reads none (the blind class, by construction)"
else bad "CASE 67: the regex row must not see a call default" "got: $(printf '%s' "$out" | grep -E 'LEVERS' | head -2)"; fi
rm -f "$CONV/observability/lever_census.py"
out=$(FP_PY="$FIXPY" FP_REPO="$CONV" FP_CONV_SUITES="windows-converter/ok_selftest.py" bash "$CLOSE" "$conv_pin" 2>&1); rc_unread=$?
if printf '%s' "$out" | grep -q 'lever census UNREAD'; then ok "CASE 67 NEGATIVE CONTROL: with no census module the sub-row reads UNREAD, never clean"
else bad "CASE 67 NEGATIVE CONTROL: a failed probe must read UNREAD" "got: $(printf '%s' "$out" | grep -E 'lever census' | head -2)"; fi
if [[ "$rc_lit" -eq "$rc_unread" ]]; then ok "CASE 67: …and the exit code is the SAME listed or UNREAD (warn-only by construction; arming is Rab's)"
else bad "CASE 67: the sub-row must not move the exit code" "listed $rc_lit vs UNREAD $rc_unread"; fi
cp "$HERE/../../../observability/lever_census.py" "$CONV/observability/lever_census.py"

# ── CASE 68: close.sh [5] LEVERS, the regex row exempts selftests (S185, POLICY law 2) ───────────────────────
# The property: a `NAME = 0.42` added inside a *_selftest.py (an expected value, a fixture string) is NOT a lever and the
# regex row must not name it — S184's close named `LIMIT` from a string in lever_census_selftest.py; the same line added in a
# non-selftest file IS named (the positive control, so the exemption cannot have silenced the row).
printf 'LIMIT68 = 0.42\n' > "$CONV/windows-converter/plant_selftest.py"
git -C "$CONV" add -A >/dev/null 2>&1
git -C "$CONV" -c user.email=t@t -c user.name=t commit -qm lever-selftest-plant >/dev/null 2>&1
out=$(FP_PY="$FIXPY" FP_REPO="$CONV" FP_CONV_SUITES="windows-converter/ok_selftest.py" bash "$CLOSE" "$conv_pin" 2>&1)
if ! printf '%s' "$out" | grep -q 'LIMIT68'; then ok "CASE 68: a NAME = 0.42 added in a *_selftest.py is NOT named by the regex row (POLICY law 2)"
else bad "CASE 68: the regex row must exempt a selftest's constants" "got: $(printf '%s' "$out" | grep -E 'LEVERS' | head -2)"; fi
printf 'LIMIT68B = 0.42\n' > "$CONV/windows-converter/plant_module.py"
git -C "$CONV" add -A >/dev/null 2>&1
git -C "$CONV" -c user.email=t@t -c user.name=t commit -qm lever-module-plant >/dev/null 2>&1
out=$(FP_PY="$FIXPY" FP_REPO="$CONV" FP_CONV_SUITES="windows-converter/ok_selftest.py" bash "$CLOSE" "$conv_pin" 2>&1)
if printf '%s' "$out" | grep -q 'LIMIT68B'; then ok "CASE 68 POSITIVE CONTROL: the same line in a non-selftest file IS named — the exemption did not silence the row"
else bad "CASE 68 POSITIVE CONTROL: a module's unlevered constant must still be named" "got: $(printf '%s' "$out" | grep -E 'LEVERS' | head -2)"; fi

# ── CASE 69: close.sh [5b] PROMISES — docs/18 §3.7's line filed at every close (S189 E3) ─────────────────────
# The property: the row reads the converted events' promise beside the actual (a planted events file through FP_EVENTS:
# two promised conversions at 0.50x and 4.00x) and prints the summary — median, within 2×, the worst named; a missing file
# reads UNREAD, never clean; and the exit code is the same either way (warn-only by construction).
cp "$HERE/../../../observability/promise_audit.py" "$CONV/observability/promise_audit.py"
printf '{"ts":"2026-09-17T05:00:00+00:00","pid":1,"stage":"convert","event":"converted","source":"p69a.pdf","pages":100,"s_per_page":2.0,"promised_s_per_page":1.0,"estimate_basis":"similar","estimate_samples":3}\n{"ts":"2026-09-17T06:00:00+00:00","pid":1,"stage":"convert","event":"converted","source":"p69b.pdf","pages":100,"s_per_page":0.5,"promised_s_per_page":2.0,"estimate_basis":"similar","estimate_samples":3}\n' > "$WORK/events69.jsonl"
out=$(FP_PY="$FIXPY" FP_REPO="$CONV" FP_EVENTS="$WORK/events69.jsonl" FP_CONV_SUITES="windows-converter/ok_selftest.py" bash "$CLOSE" "$conv_pin" 2>&1); rc_p=$?
# the median of [0.50, 4.00] is 2.25 (the arithmetic median, docs/34's plain reading) and 0.50 sits ON the 2× bound, inside —
# the first draft of this case typed 1.41x / 0 of 2 (a geometric guess) and the instrument corrected it (S189 E3)
if printf '%s' "$out" | grep -q 'PROMISES  *promise/actual over the last 2 promised conversion(s): median 2.25x .* within 2x 1 of 2'; then ok "CASE 69: the PROMISES row reads the planted events — 2 promised, median 2.25x, within 2x 1 of 2"
else bad "CASE 69: the PROMISES row must summarise the planted events" "got: $(printf '%s' "$out" | grep -E 'PROMISES' | head -2)"; fi
if printf '%s' "$out" | grep -q 'worst 4.00x p69b.pdf'; then ok "CASE 69: …and names the worst promise (4.00x p69b.pdf)"
else bad "CASE 69: the worst promise must be named" "got: $(printf '%s' "$out" | grep -E 'PROMISES' | head -2)"; fi
out=$(FP_PY="$FIXPY" FP_REPO="$CONV" FP_EVENTS="$WORK/no-such-events.jsonl" FP_CONV_SUITES="windows-converter/ok_selftest.py" bash "$CLOSE" "$conv_pin" 2>&1); rc_pu=$?
if printf '%s' "$out" | grep -q 'PROMISES  *UNREAD'; then ok "CASE 69 NEGATIVE CONTROL: a missing events file reads UNREAD, never clean"
else bad "CASE 69 NEGATIVE CONTROL: a failed probe must read UNREAD" "got: $(printf '%s' "$out" | grep -E 'PROMISES' | head -2)"; fi
if [[ "$rc_p" -eq "$rc_pu" ]]; then ok "CASE 69: …and the exit code is the SAME read or UNREAD (warn-only by construction; what the Dock promises is Rab's)"
else bad "CASE 69: the row must not move the exit code" "read $rc_p vs UNREAD $rc_pu"; fi

# CASE 70 — THE TICKET REGISTER'S COUNT REACHES THE CARD, AND ITS ABSENCE READS UNREAD (S212, Phase C's
# second half). The property: the card prints the accounting register's totals BY FAMILY beside the SYM
# count, and — the half that actually matters — prints UNREAD when the private register is not on this
# machine. A 0 there would assert that no document has an open fault, which is the most flattering
# possible lie and the exact shape of the open-tasks undercount this suite already carries a case for.
# Violate both ways: a fixture register beside the fixture repo, then the same run with it absent.
TKP="$WORK/tkp/file-portal-private/sittings/S211/accounting"; mkdir -p "$TKP"
printf '# TICKETS\n\n## The counts\n\n| what | count |\n|---|---|\n| documents accounted | 7 |\n| tickets | 41 |\n| class 1 — an attempt that did not land | 2 |\n| class 2 — a verdict below pass | 9 |\n| class 3 — a measured loss in a shipped bundle | 20 |\n| class 4 — a reading the instrument got wrong | 5 |\n| class 5 — the whitelist consequence | 4 |\n| class 6 — a runtime or lane error | 1 |\n' > "$TKP/TICKETS.md"
R70="$WORK/tkp/file-portal"; mkdir -p "$(dirname "$R70")"
sha70=$(mkrepo "$R70" '| 2026-01-01 | Desktop | S41: first | 1111111 |' '| 2026-01-02 | Desktop | S42: second | SHAPLACEHOLDER |')
sed -i "s/SHAPLACEHOLDER/$sha70/" "$R70/CLAUDE_README.md"
git -C "$R70" add -A >/dev/null 2>&1; git -C "$R70" commit -qm tk >/dev/null 2>&1
mklib "$WORK/l70" 12 S42 "$sha70"
out=$(MEMORY_LIB="$WORK/l70" FP_REPO="$R70" PIPE_ROOT="$WORK/nope" VAULT_DIR="$WORK/nope" \
      WIDGET_EXE="$WORK/nope" MUSTER_NO_REMOTE=1 bash "$OPEN" 2>&1); rc=$?
if printf '%s' "$out" | grep -qE 'tickets +41 ticket\(s\) over 7 document\(s\)'; then ok "CASE 70: the card reads the register's totals (41 over 7)"
else bad "CASE 70: the card must read the register's totals" "got: $(printf '%s' "$out" | grep -E 'tickets' | head -2)"; fi
if printf '%s' "$out" | grep -qE 'c1=2 c2=9 c3=20 c4=5 c5=4 c6=1'; then ok "CASE 70: …and prints the open count BY FAMILY, which is the whole point of the row"
else bad "CASE 70: the family breakdown must reach the card" "got: $(printf '%s' "$out" | grep -E 'tickets' | head -2)"; fi
rm -f "$TKP/TICKETS.md"
out=$(MEMORY_LIB="$WORK/l70" FP_REPO="$R70" PIPE_ROOT="$WORK/nope" VAULT_DIR="$WORK/nope" \
      WIDGET_EXE="$WORK/nope" MUSTER_NO_REMOTE=1 bash "$OPEN" 2>&1); rc70u=$?
if printf '%s' "$out" | grep -qE 'tickets +UNREAD'; then ok "CASE 70 NEGATIVE CONTROL: an absent private register reads UNREAD"
else bad "CASE 70 NEGATIVE CONTROL: an absent register must read UNREAD" "got: $(printf '%s' "$out" | grep -E 'tickets' | head -2)"; fi
if printf '%s' "$out" | grep -qE 'tickets +(0 ticket|.*c1=0)'; then
  bad "CASE 70 NEGATIVE CONTROL: absence must NEVER render as a zero count" "the card printed a 0 where it could not read"
else ok "CASE 70 NEGATIVE CONTROL: …and never renders absence as 0 — the flattering lie this row exists to refuse"; fi
if [[ "$rc" -eq "$rc70u" ]]; then ok "CASE 70: the row is warn-only — the exit code is the same read or UNREAD"
else bad "CASE 70: the tickets row must not move the exit code" "read $rc vs UNREAD $rc70u"; fi

printf '\n%s\n' "────────────────────────────────"
# CASE 72 — THE DAY-ONE CLOSEOUT SAYS WHETHER IT IS STAMPED (S212 E5). The property: the branch that
# matches this session's OWN closeout by filename must also read its ⟨claimed:⟩ stamp and say so. It
# matched on the name alone before, so a record with no stamp passed on day one and only failed on day
# two — as a COLLISION, which reads like the card's fault. That is exactly how the stamp came to be
# missing from EIGHTY-NINE consecutive sittings (S124–S212, measured; OPEN-TASKS F14): day one never
# complained and day two blamed the guard. It is a WARN, never an exit, because a missing stamp breaks
# nothing on the first day — it breaks the open on the second.
# S213: gated like CASES 40–43, whose fixture this shares — off Windows mkopen43's S43-desktop-*.md reads as another
# machine's, and the case failed on the Linux runner from S212 E5 onward (two reds, three vacuous greens).
windows_case_72() {
mkopen43 72
today72=$(date -u +%Y-%m-%d)
printf '# S43\n\n**Occupant:** t\n\n## 1. Intent\n' > "$R/sessions/S43-desktop-$today72.md"
out=$(runopen 72); rc72u=$?
if printf '%s' "$out" | grep -qE 'MISSING — stamp it now'; then ok "CASE 72: a day-one closeout with NO stamp is told so, on the day someone can still fix it"
else bad "CASE 72: an unstamped day-one closeout must be named" "got: $(printf '%s' "$out" | grep -E 'OPEN —' | head -1 | cut -c1-150)"; fi
# ANCHORED to a COLLISION VERDICT — a row whose reading BEGINS with it — and not to the word anywhere
# in the output. This assertion's first draft searched the whole card and convicted the new warning for
# the sentence inside it ("without it a sitting past midnight opens on a COLLISION"). That is the THIRD
# time in one day, and the second AFTER the lesson was written into CASE 71 eight lines below: a test
# that cannot tell a verdict from a sentence about a verdict is the same confusion it is policing.
if printf '%s' "$out" | grep -qE '^[[:space:]]*COLLISION —'; then bad "CASE 72: a missing stamp on day one is a WARN, not a collision" "printed a COLLISION verdict"
else ok "CASE 72: …and it is not called a collision, because on day one it is not one"; fi
# NEGATIVE CONTROL: the same file WITH its stamp must say stamped and must NOT carry the warning —
# otherwise the note is decoration that fires on every open and stops being read, which is the failure
# mode of every warning nobody can turn off.
printf '# S43\n\n**Occupant:** t · ⟨claimed: Fable lane · occupant: t · S43 · %s⟩\n\n## 1. Intent\n' "$today72" > "$R/sessions/S43-desktop-$today72.md"
out=$(runopen 72); rc72s=$?
if printf '%s' "$out" | grep -qE '⟨claimed⟩ stamped'; then ok "CASE 72 NEGATIVE CONTROL: a stamped day-one closeout reads stamped"
else bad "CASE 72 NEGATIVE CONTROL: a stamped closeout must say so" "got: $(printf '%s' "$out" | grep -E 'OPEN —' | head -1 | cut -c1-150)"; fi
if printf '%s' "$out" | grep -qE 'MISSING — stamp it now'; then bad "CASE 72 NEGATIVE CONTROL: the warning must NOT fire on a stamped record" "a warning that always fires is decoration"
else ok "CASE 72 NEGATIVE CONTROL: …and the warning does not fire on it — a warning that always fires stops being read"; fi
if [[ "$rc72u" -eq "$rc72s" ]]; then ok "CASE 72: the stamp note is warn-only — it does not move the exit code either way"
else bad "CASE 72: the stamp note must not move the exit code" "unstamped $rc72u vs stamped $rc72s"; fi
}
if on_windows; then windows_case_72; else skip "CASE 72 (S212 E5): the fixture's S43-desktop-*.md reads as "\
"another machine's off Windows, as in CASES 40–43" "platform $(uname -s 2>/dev/null) (MUSTER_SELFTEST_PLATFORM=${MUSTER_SELFTEST_PLATFORM:-unset})" 5; fi

printf '\n%s\n' "────────────────────────────────"
# CASE 71 — THE PORTAL DOOR READS UNREAD WHEN IT CANNOT BE REACHED, NEVER "down" (S212 E4). The property is
# the oldest one in this file and the one its own first run broke: a probe that could not run is not an
# observation. The row was added because no card read PORTAL at all — every session opened without knowing
# whether the web app his phone talks to was up. The NEGATIVE CONTROL is the whole case: point PORTAL_URL at
# a closed port and the card must say UNREAD and must NOT say down, and must NOT move the exit code, because
# a dark tailnet address at 3am is not a fault and a session that treats it as one stops for nothing.
# S213: gated — open.sh prints the task rows and the portal door INSIDE its `if tasklist works` block, so off Windows
# neither row exists; on the Linux runner this case failed from S212 E4 onward (three reds, two vacuous greens).
windows_case_71() {
R71="$WORK/p71/file-portal"; mkdir -p "$(dirname "$R71")"
sha71=$(mkrepo "$R71" '| 2026-01-01 | Desktop | S41: first | 1111111 |' '| 2026-01-02 | Desktop | S42: second | SHAPLACEHOLDER |')
sed -i "s/SHAPLACEHOLDER/$sha71/" "$R71/CLAUDE_README.md"
git -C "$R71" add -A >/dev/null 2>&1; git -C "$R71" commit -qm p71 >/dev/null 2>&1
mklib "$WORK/l71" 12 S42 "$sha71"
# First: with MUSTER_NO_REMOTE set — the suite's own default — the row must SKIP rather than knock on a live door.
out=$(MEMORY_LIB="$WORK/l71" FP_REPO="$R71" PIPE_ROOT="$WORK/nope" VAULT_DIR="$WORK/nope" \
      WIDGET_EXE="$WORK/nope" MUSTER_NO_REMOTE=1 bash "$OPEN" 2>&1); rc71s=$?
if printf '%s' "$out" | grep -qE 'portal door +SKIPPED'; then ok "CASE 71: MUSTER_NO_REMOTE skips the door, so the suite never reaches the live one"
else bad "CASE 71: MUSTER_NO_REMOTE must skip the portal door" "got: $(printf '%s' "$out" | grep -E 'portal door' | head -2)"; fi
# Then the probe itself, named at a CLOSED LOCAL PORT so the case stays off the tailnet entirely — MUSTER_NO_REMOTE
# stays set, and the explicit PORTAL_URL is what lets the row run. 127.0.0.1:9 is the discard port and nothing
# listens on it, so this measures the refusal itself rather than a timeout.
out=$(MEMORY_LIB="$WORK/l71" FP_REPO="$R71" PIPE_ROOT="$WORK/nope" VAULT_DIR="$WORK/nope" \
      WIDGET_EXE="$WORK/nope" MUSTER_NO_REMOTE=1 PORTAL_URL="http://127.0.0.1:9/" bash "$OPEN" 2>&1); rc71d=$?
if printf '%s' "$out" | grep -qE 'portal door +UNREAD'; then ok "CASE 71 NEGATIVE CONTROL: a closed door reads UNREAD"
else bad "CASE 71 NEGATIVE CONTROL: an unreachable door must read UNREAD" "got: $(printf '%s' "$out" | grep -E 'portal door' | head -2)"; fi
# The match is ANCHORED to the reading itself — the label, the padding, then the first word — and not to the
# line, because this assertion's first draft searched the whole line for "down" and convicted the row for its own
# disclaimer ("NOT a statement that it is down"). The property is what the READING says, not which words appear
# near it; a test that cannot tell a verdict from a sentence about a verdict is the same confusion it is policing.
if printf '%s' "$out" | grep -qE 'portal door +(down|DOWN|not running|NOT RUNNING|unreachable|UNREACHABLE)'; then
  bad "CASE 71 NEGATIVE CONTROL: a failed probe must NEVER render as down" "the card called an unread door down"
else ok "CASE 71 NEGATIVE CONTROL: …and never renders a failed probe as down — this file's oldest rule"; fi
if printf '%s' "$out" | grep -qE "task +'File Portal PORTAL \(web app\)'"; then ok "CASE 71: the PORTAL task is on the card, so DURABLE is a question the open asks"
else bad "CASE 71: the card must carry a row for the PORTAL task" "got: $(printf '%s' "$out" | grep -E 'PORTAL' | head -2)"; fi
if [[ "$rc71d" -eq "$rc71s" ]]; then ok "CASE 71: the door row is warn-only — an unreachable PORTAL does not move the exit code"
else bad "CASE 71: the portal door row must not move the exit code" "unreachable $rc71d vs skipped $rc71s"; fi
}
if on_windows; then windows_case_71; else skip "CASE 71 (S212 E4): the task and portal-door rows live inside "\
"open.sh's tasklist block, absent off Windows" "platform $(uname -s 2>/dev/null) (MUSTER_SELFTEST_PLATFORM=${MUSTER_SELFTEST_PLATFORM:-unset})" 5; fi

printf '\n%s\n' "────────────────────────────────"
# CASE 73 — close.sh [4b] READS THE WARN-ONLY STEPS' LOGS (S213, OPEN-TASKS F16). The property: a continue-on-error
# step's red lives in its LOG, not in the run's conclusion (SYM-075), and the close must say so — while the exit code
# stays where it was (warn-only; arming A29 is Rab's). Fixture logs zips, fed through FP_CI_LOGS_ZIP, shaped like the
# real one (`python/31_Governance suites (A29, warn-only) — muster.txt` ending in the runner's own error line).
# THE POSITIVE CONTROL is the clean zip: without it a row that always printed RED would pass the red case.
C73="$WORK/c73"; mkdir -p "$C73"
git -C "$C73" init -q 2>/dev/null; printf 'x\n' > "$C73/f.txt"; git -C "$C73" add -A >/dev/null 2>&1
git -C "$C73" -c user.email=t@t -c user.name=t commit -qm base >/dev/null 2>&1
c73_pin=$(git -C "$C73" rev-parse HEAD)
"$FIXPY" - "$C73" <<'PYEOF'
import os, sys, zipfile
d = sys.argv[1]
red = "2026-09-24T19:50:00.0000000Z ALL TRIPWIRES...\n2026-09-24T19:50:01.0000000Z ##[error]Process completed with exit code 1.\n"
ok = "2026-09-24T19:50:00.0000000Z ALL TRIPWIRES FIRED\n"
for name, muster in (("red.zip", red), ("clean.zip", ok)):
    with zipfile.ZipFile(os.path.join(d, name), "w") as z:
        z.writestr("python/31_Governance suites (A29, warn-only) \u2014 muster.txt", muster)
        z.writestr("python/30_Governance suites (A29, warn-only) \u2014 coordination.txt", ok)
        z.writestr("python/16_Selftest (windows-converter inventions).txt", ok)
open(os.path.join(d, "notazip.zip"), "w").write("not a zip\n")
# THE WHOLE-JOB FORM: GitHub drops the per-step files after a while (run #755's were gone within two hours) and keeps
# `<n>_<job>.txt`; the reader must still find the red there, by the `##[group]Run` header above the error line
hdr = "2026-09-24T19:49:00.0000000Z ##[group]Run bash .claude/skills/muster/selftest.sh\n"
for name, body in (("jobred.zip", hdr + red), ("jobclean.zip", hdr + ok)):
    with zipfile.ZipFile(os.path.join(d, name), "w") as z:
        z.writestr("1_python.txt", body)
        z.writestr("python/system.txt", "system\n")
PYEOF
out=$(FP_PY="$FIXPY" FP_REPO="$C73" FP_CI_LOGS_ZIP="$C73/red.zip" bash "$CLOSE" "$c73_pin" 2>&1); rc73r=$?
if printf '%s' "$out" | grep -qE 'CI WARN-ONLY +RED IN THE LOG.*muster \(exit 1\)'; then ok "CASE 73: a warn-only step whose LOG exited 1 is named on the close — the red the conclusion hides"
else bad "CASE 73: a red warn-only log must be named" "got: $(printf '%s' "$out" | grep -E 'CI WARN-ONLY' | head -1)"; fi
if printf '%s' "$out" | grep -qE 'CI WARN-ONLY.*coordination'; then bad "CASE 73: a CLEAN warn-only step must not be named red" "the row named coordination"
else ok "CASE 73: …and only the red step is named — the clean warn-only step beside it is not"; fi
out=$(FP_PY="$FIXPY" FP_REPO="$C73" FP_CI_LOGS_ZIP="$C73/clean.zip" bash "$CLOSE" "$c73_pin" 2>&1); rc73c=$?
if printf '%s' "$out" | grep -qE 'CI WARN-ONLY +clean — 2 warn-only'; then ok "CASE 73 POSITIVE CONTROL: all warn-only logs clean reads clean, counting 2"
else bad "CASE 73 POSITIVE CONTROL: a clean zip must read clean with its count" "got: $(printf '%s' "$out" | grep -E 'CI WARN-ONLY' | head -1)"; fi
out=$(FP_PY="$FIXPY" FP_REPO="$C73" FP_CI_LOGS_ZIP="$C73/notazip.zip" bash "$CLOSE" "$c73_pin" 2>&1)
if printf '%s' "$out" | grep -qE 'CI WARN-ONLY +UNREAD'; then ok "CASE 73 NEGATIVE CONTROL: logs that cannot be read are UNREAD, never clean"
else bad "CASE 73 NEGATIVE CONTROL: an unreadable zip must read UNREAD" "got: $(printf '%s' "$out" | grep -E 'CI WARN-ONLY' | head -1)"; fi
out=$(FP_PY="$FIXPY" FP_REPO="$C73" FP_CI_LOGS_ZIP="$C73/jobred.zip" bash "$CLOSE" "$c73_pin" 2>&1)
if printf '%s' "$out" | grep -qE 'CI WARN-ONLY +RED IN THE LOG.*muster/selftest\.sh` \(exit 1, from the whole-job log\)'; then
  ok "CASE 73: once the per-step files have expired, the red is still found in the whole-job log, named by its command"
else bad "CASE 73: the whole-job form must still name the red" "got: $(printf '%s' "$out" | grep -E 'CI WARN-ONLY' | head -1)"; fi
out=$(FP_PY="$FIXPY" FP_REPO="$C73" FP_CI_LOGS_ZIP="$C73/jobclean.zip" bash "$CLOSE" "$c73_pin" 2>&1)
if printf '%s' "$out" | grep -qE 'CI WARN-ONLY +clean — 1 whole-job log'; then ok "CASE 73 POSITIVE CONTROL (whole-job form): no error exit reads clean"
else bad "CASE 73 POSITIVE CONTROL (whole-job form): a clean job log must read clean" "got: $(printf '%s' "$out" | grep -E 'CI WARN-ONLY' | head -1)"; fi
if [[ "$rc73r" -eq "$rc73c" ]]; then ok "CASE 73: the row is warn-only — a red warn-only log and a clean one exit the same"
else bad "CASE 73: the warn-only row must not move the exit code" "red $rc73r vs clean $rc73c"; fi

printf '\n%s\n' "────────────────────────────────"
# S194 E1: three tallies — fired (pass) / skipped (not run here, said) / silent (failed) — and the exit reads the fired cases only.
if [[ "$failed" -eq 0 ]]; then printf 'ALL TRIPWIRES FIRED — %s/%s · fired %s / skipped %s / silent 0%s\n' "$pass" "$((pass+failed))" "$pass" "$skipped" "$([[ $skipped -gt 0 ]] && printf ' (a skip is not a pass: %s assertion(s) could not run on this platform)' "$skipped")"; exit 0
else printf 'TRIPWIRES DISARMED — %s failed of %s · fired %s / skipped %s / silent %s. A guard nobody watched fire is a proxy with a reputation.\n' "$failed" "$((pass+failed))" "$pass" "$skipped" "$failed"; exit 1; fi
