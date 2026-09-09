#!/usr/bin/env bash
# coordination/relay_watch.sh — the tracked relay watcher (S120 B8).
#
# Ports coordination/private/relay-watch.sh (the S119 gitignored original, born
# "/relay-gate have a sonnet agent watching the relay autonomously 24/7 until I say stop
# relay-gate") into the tracked tree: path-relative (repo root derived from this script's own
# location, never hardcoded), either lane via --as, every signal UTC-stamped AND logged, and a
# selftest (coordination/relay_watch_selftest.sh).
#
# SIGNALS (stdout carries ONLY these — each line is meant to wake a session — and every one is
# also appended to <coord>/private/relay-watch.log with the same UTC prefix):
#   WATCH ARMED <header/inbox/interval summary>          — once, at start
#   NEW-ENTRY <header>                                   — a relay.md header from any OTHER lane
#   INBOX <id> awaits <lane>'s confirmation               — a newly unconfirmed ack-required msg
#   BEAT <peer>: <doing>                                  — the peer's beat "doing" text changed
#   ESCALATION OPEN — FULL STOP on both lanes ...          — gate.py status renders the FULL STOP
#   UNREAD: gate.py status exited <rc> ...                 — status failed AND printed no board
#   STOPPED: <first 120 bytes of the STOP file>            — coordination/private/relay-watch.STOP
#     exists; the loop exits 0 immediately after
#
# NOT a signal (log only, never stdout): "WATCH ALIVE" every RELAY_WATCH_ALIVE_MIN minutes
# (default 10) — so a quiet stretch of log reads as "watching, nothing happened" rather than
# "the watcher died silently" (NR-13).
#
# Two sources, because the gate's sidecar cannot see an entry appended to relay.md without
# `gate.py post` (its own blind spot) and relay.md cannot see a confirmation:
#   (1) relay.md          — a new header from any lane but mine       -> NEW-ENTRY
#   (2) gate.py inbox     — a newly unconfirmed gated message to me   -> INBOX
#   (3) gate.py status    — the peer's beat text changing             -> BEAT
#                          — an OPEN escalation                       -> ESCALATION OPEN
#                          — a failed, board-less read                -> UNREAD
#
# The ESCALATION match is anchored on gate.py's exact rendered sentence
# ("An open escalation halts every lane"), never the bare word "escalation" — that word also
# appears inside ordinary beat text ("no displayed open escalation"), and matching it alone fired
# a false positive on Codex's beat every 30s in S119 (2026-09-09T18:36Z).
#
# CAVEAT (measured against gate.py @ 280cfc7, 2026-09-09): `load()` (gate.py:176) never raises —
# a malformed or corrupt ack-*.json degrades to a graceful per-lane "UNREAD (skill not on, or
# file malformed)" line, and `cmd_status` still prints "relay-gate board ..." first and returns 0.
# So corrupting one ack-*.json alone does NOT trip the UNREAD branch below; only a status run that
# raises BEFORE its first print (e.g. the transaction lock file itself becomes unopenable) does.
# The branch is kept because it is the honest defensive case ("a probe that could not run" is
# never silence), not because ack corruption reaches it today. See the selftest's case 6/6b.
#
# STOPS only on coordination/private/relay-watch.STOP existing (prints STOPPED, exits 0). Any
# other exit is a failure — silence is never calm. Read-only: never posts, confirms, beats, or
# touches a sidecar; never writes relay.md or an ack-*.json.
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/.." && pwd)"
GATE="$REPO_ROOT/.claude/skills/relay-gate/gate.py"

LANE="Fable"
if [ "${1:-}" = "--as" ]; then
  LANE="${2:?--as requires a lane (Fable or Codex)}"
fi
case "$LANE" in
  Fable) PEER="Codex" ;;
  Codex) PEER="Fable" ;;
  *) echo "FAILED: --as must be Fable or Codex, got '$LANE'" >&2; exit 2 ;;
esac

# coordination/ itself — honours FP_COORD exactly as gate.py's own coord_dir() does (gate.py:44):
# FP_COORD's presence REPLACES the coordination dir wholesale, it does not nest under it.
COORD_DIR="${FP_COORD:-$REPO_ROOT/coordination}"
RELAY_MD="$COORD_DIR/relay.md"
PRIVATE_DIR="$COORD_DIR/private"
LOG="$PRIVATE_DIR/relay-watch.log"
STOP="$PRIVATE_DIR/relay-watch.STOP"
mkdir -p "$PRIVATE_DIR" || { echo "FAILED: cannot mkdir -p $PRIVATE_DIR" >&2; exit 2; }

INTERVAL="${RELAY_WATCH_INTERVAL:-30}"
ALIVE_MIN="${RELAY_WATCH_ALIVE_MIN:-10}"
PY="uv run python"

cd "$REPO_ROOT" || { echo "FAILED: cannot cd to $REPO_ROOT" >&2; exit 2; }

utc_now() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# `grep -c` already prints "0" for a readable file with no match (and only fails, with nothing on
# stdout, when the file itself is absent) — a naive `grep -c ... || echo 0` double-prints "0" in
# the zero-match case (grep's own "0" plus the fallback's), corrupting the count into two lines.
header_count() {
  if [ -f "$RELAY_MD" ]; then
    grep -cU "^## .*⟨from: " "$RELAY_MD"
  else
    echo 0
  fi
}

# Every SIGNAL: stdout AND the log, both UTC-prefixed, byte-identical apart from the trailing
# newline each stream already supplies.
signal() {
  local line
  line="$(utc_now) $1"
  printf '%s\n' "$line"
  printf '%s\n' "$line" >>"$LOG"
}

# WATCH ALIVE: log only — never stdout, so it never wakes a session (NR-13).
alive_log() {
  printf '%s WATCH ALIVE\n' "$(utc_now)" >>"$LOG"
}

# B10 (S120, 2026-09-09): the inbox id is the FIRST COLUMN of an inbox line and nothing else. The
# S119 watcher grepped ids out of the whole line and fired a phantom "INBOX MSG-FAB-0055" at its
# arming (18:39:45Z) because MSG-CDX-0033's SUBJECT reads "RED: MSG-FAB-0055 digest mismatch".
# Tripwire: relay_watch_selftest.sh cases 3b/3c.
# B11 (S120, 21:31:55Z): gate.py inbox (B4) now also lists UNGATED peer entries under the heading
# "ungated (no ACK owed):" — those owe nothing and are already NEW-ENTRY signals; the id column
# stops at that heading. Tripwire: case 2c.
inbox_ids() {
  $PY "$GATE" inbox --as "$LANE" 2>/dev/null | awk '/^ungated/ {exit} $1 ~ /^MSG-[A-Z][A-Z][A-Z]-[0-9][0-9][0-9][0-9]$/ {print $1}' | sort -u | tr '\n' ' '
}

seen_headers=$(header_count)
inbox_prev=$(inbox_ids)
beat_prev=$($PY "$GATE" status 2>/dev/null | awk -v peer="$PEER" '$0 ~ ("^  " peer "  state="){f=1} f&&/doing/{print; exit}')
esc_prev=0
last_alive=$(date +%s)

signal "WATCH ARMED: as=$LANE peer=$PEER headers=$seen_headers inbox='${inbox_prev:-none}' interval=${INTERVAL}s alive=${ALIVE_MIN}m — stops on $STOP"

while true; do
  if [ -e "$STOP" ]; then
    signal "STOPPED: $(head -c 120 "$STOP" 2>/dev/null)"
    exit 0
  fi
  sleep "$INTERVAL"

  now_epoch=$(date +%s)
  if [ $((now_epoch - last_alive)) -ge $((ALIVE_MIN * 60)) ]; then
    alive_log
    last_alive=$now_epoch
  fi

  now_headers=$(header_count)
  if [ "$now_headers" -gt "$seen_headers" ]; then
    grep -U "^## .*⟨from: " "$RELAY_MD" | tail -n $((now_headers - seen_headers)) | tr -d '\r' | while IFS= read -r h; do
      case "$h" in
        *"⟨from: $LANE⟩"*) ;;
        *) signal "NEW-ENTRY $h" ;;
      esac
    done
    seen_headers=$now_headers
  fi

  inbox_now=$(inbox_ids)
  if [ "$inbox_now" != "$inbox_prev" ]; then
    for id in $inbox_now; do
      case " $inbox_prev " in
        *" $id "*) ;;
        *) signal "INBOX $id awaits $LANE's confirmation" ;;
      esac
    done
    inbox_prev="$inbox_now"
  fi

  st=$($PY "$GATE" status 2>&1)
  rc=$?
  if [ "$rc" -ne 0 ] && ! printf '%s' "$st" | grep -q "relay-gate board"; then
    signal "UNREAD: gate.py status exited $rc — the board cannot be read; this watch is BLIND, not quiet"
  fi

  beat_now=$(printf '%s' "$st" | awk -v peer="$PEER" '$0 ~ ("^  " peer "  state="){f=1} f&&/doing/{print; exit}')
  if [ -n "$beat_now" ] && [ "$beat_now" != "$beat_prev" ]; then
    signal "BEAT $PEER: $(printf '%s' "$beat_now" | sed 's/^ *//' | cut -c1-200)"
    beat_prev="$beat_now"
  fi

  # Match the rendering, not the word (S119: "no displayed open escalation" inside beat text fired
  # a false positive on the bare word "escalation" every 30s, 2026-09-09T18:36Z).
  if printf '%s' "$st" | grep -q "An open escalation halts every lane"; then
    if [ "$esc_prev" != "1" ]; then
      signal "ESCALATION OPEN — FULL STOP on both lanes (gate.py status renders the decision queue)"
      esc_prev=1
    fi
  else
    esc_prev=0
  fi
done
