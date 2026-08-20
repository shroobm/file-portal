#!/usr/bin/env bash
# .claude/skills/echo/sweep.sh — the MECHANICAL half of the commission echo.
#
# Prints the CONNECTED STATE a commission lands in, plus per-term hit maps across the repo
# and the memory library. VALUES, never checkmarks (docs/32 — a green summary must not stand
# in for a read state). An UNREAD row means the probe failed — it is NEVER a statement that
# the state is clean or that the thing is absent.
#
# Usage: sweep.sh [term ...]      each term: one lowercase word or a short quoted phrase
# Exit:  0 = core reads succeeded. 1 = a core surface was unreadable (repo brain, register,
#        symptom index, or lexicon) — the echo must say so, not silently proceed.
#
# Overrides (same names muster's open.sh uses, so a fixture drives both):
#   FP_REPO=  MEMORY_LIB=  PIPE_ROOT=
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FP_REPO="${FP_REPO:-$(cd "$HERE/../../.." && pwd)}"
MEMORY_LIB="${MEMORY_LIB:-$HOME/.claude/projects/C--Users-Bndit-Documents-Claude-Code-Memory-Backup/memory}"
PIPE_ROOT="${PIPE_ROOT:-$HOME/ml/library}"
README="$FP_REPO/CLAUDE_README.md"
REGISTER="$FP_REPO/docs/37-next-stage-plan.md"
SYMPTOMS="$FP_REPO/SYMPTOM-INDEX.md"
LEXICON="$HERE/lexicon.md"

fail=0
row() { printf '    %-16s %s\n' "$1" "$2"; }
lever() { cat "$PIPE_ROOT/$1" 2>/dev/null || echo '?'; }
cnt() { find "$PIPE_ROOT/$1" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' '; }

printf '══════ ECHO · SWEEP · %s ══════\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ── LEDGER — the newest row, values straight from the table ─────────────────
if [ -r "$README" ]; then
  last_row="$(grep -E '^\| 20[0-9]{2}-[0-9]{2}-[0-9]{2} \|' "$README" | tail -1)"
  if [ -n "$last_row" ]; then
    lane="$(printf '%s' "$last_row" | awk -F'|' '{gsub(/^ +| +$/,"",$3); print $3}')"
    snum="$(printf '%s' "$last_row" | awk -F'|' '{print $4}' | grep -oE 'S[0-9]+' | head -1)"
    sha="$(printf '%s' "$last_row" | awk -F'|' '{gsub(/^ +| +$/,"",$(NF-1)); print $(NF-1)}')"
    row "LEDGER" "newest row $lane ${snum:-?} · close ${sha:-?}"
  else
    row "LEDGER" "UNREAD — no ledger rows parsed from $README"; fail=1
  fi
else
  row "LEDGER" "UNREAD — $README not readable"; fail=1
fi

# ── LIVE LEVERS + PIPELINE — the state a decision would land in ─────────────
row "LEVERS" "audit=$(lever audit-mode.txt) · analyst=$(lever analyst-mode.txt) · batch=$(lever chunk-batch.txt)"
row "PIPELINE" "held $(cnt held) · anchor $(cnt anchor) · pending $(cnt pending)"

# ── REGISTER — how many decisions are open for his signature ────────────────
if [ -r "$REGISTER" ]; then
  sec="$(awk '/^## §3 /{f=1;next} /^## /{f=0} f' "$REGISTER")"
  items="$(printf '%s\n' "$sec" | grep -cE '^[0-9]+\.' || true)"
  signed="$(printf '%s\n' "$sec" | grep -c 'SIGNED' || true)"
  row "REGISTER" "docs/37 §3: $items items · $signed SIGNED mentions (per-item status is a read, not a count)"
else
  row "REGISTER" "UNREAD — $REGISTER not readable"; fail=1
fi

# ── SYMPTOMS — the tail of the index (rediscovery is a muster failure) ──────
if [ -r "$SYMPTOMS" ]; then
  total="$(grep -cE '^\| SYM-[0-9]{3} ' "$SYMPTOMS" || true)"
  tail_ids="$(grep -oE '^\| SYM-[0-9]{3}' "$SYMPTOMS" | tail -3 | grep -oE 'SYM-[0-9]{3}' | tr '\n' ' ')"
  row "SYM" "$total rows · tail: ${tail_ids:-?}"
else
  row "SYM" "UNREAD — $SYMPTOMS not readable"; fail=1
fi

# ── DOCS + LEXICON ──────────────────────────────────────────────────────────
docs_n="$(ls "$FP_REPO"/docs/[0-9][0-9]-*.* 2>/dev/null | wc -l | tr -d ' ')"
docs_newest="$(ls "$FP_REPO"/docs/[0-9][0-9]-*.* 2>/dev/null | sed 's|.*/||' | sort | tail -1)"
row "DOCS" "$docs_n numbered · newest ${docs_newest:-?}"
if [ -r "$LEXICON" ]; then
  lex_n="$(grep -cE '^\| [^|]+ \| ' "$LEXICON" || true)"
  lex_n=$((lex_n - 1))  # header row
  row "LEXICON" "$lex_n confirmed mappings · $LEXICON"
else
  row "LEXICON" "UNREAD — $LEXICON not readable"; fail=1
fi

# ── TERM HITS — the full-context search, per load-bearing word ──────────────
# Counts are FILE counts (how many files mention it), then top paths. The repo sweep covers
# docs + code + sessions; the library sweep covers every memory. Zero hits is evidence of an
# UNMAPPED word, not proof the concept is absent — say so in the card.
for term in "$@"; do
  repo_hits="$(grep -rliE -- "$term" "$FP_REPO/docs" "$FP_REPO/sessions" "$FP_REPO/windows-converter" "$FP_REPO/windows-widget/src-tauri/src" "$FP_REPO/linux-converter" "$FP_REPO/CLAUDE_README.md" "$FP_REPO/SYMPTOM-INDEX.md" 2>/dev/null)"
  mem_hits="$(grep -rliE -- "$term" "$MEMORY_LIB" 2>/dev/null)"
  rc="$(printf '%s' "$repo_hits" | grep -c . || true)"
  mc="$(printf '%s' "$mem_hits" | grep -c . || true)"
  row "TERM $term" "repo $rc file(s) · library $mc file(s)"
  printf '%s\n' "$repo_hits" | head -4 | sed "s|^$FP_REPO/|        repo: |"
  printf '%s\n' "$mem_hits" | head -2 | sed "s|^$MEMORY_LIB/|        lib:  |"
done

printf '══════ sweep exit %d — values only; the readings are the judgment half ══════\n' "$fail"
exit "$fail"
