#!/usr/bin/env bash
# .claude/skills/muster/open.sh — the MECHANICAL half of the session open.
#
# docs/21 §3: "never author a derivable section." Everything a command can produce is produced
# here; everything requiring judgment stays in SKILL.md, where a reader does it. Mechanical
# checks belong on mechanical facts; judgment checks belong to human hands (docs/21 §6).
#
# THE OUTPUT DISCIPLINE — read this before adding a line to the card:
#   This script prints VALUES, never ✓, for everything except a process exit code. A row of
#   checkmarks can be skimmed as "fine"; `held 4 · exe C3D277F7 · census 75/84` cannot. The
#   whole failure mode this file exists inside is a green summary standing in for a read state
#   (docs/32 — proxy substitution). A ✓ here is only ever an exit code.
#
# Exit: 0 = the mechanical half is clean. 1 = an incident the session must reconcile first.
#
# Overrides (same names muster.sh uses, so a fixture drives both):
#   MEMORY_LIB=  FP_REPO=  PIPE_ROOT=  VAULT_DIR=  WIDGET_EXE=
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FP_REPO="${FP_REPO:-$(cd "$HERE/../../.." && pwd)}"
MEMORY_LIB="${MEMORY_LIB:-$HOME/.claude/projects/C--Users-Bndit-Documents-Claude-Code-Memory-Backup/memory}"
PIPE_ROOT="${PIPE_ROOT:-$HOME/ml/library}"
VAULT_DIR="${VAULT_DIR:-$HOME/Documents/Obsidian/Obsidian and Zennotes Vault/Library}"
WIDGET_EXE="${WIDGET_EXE:-$HOME/AppData/Local/File Portal/file-portal-widget.exe}"
README="$FP_REPO/CLAUDE_README.md"

fail=0
row() { printf '    %-16s %s\n' "$1" "$2"; }

printf '════════ MUSTER · OPEN · %s ════════\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ─────────────────────────────────────────────────────────────────────────────
# [0] IDENTITY — which session is this?
#
# The number comes from LEDGER ROWS ONLY: lines that open `| <date> |` and carry an `S<n>:`
# cell. It is never taken from prose. docs/21 §7 prescribes
#     grep -oE '\bS[0-9]{1,3}\b' CLAUDE_README.md | sort -t S -k2 -n | tail -1
# under the banner "never by assumption" — and on 2026-08-15 that command returned S79 off a
# PROSE mention at CLAUDE_README.md:65 while the newest ledger row was S78. A selector that
# reads narrative is the same defect as `tail -1` reading position (SYM-028): a cheap proxy
# for "which session is newest" that drifted from the property and kept passing.
printf '[0] IDENTITY\n'
if [[ ! -f "$README" ]]; then
  row "ledger" "MISSING — no $README"; fail=1
  led_n=""; led_sha=""
else
  # S86: identity reads THIS machine's lane only (ledger cell 2). After the 2026-08-16 fork
  # merge the table carries ThinkPad rows; without the filter, a foreign row with a higher
  # number would move this machine's identity (their S99 would make this session S100).
  led_line=$(grep -E '^\| 20[0-9][0-9]-' "$README" | awk -F'|' -v lane="${MUSTER_LANE:-Desktop}" '
    { for (i=1;i<=NF;i++) gsub(/^[ \t\r]+|[ \t\r]+$/,"",$i)
      if ($3 != lane) next
      sess=""; sha=""
      for (i=1;i<=NF;i++) if ($i ~ /^S[0-9]+:/) { sess=substr($i,2,index($i,":")-2); break }
      for (i=NF;i>=1;i--) if ($i != "") { sha=$i; break }
      if (sess != "" && sha ~ /^[0-9a-fA-F]{7,40}$/) print sess, sha }' | sort -k1,1n | tail -1)
  led_n=$(printf '%s' "$led_line" | awk '{print $1}')
  led_sha=$(printf '%s' "$led_line" | awk '{print $2}')
  if [[ -z "$led_n" ]]; then
    row "ledger" "UNPARSEABLE — no row carries both an S<n>: cell and a SHA"; fail=1
  else
    row "ledger newest" "S$led_n  $led_sha"
  fi
fi

this_n=""
if [[ -n "$led_n" ]]; then this_n=$((led_n + 1)); fi
machine=$(uname -s 2>/dev/null)
case "$machine" in MINGW*|MSYS*|CYGWIN*) machine="desktop" ;; Linux) machine="thinkpad" ;; *) machine="unknown" ;; esac
today=$(date +%Y-%m-%d)
closeout="sessions/S${this_n}-${machine}-${today}.md"
[[ -n "$this_n" ]] && row "this session" "S$this_n  ·  $machine  ·  $today"

# Collision check. A number already spoken for means either this session is misnumbered or an
# earlier one wrote under a number it did not own. Both are faults, they are indistinguishable
# from here, and so this REPORTS and does not guess.
#
# SCOPED TO THE INHERITED TREE, at the newest ledger SHA — never to the working tree. The
# question is "was S<N> already spoken for in the record this session INHERITED", and a live-tree
# grep cannot answer it: the moment this session legitimately writes its own number, the check
# starts reporting the session to itself. That is the same defect shape as `tail -1` (position
# standing in for newest) and the TIME-STATE line-distance window — a cheap observable that is
# true when chosen and drifts the moment the thing it measures moves. Caught by running it:
# after the S79/S78 corrections it still fired, naming three files whose S79 references were
# written by S79 and were correct.
if [[ -n "$this_n" ]]; then
  # "Does a closeout already own this number" is asked ONCE, in [3] PIN, where it gets the three
  # states it actually has: this session's own / another machine-or-date's / absent. It used to
  # be asked here too as a flat exists-or-not, and the two answers disagreed the moment Phase 6
  # ran — PIN said OPEN while this said COLLISION, so the card contradicted itself and exited 1.
  # One question, one place, one answer.
  # Two different questions, and only one of them is mechanical (docs/21 §6: mechanical checks
  # belong on mechanical facts, judgment checks belong to human hands — confusing the two is how
  # a check comes to share the blind spot of the thing it checks).
  #
  # HARD — an unambiguous ownership claim: a closeout file for this number already exists. A
  # ledger row cannot exist by construction, since this number is the newest row's plus one.
  # Nothing to interpret; this fails.
  #
  # ADVISORY — prose in the inherited tree naming this number. A grep cannot tell "an artifact
  # misattributed to S<N>" from "a forward-looking reference to S<N> that was correct when
  # written". Both are real and they read identically: on 2026-08-15 the same grep returned six
  # genuine misattributions AND two correct forward references in docs/31 ("a future row that
  # omits S79:", "test against S79's own work"). A blanket correction would have broken the
  # correct ones. So this lists and the reader judges — it does not vote.
  hits=$(git -C "$FP_REPO" grep -lE "\bS${this_n}\b" "${led_sha:-HEAD}" -- . 2>/dev/null \
         | sed "s|^${led_sha}:||" | tr '\n' ' ')
  if [[ -n "$hits" ]]; then
    row "advisory" "S${this_n} is named in the INHERITED tree (${led_sha:-HEAD}) — read each, do not blanket-correct:"
    printf '    %-16s %s\n' "" "$hits"
  else
    row "advisory" "S${this_n} unnamed in the inherited tree"
  fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# [1] GROUND — the clocks, verbatim, plus the verifier's own integrity.
printf '[1] GROUND\n'
VENDOR="$HERE/muster.sh"
HOMECOPY="$HOME/.claude/muster.sh"
if [[ -f "$VENDOR" ]]; then
  vh=$(sha256sum "$VENDOR" | cut -c1-8 | tr 'a-f' 'A-F')
  if [[ -f "$HOMECOPY" ]]; then
    hh=$(sha256sum "$HOMECOPY" | cut -c1-8 | tr 'a-f' 'A-F')
    if [[ "$vh" == "$hh" ]]; then row "verifier" "$vh  (repo == ~/.claude)"
    else row "verifier" "DRIFT repo=$vh  home=$hh — the two copies disagree"; fail=1; fi
  else
    row "verifier" "$vh  (repo only; no ~/.claude/muster.sh)"
  fi
else
  row "verifier" "MISSING — $VENDOR"; fail=1
fi

if [[ -f "$VENDOR" ]]; then
  MEMORY_LIB="$MEMORY_LIB" FP_REPO="$FP_REPO" bash "$VENDOR"
  mexit=$?
  row "muster exit" "$mexit"
  [[ "$mexit" -ne 0 ]] && fail=1
fi

# THE ORIGIN RULE, born 2026-08-16 (S86). The hard clock verified LOCAL history only, and the
# local card was green while origin carried a fork: 52 unpushed Desktop commits (S78–S85) beside
# 11 ThinkPad commits whose sessions had taken the same numbers from the last row they could see.
# The clock cannot see a fork it never fetches — it was found this time only because Rab said
# "the ThinkPad left you a message". Fetch is read-only; a FAILED fetch renders UNREAD
# (SYM-031), never "in sync". Three live states, three severities: diverged (ahead AND behind)
# is the fork class and FAILS the card — reconcile by MERGE, never rebase, because ledger rows
# pin SHAs that a rebase would orphan (SYM-016); behind-only means pull before work; ahead-only
# is the unpushed backlog that GREW this fork — the close must push (CLAUDE_README §4).
if [[ -n "${MUSTER_NO_REMOTE:-}" ]]; then
  row "origin" "SKIPPED — MUSTER_NO_REMOTE set"
elif ! git -C "$FP_REPO" rev-parse --git-dir >/dev/null 2>&1; then
  row "origin" "n/a — not a git repo"
elif ! git -C "$FP_REPO" rev-parse --abbrev-ref '@{upstream}' >/dev/null 2>&1; then
  row "origin" "no upstream configured for this branch"
elif timeout 30 git -C "$FP_REPO" fetch --quiet 2>/dev/null; then
  ahead=$(git -C "$FP_REPO" rev-list --count '@{upstream}..HEAD' 2>/dev/null)
  behind=$(git -C "$FP_REPO" rev-list --count 'HEAD..@{upstream}' 2>/dev/null)
  if [[ -z "$ahead" || -z "$behind" ]]; then
    row "origin" "UNREAD — fetched, but ahead/behind counts unavailable"
  elif [[ "$ahead" -gt 0 && "$behind" -gt 0 ]]; then
    row "origin" "FORKED — ahead $ahead / behind $behind of upstream: reconcile before work (merge, never rebase — SYM-016)"; fail=1
  elif [[ "$behind" -gt 0 ]]; then
    row "origin" "behind $behind — new work on origin; pull before work"
  elif [[ "$ahead" -gt 0 ]]; then
    row "origin" "ahead $ahead — unpushed local work; the close must push"
  else
    row "origin" "in sync (fetched)"
  fi
else
  row "origin" "UNREAD — fetch failed; NOT a statement that origin matches local"
fi

# ─────────────────────────────────────────────────────────────────────────────
# [2] LIVE — today's reality. Every value here is `Observed` at the timestamp above and at NO
# other time. The previous closeout's §17 is `Historical` and may not stand in for any of it:
# on 2026-08-15 S78's §17 read "widget down · bench down" while both had been up since 12:59.
printf '[2] LIVE\n'
if [[ -d "$PIPE_ROOT" ]]; then
  cnt() { ls -1d "$PIPE_ROOT/$1"/*/ 2>/dev/null | grep -c . ; }
  fcnt() { ls -1 "$PIPE_ROOT/$1"/*.pdf 2>/dev/null | grep -c . ; }
  row "pipeline" "held $(cnt held) · anchor $(cnt anchor) · pending $(cnt pending) · drop $(fcnt drop)"
  row "levers" "audit=$(cat "$PIPE_ROOT/audit-mode.txt" 2>/dev/null || echo '?') · analyst=$(cat "$PIPE_ROOT/analyst-mode.txt" 2>/dev/null || echo '?') · batch=$(cat "$PIPE_ROOT/chunk-batch.txt" 2>/dev/null || echo '?')"
  row "gpu-lock" "$([[ -e "$PIPE_ROOT/.gpu-lock" ]] && echo 'PRESENT — a convert holds the card' || echo 'absent')"
  row "events" "$(grep -c . "$PIPE_ROOT/events.jsonl" 2>/dev/null || echo 0) line(s)"
else
  row "pipeline" "UNREAD — no $PIPE_ROOT on this machine (say unread, never fine)"
fi

# [2b] THE THREE REGISTERS — Rab's rule, signed S109: "muster makes it mandatory to check it."
#
# OPEN-TASKS.md existed from S107 and the protocol had NEVER referenced it: 0 hits in SKILL.md,
# open.sh and close.sh, measured. A register nothing forces you through is a shrine, not a spine,
# and its own header says it "should either earn its keep by being worked down or be deleted."
#
# So the card PRINTS COUNTS, never a checkmark. A tick would say "the register exists"; a count
# says how much is open, and a count that never falls is visible as a count that never falls.
# STALENESS IS A READING: a register untouched since before the last close is named as such,
# because a task list that stopped being written is worse than none - it reads authoritative.
reg_row() {  # reg_row <label> <path> <count-cmd>
  local label="$1" path="$2"
  if [[ ! -f "$path" ]]; then
    # A register that is TRACKED and missing from the tree was DELETED — an incident.
    # A register that was never tracked is a repo that does not have one — UNREAD, not a fault.
    # The first cut failed on both, which conflated "this file is absent" with "the clocks
    # disagree", and turned two ORIGIN advisories into incidents in fixtures that are bare temp
    # repos by design. Caught by this file's own suite, after I had already pushed it red.
    if git -C "$FP_REPO" ls-files --error-unmatch "${path#$FP_REPO/}" >/dev/null 2>&1; then
      row "$label" "UNREAD — tracked but MISSING from the tree; it was deleted, not empty"; fail=1
    else
      row "$label" "UNREAD — no ${path##*/} in this repo (not tracked; not a statement of 'nothing open')"
    fi
    return
  fi
  local age days
  age=$(git -C "$FP_REPO" log -1 --format=%cr -- "${path#$FP_REPO/}" 2>/dev/null)
  days=$(git -C "$FP_REPO" log -1 --format=%ct -- "${path#$FP_REPO/}" 2>/dev/null)
  if [[ -n "$days" ]]; then
    days=$(( ( $(date +%s) - days ) / 86400 ))
  else
    age="UNREAD"; days=0
  fi
  local stale=""
  [[ "$days" -ge 2 ]] && stale="  *** not written in ${days}d — is it still true? ***"
  row "$label" "$3 · last written ${age:-UNREAD}$stale"
}
if [[ -f "$README" ]]; then
  TASKS="$FP_REPO/OPEN-TASKS.md"
  SYMS="$FP_REPO/SYMPTOM-INDEX.md"
  # 2026-08-27: this class was [A-F], and OPEN-TASKS.md section J holds ids J1..J18 -
  # OUTSIDE it. The card printed `94 item(s)` against a file holding 112, for three
  # sessions. That is J15's shape - a counter that reads ONE spelling of a marker -
  # applied to the register instead of the symptom index, and it under-reported in the
  # direction that flatters. Struck rows begin `| ~~A18~~` and correctly do NOT match,
  # so this counts OPEN rows, which is the point.
  # Tripwire: selftest CASE 35, with a negative control on the strike exclusion.
  reg_row "open-tasks" "$TASKS" \
    "$(grep -cU '^| [A-FJ][0-9]' "$TASKS" 2>/dev/null || echo '?') item(s)"
  reg_row "symptoms" "$SYMS" \
    "$(grep -cU '^| SYM-' "$SYMS" 2>/dev/null || echo '?') row(s), $(grep -oU '| `open`' "$SYMS" 2>/dev/null | grep -c . || echo '?') open"
  if [[ -f "$FP_REPO/coordination/relay.md" ]]; then
    row "relay" "$(grep -cU '^## 20' "$FP_REPO/coordination/relay.md" 2>/dev/null || echo '?') entries · run \`gate.py status\` for the board"
  else
    # Same distinction as the registers above: tracked-and-missing is a deletion and an incident;
    # never-tracked is a repo without a bus. Both read UNREAD; only one is a fault.
    if git -C "$FP_REPO" ls-files --error-unmatch coordination/relay.md >/dev/null 2>&1; then
      row "relay" "UNREAD — tracked but MISSING; the bus was deleted, never 'quiet'"; fail=1
    else
      row "relay" "UNREAD — no coordination/relay.md in this repo (not tracked)"
    fi
  fi
fi

# THE FAILED-PROBE RULE, paid for during this script's own first run:
#
#   A probe that FAILED must never render as a NEGATIVE OBSERVATION.
#
# The first version ran `tasklist /FI "IMAGENAME eq …" /NH`. Git Bash's MSYS layer rewrites a
# leading `/FI` into a Windows path (`C:/Program Files/Git/FI`), tasklist rejected it, the error
# went to stderr, `2>/dev/null` swallowed it, awk got an empty string — and the card printed
# `widget  down` while PID 10048 was alive and had been all afternoon. An empty result stood in
# for "not running": a cheap proxy for the property, silently wrong, confidently rendered. That
# is docs/32 exactly, inside the guard written against docs/32, on its first run — the §6
# prediction landing immediately.
#
# So: take the process table ONCE with no `/` switches (nothing for MSYS to rewrite), verify the
# call actually produced a table, and only then count. If the probe did not succeed, the row says
# UNREAD. `down` is a claim, and a claim needs a reading behind it.
ps_table=$(tasklist 2>/dev/null); ps_rc=$?
if [[ "$ps_rc" -eq 0 && "$(printf '%s' "$ps_table" | grep -c .)" -gt 5 ]]; then
  # AND THE MIRROR OF THAT RULE, paid for by S80's own open. A probe that SUCCEEDED must not
  # render a PARTIAL observation as a whole one. This line was `{print $2; exit}` — first match
  # wins, the rest discarded — so the card printed `widget  18856` while 18856 AND 19536 were both
  # alive, each having spawned its own watcher chain onto the same drop folder. Nothing stops a
  # second launch (no single-instance guard in the Tauri app) and `.gpu-lock` arbitrates nothing
  # (SYM-032), so two instances is a state this machine can actually reach — which makes the card
  # the place it has to become visible. `down` needed a reading behind it; so does `one`.
  wpids=$(printf '%s\n' "$ps_table" | awk '/^file-portal-widget\.exe/{print $2}')
  wn=$(printf '%s\n' "$wpids" | grep -c .)
  if [[ "$wn" -gt 1 ]]; then
    row "widget" "$wn INSTANCES: $(printf '%s' "$wpids" | tr '\n' ' ')— each spawns its own watcher, no mutex between them (SYM-033)"
  else
    row "widget" "${wpids:-down (table read, no match)}"
  fi
  row "python procs" "$(printf '%s\n' "$ps_table" | grep -c '^python\.exe')"
  row "ollama" "$(printf '%s\n' "$ps_table" | grep -c '^ollama')"
  # S81 §10.4: a hung run was reported healthy because a process NAMED llama-server was read as
  # ours - it was ollama's own engine (ollama >= 0.32 runs llama-server.exe internally, from
  # AppData\Local\Programs\Ollama\lib\ollama\). The name is not an identity; only the parent PID
  # decides. The row exists so the next glance at the card meets the lesson at the exact place
  # the mistake was made.
  lsn=$(printf '%s\n' "$ps_table" | grep -c '^llama-server\.exe')
  if [[ "$lsn" -gt 0 ]]; then
    row "llama-server" "$lsn — the NAME does not identify it (ollama's engine is also llama-server.exe); the parent PID decides, never the name (S81)"
  fi
else
  row "processes" "UNREAD — process-table probe failed (rc=$ps_rc); NOT a statement that anything is down"
fi

if [[ -f "$WIDGET_EXE" ]]; then
  row "installed exe" "$(sha256sum "$WIDGET_EXE" | cut -c1-8 | tr 'a-f' 'A-F')  (adoption is Rab's hand — docs/19 §0.3)"
else
  row "installed exe" "UNREAD — not at $WIDGET_EXE"
fi

if [[ -d "$VAULT_DIR" ]]; then
  row "vault" "$(find "$VAULT_DIR" -name '*.md' -not -path '*/.git/*' 2>/dev/null | grep -c .) note(s) · tip $(git -C "$VAULT_DIR" log --format=%h -1 2>/dev/null || echo '?')"
else
  row "vault" "UNREAD — no $VAULT_DIR"
fi
# The receiver half. coordination/messages/2026-08-09 fixes the split: the desktop can verify the
# soft clock, the widget/exe, the pipeline root and the GPU; the vault tip, staging occupants,
# receipts and unit liveness exist only on the ThinkPad and must be READ, never assumed. ssh flags
# are docs/19 law 6 — without BatchMode a windowless process hangs forever on an invisible
# host-key prompt (S56: nine zombie scp pairs). `timeout` is the second belt: this probe may cost
# the open a few seconds and can never cost it the session.
if [[ -n "${MUSTER_NO_REMOTE:-}" ]]; then
  row "thinkpad" "SKIPPED — MUSTER_NO_REMOTE set"
elif ! command -v ssh >/dev/null 2>&1; then
  row "thinkpad" "UNREAD — no ssh on this machine"
else
  rmt=$(timeout 25 ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 \
        rab@archlinux 'printf "%s|%s|%s|%s" \
          "$(systemctl --user is-active file-portal-converter 2>/dev/null)" \
          "$(git -C ~/file-portal/vault.git log --format=%h -1 2>/dev/null)" \
          "$(ls -1 ~/file-portal/library/staging 2>/dev/null | wc -l)" \
          "$(wc -l < ~/file-portal/receipts.jsonl 2>/dev/null)"' 2>/dev/null)
  if [[ -n "$rmt" ]]; then
    IFS='|' read -r r_unit r_tip r_stg r_rcpt <<< "$rmt"
    row "thinkpad" "converter=$r_unit · vault tip $r_tip · staging $r_stg · receipts $r_rcpt"
  else
    row "thinkpad" "UNREAD — host did not answer; NOT a statement that it is down or clean"
  fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# [3] PIN — fix the closeout's terms NOW, while nothing is known about the outcome.
#
# S78 §10.1: the closeout ref was chosen at CLOSE by `len(diff) > 500` — a proxy for "this diff
# introduces a producer key" — and the session shipped a green report over a red suite. A ref
# picked before any result exists cannot be picked to suit one.
printf '[3] PIN\n'
row "--since" "${led_sha:-UNKNOWN}"
row "closeout" "$closeout"
# Three states, not two. Re-running the open MID-SESSION is normal — Rab reruns it, and a
# reconciliation loop reruns it — so "the closeout exists" must not be reported as an incident
# when the thing that exists is THIS session's own file. The discriminator is mechanical: a
# closeout for this number, this machine, and today is this session's; one carrying a different
# machine or date belongs to someone else and is a real collision.
if [[ -n "$this_n" && -f "$FP_REPO/$closeout" ]]; then
  added=$(git -C "$FP_REPO" log --diff-filter=A --format=%h -- "$closeout" 2>/dev/null | tail -1)
  row "" "OPEN — this session's closeout exists${added:+, added in $added} · §1 must stay byte-identical to close"
elif [[ -n "$this_n" && -n "$(ls -1 "$FP_REPO/sessions/S${this_n}-"* 2>/dev/null)" ]]; then
  row "" "COLLISION — a closeout for S${this_n} exists under a different machine/date"; fail=1
else
  row "" "absent — SKILL.md Phase 6 creates it BEFORE work, with §1 Intent in Rab's words"
fi

printf '════════ mechanical half: %s ════════\n' \
  "$([[ "$fail" -eq 0 ]] && echo 'clean (exit 0) — judgment half is SKILL.md Phases 2-6' || echo 'INCIDENT (exit 1) — reconcile before work')"
exit "$fail"
