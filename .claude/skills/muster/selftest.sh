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
printf '\n%s\n' "────────────────────────────────"
if [[ "$failed" -eq 0 ]]; then printf 'ALL TRIPWIRES FIRED — %s/%s\n' "$pass" "$((pass+failed))"; exit 0
else printf 'TRIPWIRES DISARMED — %s failed of %s. A guard nobody watched fire is a proxy with a reputation.\n' "$failed" "$((pass+failed))"; exit 1; fi
