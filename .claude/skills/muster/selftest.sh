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
out=$(FP_PY="/no/such/python.exe" FP_REPO="$GATE" FP_CENSUS_SUITE="$CEN29/zero-two.sh" bash "$CLOSE" "$base" 2>&1); rc=$?
assert "CLOSE CENSUS: 0/2 can never green a two-tripwire suite" 0 'RED-WARN.*banner 0/2' "$rc" "$out"
out=$(FP_PY="/no/such/python.exe" FP_REPO="$GATE" FP_CENSUS_SUITE="$CEN29/shared-lie.sh" bash "$CLOSE" "$base" 2>&1); rc=$?
assert "CLOSE CENSUS: a declared-but-unreached tripwire is named missing" 0 'RED-WARN.*declaration/flight mismatch' "$rc" "$out"
assert "CLOSE CENSUS: the missing tripwire ID is visible" 0 'MISSING FIRED: T2' "$rc" "$out"
out=$(FP_PY="/no/such/python.exe" FP_REPO="$GATE" FP_CENSUS_SUITE="$CEN29/huge.sh" bash "$CLOSE" "$base" 2>&1); rc=$?
assert "CLOSE CENSUS: an oversized integer is UNREAD, never a numeric false green" 0 'banner integers exceed the bounded parser' "$rc" "$out"


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
printf '%s\r\n' '# OPEN TASKS' '' '| A1 | open a-row | x |' '| A2 | open a-row | x |' '| ~~A3~~ **STRUCK** | resolved - must NOT be counted | x |' '| B1 | open b-row | x |' '| J1 | open j-row | x |' '| J2 | open j-row | x |' > "$R/OPEN-TASKS.md"
printf '%s\r\n' '| SYM-001 | s | c | S1 | `open` | g |' > "$R/SYMPTOM-INDEX.md"
git -C "$R" add -A >/dev/null 2>&1; git -C "$R" commit -qm reg >/dev/null 2>&1
mklib "$WORK/l35" 12 S42 "$sha"
out=$(MEMORY_LIB="$WORK/l35" FP_REPO="$R" PIPE_ROOT="$WORK/nope" VAULT_DIR="$WORK/nope" WIDGET_EXE="$WORK/nope" MUSTER_NO_REMOTE=1 bash "$OPEN" 2>&1)
if printf '%s' "$out" | grep -qE 'open-tasks +5 item\(s\)'; then
  ok "REGISTER COUNT: A-rows, B-rows AND J-rows all counted; struck excluded (5)"
else
  bad "REGISTER COUNT: open-tasks must read 5 (2 A + 1 B + 2 J; struck A3 excluded)" "got: $(printf '%s' "$out" | grep -E 'open-tasks' | head -1)"
fi
# NEGATIVE CONTROL, same fixture: 6 id-bearing rows exist. A counter that ignored the strike
# would read 6. So 6 must never appear - this is what stops the fix degenerating into
# "count every row", which would satisfy the assertion above for entirely the wrong reason.
if printf '%s' "$out" | grep -qE 'open-tasks +6 item\(s\)'; then
  bad "REGISTER COUNT negative control: a struck row was counted" "read 6, so ~~A3~~ was counted"
else ok "…and a struck row is never counted (never reads 6)"; fi

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
  ok "J15: both `open` and **OPEN** counted, and a prose mention is NOT (3 of 4)"
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

printf '\n%s\n' "────────────────────────────────"
if [[ "$failed" -eq 0 ]]; then printf 'ALL TRIPWIRES FIRED — %s/%s\n' "$pass" "$((pass+failed))"; exit 0
else printf 'TRIPWIRES DISARMED — %s failed of %s. A guard nobody watched fire is a proxy with a reputation.\n' "$failed" "$((pass+failed))"; exit 1; fi
