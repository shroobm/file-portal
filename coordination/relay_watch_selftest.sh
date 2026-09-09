#!/usr/bin/env bash
# coordination/relay_watch_selftest.sh — fixtures for coordination/relay_watch.sh (S120 B8).
#
# Builds a fixture coordination dir under a temp dir (FP_COORD), runs the watcher against it
# with a 1s interval, and drives every signal: NEW-ENTRY, INBOX, BEAT, UNREAD, ESCALATION OPEN,
# STOPPED — plus a positive control (a quiet interval prints nothing) and a log/stdout parity
# check. Never touches the real coordination/relay.md or ack-*.json (FP_COORD replaces the
# coordination dir wholesale for both gate.py and the watcher under test).
#
# CAVEAT, discovered while building this fixture and kept as case 6 rather than smoothed over:
# the assignment's own fixture list names "corrupt ack-codex.json -> UNREAD". Measured against
# gate.py @ 280cfc7: `load()` (gate.py:176) never raises on a malformed sidecar — it degrades to
# a graceful per-lane "UNREAD (skill not on, or file malformed)" board line, and `cmd_status`
# still prints "relay-gate board ..." first and returns 0 either way. So corrupting ONE ack file
# does NOT trip the watcher's UNREAD branch (which fires only when `gate.py status` itself exits
# non-zero WITHOUT ever printing the board). Case 6a proves that non-trip honestly; case 6b
# reaches the real precondition (the transaction lock path made unopenable, so `status` raises
# before its first print) and proves the guard fires there. A guard whose stated fixture never
# reaches it is a proxy dressed as a tripwire (docs/47 law 4) — this suite tests the real
# precondition, not the assignment's literal, unreachable one, and says so.
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/.." && pwd)"
GATE="$REPO_ROOT/.claude/skills/relay-gate/gate.py"
WATCHER="$HERE/relay_watch.sh"
PY="uv run python"

FIXTURE="$(mktemp -d)"
export FP_COORD="$FIXTURE"
RELAY_MD="$FIXTURE/relay.md"
PRIVATE_DIR="$FIXTURE/private"
LOG="$PRIVATE_DIR/relay-watch.log"
STOP="$PRIVATE_DIR/relay-watch.STOP"
STDOUT_FILE="$FIXTURE/watch-stdout.log"
STDERR_FILE="$FIXTURE/watch-stderr.log"

WATCHER_PID=""
cleanup() {
  if [ -n "$WATCHER_PID" ] && kill -0 "$WATCHER_PID" 2>/dev/null; then
    kill "$WATCHER_PID" 2>/dev/null
    sleep 0.3
    kill -9 "$WATCHER_PID" 2>/dev/null
  fi
  rm -rf "$FIXTURE" 2>/dev/null
}
trap cleanup EXIT
trap 'cleanup; exit 130' INT
trap 'cleanup; exit 143' TERM

pass=0; total=0
check() {
  total=$((total + 1))
  if [ "$2" -eq 0 ]; then
    pass=$((pass + 1)); printf 'PASS %d — %s\n' "$total" "$1"
  else
    printf 'FAIL %d — %s\n' "$total" "$1"
  fi
}

utc_now() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# wait_for <file> <pattern> <timeout_seconds> — polls once a second; returns 0 the moment
# <pattern> (a fixed string) appears in <file>, 1 if it never does within the budget.
wait_for() {
  local file="$1" pat="$2" timeout="${3:-3}" waited=0
  while [ "$waited" -lt "$timeout" ]; do
    if grep -qF -- "$pat" "$file" 2>/dev/null; then return 0; fi
    sleep 1
    waited=$((waited + 1))
  done
  grep -qF -- "$pat" "$file" 2>/dev/null
}

# The header stamp is MINUTE-granular (gate.py ENTRY_META_RE: `\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z`). The
# first version of this fixture stamped seconds, so gate.py never parsed the fixture's hand-appended
# headers as entries and the ungated path (B4/B11) was UNREACHABLE here while the live bus fired a
# phantom INBOX on it — a fixture that cannot reach the guard is a proxy (PROBE-SHAPE, S120).
append_header() {  # append_header <from> <to> <id>
  printf '\n## %s · ⟨from: %s⟩ → ⟨to: %s⟩ · ⟨msg: %s⟩\n**RECAP.** fixture entry\n' \
    "$(date -u +%Y-%m-%dT%H:%MZ)" "$1" "$2" "$3" >>"$RELAY_MD"
}

cd "$REPO_ROOT" || { echo "FAILED: cannot cd to $REPO_ROOT"; exit 2; }

# ── fixture: two lanes on, a seed relay.md ──────────────────────────────────
$PY "$GATE" init --as Fable >/dev/null 2>&1
check "fixture: gate.py init --as Fable" $?
$PY "$GATE" init --as Codex >/dev/null 2>&1
check "fixture: gate.py init --as Codex" $?
printf '# fixture relay\n\n' >"$RELAY_MD"
check "fixture: seed relay.md written" $([ -f "$RELAY_MD" ]; echo $?)

BODY="$FIXTURE/body.md"
cat >"$BODY" <<'EOF'
**RECAP.** fixture body for the relay_watch selftest.

**FOR RAB.** nothing to decide; fixture only.

**SUGGESTED PROMPT** none.
EOF

# ── start the watcher: 1s interval, ALIVE every tick (RELAY_WATCH_ALIVE_MIN=0) so case 8 below
#    (ALIVE is log-only) doesn't need a second instance or a long wait ───────────────────────
RELAY_WATCH_INTERVAL=1 RELAY_WATCH_ALIVE_MIN=0 bash "$WATCHER" --as Fable \
  >"$STDOUT_FILE" 2>"$STDERR_FILE" &
WATCHER_PID=$!

wait_for "$STDOUT_FILE" "WATCH ARMED"
check "1: WATCH ARMED on stdout at start" $?

# ── 2: NEW-ENTRY — a header from the OTHER lane (Codex) ────────────────────
append_header Codex Fable MSG-CDX-0001
wait_for "$STDOUT_FILE" "NEW-ENTRY"
check "2: NEW-ENTRY fires for a Codex header within 3s" $?
line="$(grep 'NEW-ENTRY' "$STDOUT_FILE" | head -1)"
printf '%s' "$line" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z NEW-ENTRY'
check "2b: the NEW-ENTRY line carries a UTC prefix (YYYY-MM-DDTHH:MM:SSZ)" $?

# ── 2c: B11 (S120) — an UNGATED peer entry (a header with no `sent` record: B4 lists it under
#    "ungated (no ACK owed):" in gate.py inbox) is NEW-ENTRY only; it must NEVER fire INBOX. The
#    live bus fired "INBOX MSG-CDX-0027" at 2026-09-09T21:31:55Z the moment B4 landed, because the
#    watcher read ids from every inbox line. The id column stops at the ungated heading. ──────
sleep 3
phantom_ungated="$(grep -c 'INBOX MSG-CDX-0001' "$STDOUT_FILE")"
check "2c: B11 — an ungated entry (no ACK owed) never fires INBOX (phantom lines: $phantom_ungated)" $([ "$phantom_ungated" -eq 0 ]; echo $?)

# ── 3: INBOX — a conforming, ack-required post from Codex to Fable ─────────
$PY "$GATE" post --as Codex --to Fable --subject "selftest inbox" --body "$BODY" >/dev/null 2>&1
check "fixture: gate.py post --as Codex (conforming envelope)" $?
wait_for "$STDOUT_FILE" "INBOX"
check "3: INBOX fires for the unconfirmed gated message" $?

# ── 3b/3c: B10 (S120) — an id named inside another message's SUBJECT must never become an INBOX
#    signal. The S119 watcher grepped ids out of the whole inbox line and fired a phantom
#    "INBOX MSG-FAB-0055" at its arming (2026-09-09T18:39:45Z) because MSG-CDX-0033's subject reads
#    "RED: MSG-FAB-0055 digest mismatch". The id is the FIRST column, nothing else. ───────────
$PY "$GATE" post --as Codex --to Fable --subject "RED: MSG-FAB-0055 digest mismatch (selftest B10)" --body "$BODY" >/dev/null 2>&1
check "fixture: gate.py post --as Codex whose SUBJECT names MSG-FAB-0055" $?
sleep 3
phantom="$(grep -c 'INBOX MSG-FAB-0055' "$STDOUT_FILE")"
check "3b: B10 — an id inside a subject never fires INBOX (phantom lines: $phantom)" $([ "$phantom" -eq 0 ]; echo $?)
inbox_lines="$(grep -c 'INBOX MSG-CDX-' "$STDOUT_FILE")"
check "3c: B10 — both real Codex messages fired INBOX by their own id (INBOX MSG-CDX-* lines: $inbox_lines)" $([ "$inbox_lines" -eq 2 ]; echo $?)

# ── 4: BEAT — Codex's doing text changes ────────────────────────────────────
$PY "$GATE" beat --as Codex --doing "selftest beat marker" >/dev/null 2>&1
check "fixture: gate.py beat --as Codex --doing ..." $?
wait_for "$STDOUT_FILE" "BEAT Codex"
check "4: BEAT Codex fires with the new doing text" $?

# ── 6a: corrupting ack-codex.json alone does NOT trip UNREAD (see the file header caveat) ──
before_unread="$(grep -c 'UNREAD' "$STDOUT_FILE")"
cp "$FIXTURE/ack-codex.json" "$FIXTURE/ack-codex.json.bak"
printf 'not json' >"$FIXTURE/ack-codex.json"
sleep 3
after_unread="$(grep -c 'UNREAD' "$STDOUT_FILE")"
check "6a: corrupt ack-codex.json alone does NOT fire UNREAD (gate.py@280cfc7 degrades gracefully — status still exits 0)" \
  $([ "$before_unread" -eq "$after_unread" ]; echo $?)
mv "$FIXTURE/ack-codex.json.bak" "$FIXTURE/ack-codex.json"

# ── 6b: NEGATIVE CONTROL — the real UNREAD precondition (status fails before its first print) ──
LOCKFILE="$FIXTURE/.relay-gate.lock"
rm -f "$LOCKFILE"
mkdir "$LOCKFILE"
wait_for "$STDOUT_FILE" "UNREAD"
check "6b: UNREAD fires when gate.py status genuinely fails before printing the board (lock path unopenable)" $?
rmdir "$LOCKFILE"

# ── 5: ESCALATION OPEN, and it fires exactly once (S119's false-positive guard) ─────────────
$PY "$GATE" escalate --as Codex --asking "selftest escalation" --why "adoption" \
  --ticket SELFTEST-ESC-1 >/dev/null 2>&1
check "fixture: gate.py escalate --as Codex" $?
wait_for "$STDOUT_FILE" "ESCALATION OPEN"
check "5: ESCALATION OPEN fires (matches the rendered sentence)" $?
esc_before="$(grep -c 'ESCALATION OPEN' "$STDOUT_FILE")"
sleep 3
esc_after="$(grep -c 'ESCALATION OPEN' "$STDOUT_FILE")"
check "5b: ESCALATION OPEN fires once, not on every subsequent poll" \
  $([ "$esc_before" -eq "$esc_after" ]; echo $?)

# ── 7: POSITIVE CONTROL — a quiet interval (nothing changed) prints no new line ─────────────
before_lines="$(wc -l <"$STDOUT_FILE")"
sleep 3
after_lines="$(wc -l <"$STDOUT_FILE")"
check "7: POSITIVE CONTROL — a quiet interval adds no new stdout line" \
  $([ "$before_lines" -eq "$after_lines" ]; echo $?)

# ── 8: ALIVE is log-only — it must never reach stdout, but must reach the log ───────────────
grep -q "WATCH ALIVE" "$LOG"
check "8a: WATCH ALIVE reaches the log" $?
grep -q "WATCH ALIVE" "$STDOUT_FILE"
alive_on_stdout=$?
check "8b: WATCH ALIVE never reaches stdout (log-only, per NR-13)" $([ "$alive_on_stdout" -ne 0 ]; echo $?)

# ── 9: log holds every stdout signal line, verbatim (extra ALIVE lines in the log are fine) ──
mismatch=0
while IFS= read -r sline; do
  [ -z "$sline" ] && continue
  grep -qF -- "$sline" "$LOG" || mismatch=1
done <"$STDOUT_FILE"
check "9: every stdout signal line is also present, verbatim, in relay-watch.log" "$mismatch"

# ── 10: STOPPED — the watcher exits 0 the moment the STOP file appears ─────────────────────
echo "selftest stop reason" >"$STOP"
wait_for "$STDOUT_FILE" "STOPPED"
check "10a: STOPPED fires within 3s of the STOP file appearing" $?
wait "$WATCHER_PID"
stop_exit_rc=$?
check "10b: the watcher process exits 0 after STOPPED" $stop_exit_rc
WATCHER_PID=""   # already reaped; nothing left for cleanup to kill

printf '════ relay_watch selftest: %d/%d ════\n' "$pass" "$total"
[ "$pass" -eq "$total" ]
