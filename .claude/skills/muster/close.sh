#!/usr/bin/env bash
# .claude/skills/muster/close.sh — the MECHANICAL half of the session close.
# ⟨claimed: Fable · S103 · 2026-08-20⟩
#
# Signed by Rab 2026-08-20: "add both, fmt to the ritual and CI to the close." Built because
# both halves of that sentence had already been DOCTRINE and had failed as doctrine:
#
#   · `cargo fmt --check` was prescribed FIRST in the rebuild ritual (docs/19:68, SYM-020) and
#     S101 skipped it, turning CI red.
#   · CI was never in the close at all, so S101 and S102 both closed reporting "clean" on top
#     of a red build — three closes red before Rab saw it.
#   · And the close contract itself asked for `glass_detector.py --since <SHA>` WITHOUT
#     `--enforce`, the form that exits 0 while printing dozens of unsigned glitches (SYM-046).
#
# THE OUTPUT DISCIPLINE — identical to open.sh, and for the same reason (docs/32, proxy
# substitution): this prints VALUES, never ✓, for anything but an exit code. UNREAD means the
# probe failed and is NEVER a statement that the thing is clean. A close that cannot reach
# GitHub says UNREAD and stays exit 0 — it does not invent a green, and it does not block the
# close over a network outage. Only a MEASURED red exits 1.
#
#   bash .claude/skills/muster/close.sh <pinned-SHA>
#
# Exit: 0 = nothing measured red. 1 = a measured red the close must resolve first.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FP_REPO="${FP_REPO:-$(cd "$HERE/../../.." && pwd)}"
PIN="${1:-}"
PY="${FP_PY:-$HOME/ml/marker-env/Scripts/python.exe}"
CARGO_DIR="$FP_REPO/windows-widget/src-tauri"

red=0
row() { printf '    %-16s %s\n' "$1" "$2"; }

printf '════════ MUSTER · CLOSE · %s ════════\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

if [ -z "$PIN" ]; then
  row "PIN" "MISSING — usage: close.sh <pinned-SHA> (the open card's --since)"
  red=1
else
  if git -C "$FP_REPO" rev-parse --verify "$PIN^{commit}" >/dev/null 2>&1; then
    row "PIN" "$PIN"
  else
    row "PIN" "UNRESOLVABLE: $PIN — NOT a statement that the tree is clean"
    red=1
  fi
fi

# ── [1] DIFF — every changed file must be accounted for by a human in the closeout ──────────
if [ -n "$PIN" ] && git -C "$FP_REPO" rev-parse --verify "$PIN^{commit}" >/dev/null 2>&1; then
  files=$(git -C "$FP_REPO" diff --name-only "$PIN"..HEAD | grep -c . || true)
  dirty=$(git -C "$FP_REPO" status --porcelain | grep -cv '^??' || true)
  untracked=$(git -C "$FP_REPO" status --porcelain | grep -c '^??' || true)
  row "DIFF" "$files file(s) since $PIN · $dirty uncommitted · $untracked untracked"
  [ "$dirty" -gt 0 ] && { row "" "UNCOMMITTED WORK — the close must commit or state it"; red=1; }
fi

# ── [2] GLASS — with --enforce, the only form whose exit code means anything (SYM-046) ──────
if [ -x "$PY" ] || [ -f "$PY" ]; then
  if [ -n "$PIN" ]; then
    if out=$("$PY" "$FP_REPO/observability/glass_detector.py" --since "$PIN" --enforce 2>&1); then
      row "GLASS" "clean since $PIN (--enforce; bare runs exit 0 regardless — SYM-046)"
    else
      n=$(printf '%s' "$out" | grep -oE '[0-9]+ UNSIGNED GLITCH' | head -1)
      row "GLASS" "RED — ${n:-unsigned glitches} since $PIN: render them or sign them"
      red=1
    fi
  fi
else
  row "GLASS" "UNREAD — interpreter not found at $PY; NOT a statement that glass is clean"
fi

# ── [3] RUST — only when this session touched the widget; fmt LEADS (docs/19:68, SYM-020) ───
touched_rust=0
if [ -n "$PIN" ] && git -C "$FP_REPO" rev-parse --verify "$PIN^{commit}" >/dev/null 2>&1; then
  git -C "$FP_REPO" diff --name-only "$PIN"..HEAD | grep -q '^windows-widget/' && touched_rust=1
fi
if [ "$touched_rust" -eq 0 ]; then
  row "RUST" "skipped — no windows-widget/ change since $PIN"
elif ! command -v cargo >/dev/null 2>&1; then
  row "RUST" "UNREAD — cargo not on PATH; NOT a statement that the widget builds"
else
  for step in "fmt:cargo fmt --check" "clippy:cargo clippy --all-targets -- -D warnings" "test:cargo test"; do
    name="${step%%:*}"; cmd="${step#*:}"
    if (cd "$CARGO_DIR" && eval "$cmd" >/dev/null 2>&1); then
      row "RUST $name" "clean"
    else
      row "RUST $name" "RED — run it and read the output; fmt LEADS the ritual (docs/19:68)"
      red=1
    fi
  done
fi

# ── [4] CI — the check whose absence let two sessions close green on a red build ────────────
# Route is docs/37 §4's pre-resolution: the stored git credential, FULL sha to head_sha.
# FP_CI_SHA exists so the tripwire can point this branch at a KNOWN-RED historical run
# (S103 uses 534a6c0, red on Format check) and watch the red path actually fire.
sha="${FP_CI_SHA:-$(git -C "$FP_REPO" rev-parse HEAD 2>/dev/null || echo "")}"
ahead=$(git -C "$FP_REPO" rev-list --count '@{u}..HEAD' 2>/dev/null || echo "?")
tok=$(printf 'protocol=https\nhost=github.com\n\n' | git -C "$FP_REPO" credential fill 2>/dev/null | sed -n 's/^password=//p')
if [ -z "$tok" ]; then
  row "CI" "UNREAD — no stored credential; NOT a statement that CI is green"
elif ! command -v curl >/dev/null 2>&1; then
  row "CI" "UNREAD — curl absent; NOT a statement that CI is green"
else
  # S109: this line read `?per_page=20` and scanned the twenty most recent runs for the SHA —
  # so the guard DECAYED. Its own tripwire points at the known-red historical run 534a6c0
  # (2026-08-20); by S109 that run had simply scrolled off a twenty-item window, the probe
  # returned NO-RUN, and the red-path case had been failing ever since — a guard that stopped
  # being able to fire because time passed, not because anything broke.
  # The comment three lines above already prescribed the fix — "FULL sha to head_sha" — and the
  # implementation never did it. Code diverged from its own documented route, silently, and the
  # only witness was a tripwire nobody had re-read.
  full_sha=$(git -C "$FP_REPO" rev-parse "$sha" 2>/dev/null || printf '%s' "$sha")
  api="https://api.github.com/repos/shroobm/file-portal/actions/runs?per_page=20&head_sha=$full_sha"
  body=$(curl -s --max-time 25 -H "Authorization: Bearer $tok" -H "Accept: application/vnd.github+json" "$api" 2>/dev/null)
  if [ -z "$body" ]; then
    row "CI" "UNREAD — GitHub did not answer; NOT a statement that CI is green"
  else
    verdict=$(printf '%s' "$body" | "$PY" -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: print('PARSE-FAIL'); raise SystemExit
sha=sys.argv[1]
for r in d.get('workflow_runs',[]):
    if r.get('head_sha','').startswith(sha[:8]):
        print(f\"{r.get('status')}|{r.get('conclusion')}\"); break
else: print('NO-RUN')
" "$sha" 2>/dev/null)
    case "$verdict" in
      completed\|success) row "CI" "success on ${sha:0:8} (observed, not assumed)" ;;
      completed\|*)       row "CI" "RED — ${verdict#*|} on ${sha:0:8}: fix before the ledger row"; red=1 ;;
      in_progress*|queued*) row "CI" "still running on ${sha:0:8} — close may proceed; CHECK IT AFTER" ;;
      NO-RUN)  row "CI" "no run for ${sha:0:8} yet (unpushed? ahead=$ahead) — NOT a green" ;;
      *)       row "CI" "UNREAD — could not parse GitHub's answer; NOT a statement that CI is green" ;;
    esac
  fi
fi

# ── [5] LEVERS — the modularity gate (docs/18 §2, signed Rab S106 2026-08-21) ───────────────
#
# "A number that decides something is a LEVER, not a constant." This reports threshold-shaped
# constants ADDED since the pin that carry no lever and no waiver. It prints VALUES and never
# blocks: the judgment stays the author's, but it can no longer be silent. Waive in-line with
# a trailing `# lever-waiver: <who may change it, what evidence would move it>`.
lev_added=""
lev_n=0
if git -C "$FP_REPO" rev-parse --verify -q "$PIN" >/dev/null 2>&1; then
  while IFS= read -r line; do
    case "$line" in
      +++*|---*) continue ;;
    esac
    body="${line#+}"
    case "$body" in
      # docs/18 §2 step 5 requires a waiver to NAME who may change it and what evidence would
      # move it. A bare `# lever-waiver:` silenced the gate — the half of the law that gives it
      # meaning. Require substance after the colon (S106 Circle, Lane C).
      *lever-waiver:*[!\ ]*) continue ;;
      \#*|" "*\#*) ;;
    esac
    # THREE declaration forms, because the glob claims three languages. The first build matched
    # only Python's, so it saw 0 of 5 Rust and 0 of 10 JS constants in this repo while the
    # closeout claimed it "sees NAME = <number> in Python/Rust/JS" — the documented blind spot
    # was a strict subset of the real one (S106 Circle, Lane C census: 53 of 72 = 74 %).
    #   py:  NAME = 0.42            rs:  (pub) const|static NAME: f64 = 0.42;
    #   js:  const|let|var NAME = 0.42;      also 1e-3 / .35 exponent+bare-dot forms
    if printf '%s' "$body" | grep -Eq '^[[:space:]]*(pub[[:space:]]+)?(const|static|let|var)?[[:space:]]*_?[A-Z][A-Z0-9_]{2,}[[:space:]]*(:[[:space:]]*[A-Za-z0-9_]+)?[[:space:]]*=[[:space:]]*-?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][-+]?[0-9]+)?[[:space:]]*;?[[:space:]]*((//|#).*)?$'; then
      name="$(printf '%s' "$body" | sed -E 's/^[[:space:]]*(pub[[:space:]]+)?(const|static|let|var)?[[:space:]]*(_?[A-Z][A-Z0-9_]*).*/\3/')"
      case "$name" in
        *_RE|*_FILE|*_DIR|*_PATH|*_ALLOWED) continue ;;
      esac
      lev_n=$((lev_n + 1))
      [ "$lev_n" -le 4 ] && lev_added="${lev_added}${lev_added:+ · }${name}"
    fi
  done <<EOF
$(git -C "$FP_REPO" diff "$PIN..HEAD" -- '*.py' '*.rs' '*.js' 2>/dev/null | grep '^+' || true)
EOF
  if [ "$lev_n" -gt 0 ]; then
    row "LEVERS" "$lev_n threshold-shaped constant(s) added since $PIN with no lever, no waiver: $lev_added$([ "$lev_n" -gt 4 ] && echo ' …')"
    row "" "docs/18 §2: a number that decides something is a lever. Convert, or add '# lever-waiver: <who/what evidence>'"
  else
    row "LEVERS" "no unlevered threshold constants added since $PIN"
  fi
else
  row "LEVERS" "UNREAD — pin $PIN unresolvable; NOT a statement that none were added"
fi

# ── [6] DOCTOR — the artifact vs the measurement that justified it (S108, atlas rank 1) ─────
# S108: warn-only for one session, arm next close.
#
# S106's own words: "the one check the governance layer still lacks is comparing the
# artifact to the measurement" — that session shipped a triage rule its code did not
# implement, and every tripwire stayed honestly green while the record was wrong. Wave 1,
# signed scope:
#   (a) lever-name parity: every threshold the operator file NAMES must actually be read
#       by the consumer. Grep-level and READ-ONLY — runs nothing, writes nothing.
#   (b) closeout-headline re-runs: not yet mechanized — reported UNREAD, never green.
DOC_LEVERS="${FP_DOCTOR_LEVERS:-$HOME/ml/library/figure-triage.txt}"
DOC_CODE="${FP_DOCTOR_CODE:-$FP_REPO/windows-converter/figure_coverage.py}"
DOC_GREP="${FP_DOCTOR_GREP:-grep}"
if [ ! -f "$DOC_LEVERS" ]; then
  row "DOCTOR" "UNREAD — lever file absent at $DOC_LEVERS; NOT a statement of parity"
elif [ ! -f "$DOC_CODE" ]; then
  row "DOCTOR" "UNREAD — consumer absent at $DOC_CODE; NOT a statement of parity"
else
  # Parse completeness is part of the measurement. Dropping one declaration line and then
  # shrinking the denominator to the successfully parsed subset is a false green.
  doc_source=$(tr -d '\r' < "$DOC_LEVERS" | sed -E 's/[[:space:]]*#.*$//' | sed '/^[[:space:]]*$/d')
  doc_rows=$(printf '%s\n' "$doc_source" | awk 'NF { n++ } END { print n+0 }')
  doc_names=$(printf '%s\n' "$doc_source" | sed -nE 's/^[[:space:]]*([a-z][a-z0-9_]*)[[:space:]]*=.*/\1/p')
  doc_parsed=$(printf '%s\n' "$doc_names" | awk 'NF { n++ } END { print n+0 }')
  doc_unique=$(printf '%s\n' "$doc_names" | sed '/^$/d' | sort -u | awk 'NF { n++ } END { print n+0 }')
  if [ "$doc_rows" -eq 0 ]; then
    row "DOCTOR" "UNREAD — 0 lever names parsed from $DOC_LEVERS; NOT a statement of parity"
  elif [ "$doc_rows" -ne "$doc_parsed" ] || [ "$doc_parsed" -ne "$doc_unique" ]; then
    row "DOCTOR" "UNREAD — lever parse incomplete/ambiguous: non-comment rows $doc_rows · parsed $doc_parsed · unique $doc_unique"
    row "" "every declaration must be one unique lower_snake_case key=value row; denominator was NOT shrunk"
  else
    doc_match=""; doc_miss=""; doc_m=0; doc_x=0; doc_probe_bad=0
    while IFS= read -r lname; do
      [ -z "$lname" ] && continue
      if "$DOC_GREP" -Fq "\"$lname\"" "$DOC_CODE"; then
        doc_m=$((doc_m + 1)); doc_match="${doc_match}${doc_match:+ · }${lname}"
      else
        doc_rc=$?
        if [ "$doc_rc" -eq 1 ]; then
          doc_x=$((doc_x + 1)); doc_miss="${doc_miss}${doc_miss:+ · }${lname}"
        else
          doc_probe_bad=$doc_rc
          break
        fi
      fi
    done <<EOF
$doc_names
EOF
    if [ "$doc_probe_bad" -ne 0 ]; then
      row "DOCTOR" "UNREAD — consumer reference probe exited $doc_probe_bad; NOT a statement that names are absent"
    else
      row "DOCTOR" "lever lexical parity: $(basename "$DOC_LEVERS") names $doc_parsed · quoted refs $doc_m · MISSING $doc_x"
      [ -n "$doc_match" ] && row "" "LEXICAL REF: $doc_match"
      row "" "UNREAD — a quoted lexical occurrence does NOT prove the consumer reads the lever; gate remains unarmed"
    fi
    if [ "$doc_probe_bad" -eq 0 ] && [ "$doc_x" -gt 0 ]; then
      row "" "MISSING: $doc_miss — named in the operator file, never read by $(basename "$DOC_CODE")"
      row "" "the operator can turn a knob no code is holding — S108: warn-only for one session, arm next close"
    fi
  fi
fi
row "DOCTOR-HEAD" "UNREAD — closeout-headline probe re-run not yet mechanized; NOT a statement the numbers reproduce"

# ── [7] CENSUS — promised tripwires vs executed (S108, atlas rank 2) ────────────────────────
# S108: warn-only for one session, arm next close.
#
# docs/32 §5 rule 2: a guard nobody watched fire is a proxy with a reputation. The census
# checks that a suite EXECUTES every tripwire it declares — a planted red that never runs
# protects nothing while its banner stays green. Wave 1, signed: the wiki suite, which
# declares fixtures as `# ---- T<n>` headers and prints its own `ALL TRIPWIRES FIRED — N/N`.
# Broader census over *TEST-STRATEGY* docs: not yet mechanized — UNREAD, never assumed whole.
CEN_SUITE="${FP_CENSUS_SUITE:-$FP_REPO/.claude/skills/wiki/selftest.sh}"
if [ ! -f "$CEN_SUITE" ]; then
  row "CENSUS" "UNREAD — suite absent at $CEN_SUITE; NOT a statement its tripwires are whole"
else
  cen_decl_ids=$(tr -d '\r' < "$CEN_SUITE" | sed -nE 's/^# ---- (T[0-9]+):.*/\1/p')
  cen_decl=$(printf '%s\n' "$cen_decl_ids" | awk 'NF { n++ } END { print n+0 }')
  cen_decl_unique=$(printf '%s\n' "$cen_decl_ids" | sed '/^$/d' | sort -u | awk 'NF { n++ } END { print n+0 }')
  cen_out=$(bash "$CEN_SUITE" 2>&1); cen_rc=$?
  cen_frac_lines=$(printf '%s\n' "$cen_out" | sed -nE 's/^ALL TRIPWIRES FIRED — ([0-9]+\/[0-9]+)(, exit 0)?$/\1/p')
  cen_banner_n=$(printf '%s\n' "$cen_frac_lines" | awk 'NF { n++ } END { print n+0 }')
  cen_frac=$(printf '%s\n' "$cen_frac_lines" | sed -n '1p')
  cen_pass="${cen_frac%/*}"; cen_total="${cen_frac#*/}"
  cen_fired_ids=$(printf '%s\n' "$cen_out" | sed -nE 's/^TRIPWIRE (T[0-9]+) FIRED$/\1/p')
  cen_fired=$(printf '%s\n' "$cen_fired_ids" | awk 'NF { n++ } END { print n+0 }')
  cen_fired_unique=$(printf '%s\n' "$cen_fired_ids" | sed '/^$/d' | sort -u | awk 'NF { n++ } END { print n+0 }')
  cen_missing=$(comm -23 <(printf '%s\n' "$cen_decl_ids" | sed '/^$/d' | sort -u) <(printf '%s\n' "$cen_fired_ids" | sed '/^$/d' | sort -u) | tr '\n' ' ')
  cen_extra=$(comm -13 <(printf '%s\n' "$cen_decl_ids" | sed '/^$/d' | sort -u) <(printf '%s\n' "$cen_fired_ids" | sed '/^$/d' | sort -u) | tr '\n' ' ')
  if [ "$cen_rc" -ne 0 ]; then
    row "CENSUS" "RED-WARN — $(basename "$CEN_SUITE") itself exited $cen_rc; its last line: $(printf '%s' "$cen_out" | tail -1)"
    row "" "S108: warn-only for one session, arm next close"
  elif [ "$cen_decl" -eq 0 ] || [ "$cen_decl" -ne "$cen_decl_unique" ]; then
    row "CENSUS" "UNREAD — declaration IDs absent/duplicated: rows $cen_decl · unique $cen_decl_unique"
  elif [ "$cen_banner_n" -ne 1 ] || [ -z "$cen_frac" ]; then
    row "CENSUS" "UNREAD — expected exactly one anchored 'ALL TRIPWIRES FIRED — N/N' banner; observed $cen_banner_n"
  elif [ "${#cen_pass}" -gt 9 ] || [ "${#cen_total}" -gt 9 ]; then
    row "CENSUS" "UNREAD — banner integers exceed the bounded parser; NOT a green"
  elif [ "$cen_fired" -ne "$cen_fired_unique" ] || [ "$cen_fired_unique" -ne "$cen_decl_unique" ] || [ -n "$cen_missing$cen_extra" ]; then
    row "CENSUS" "RED-WARN — declaration/flight mismatch: declared $cen_decl_unique · unique FIRED markers $cen_fired_unique"
    [ -n "$cen_missing" ] && row "" "MISSING FIRED: $cen_missing"
    [ -n "$cen_extra" ] && row "" "UNDECLARED FIRED: $cen_extra"
    row "" "S108: warn-only for one session, arm next close"
  elif [ "$cen_pass" -le 0 ] || [ "$cen_pass" -ne "$cen_total" ] || [ "$cen_total" -ne "$cen_decl_unique" ]; then
    row "CENSUS" "RED-WARN — declared $cen_decl_unique · FIRED $cen_fired_unique · banner $cen_frac; require positive numerator = denominator = declarations"
    row "" "S108: warn-only for one session, arm next close"
  else
    row "CENSUS" "$(basename "$CEN_SUITE"): declared $cen_decl_unique = FIRED $cen_fired_unique = banner $cen_frac (exit 0)"
  fi
fi
row "CENSUS-SCOPE" "UNREAD — broader TEST-STRATEGY fixture census not yet mechanized; NOT a statement all promised tripwires ran"

# ── [8] REGISTERS — Rab's rule, signed S109: "closing sessions adds upon it" ────────────────
#
# OPEN-TASKS.md existed from S107 and NOTHING in the protocol referenced it — 0 hits across
# SKILL.md, open.sh and close.sh, measured. A session could add ten items' worth of debt and
# close green without writing one of them down, which is how a register becomes a museum.
#
# WARN-ONLY for one session (the S108 convention for a new gate), then arm.
TASKS_MD="$FP_REPO/OPEN-TASKS.md"
if [ ! -f "$TASKS_MD" ]; then
  row "REGISTER" "UNREAD — OPEN-TASKS.md is missing; that is not 'nothing open'"
elif git -C "$FP_REPO" diff --quiet "$PIN"..HEAD -- OPEN-TASKS.md 2>/dev/null; then
  row "REGISTER" "WARN — OPEN-TASKS.md UNTOUCHED since $PIN. Every session either strikes an item"
  row "" "or adds one; a session that did neither must SAY SO in its closeout, not imply it."
  row "" "S109: warn-only for one session, arm next close"
else
  reg_add=$(git -C "$FP_REPO" diff --numstat "$PIN"..HEAD -- OPEN-TASKS.md 2>/dev/null | awk '{print $1}')
  reg_del=$(git -C "$FP_REPO" diff --numstat "$PIN"..HEAD -- OPEN-TASKS.md 2>/dev/null | awk '{print $2}')
  row "REGISTER" "OPEN-TASKS.md written this session: +${reg_add:-?} / -${reg_del:-?} lines"
fi

# ── [8b] DEBT GATE — OPEN-TASKS.md §A21, proposed 2026-08-22 and never built until now ──────
#
# Its own words: "refuse a new governance artifact while the OPEN SYM count exceeds its value at
# the last close. ~3 lines". docs/45's M5 finding is that this project produces governance faster
# than output, and the register that records that is itself a governance artifact. This is the
# only mechanism anyone proposed to bound it, and it sat unbuilt in the list it would bound.
#
# It PRINTS, it does not block: a threshold that stops a close on its first run would be tuned
# away by the second. The number is the point — an OPEN count that only rises is visible here.
SYMS_MD="$FP_REPO/SYMPTOM-INDEX.md"
if [ -f "$SYMS_MD" ]; then
  sym_open=$(grep -oU '| `open`' "$SYMS_MD" 2>/dev/null | grep -c . || echo 0)
  sym_open_pin=$(git -C "$FP_REPO" show "$PIN:SYMPTOM-INDEX.md" 2>/dev/null | grep -oU '| `open`' | grep -c . || echo "?")
  if [ "$sym_open_pin" = "?" ]; then
    row "DEBT" "open SYM now $sym_open · at $PIN UNREAD — no verdict on the trend"
  elif [ "$sym_open" -gt "$sym_open_pin" ]; then
    row "DEBT" "open SYM $sym_open_pin -> $sym_open (+$((sym_open - sym_open_pin))) — this session"
    row "" "ADDED net debt. §A21: justify a new governance artifact or work one down."
  elif [ "$sym_open" -lt "$sym_open_pin" ]; then
    row "DEBT" "open SYM $sym_open_pin -> $sym_open (-$((sym_open_pin - sym_open))) — debt fell"
  else
    row "DEBT" "open SYM $sym_open, unchanged since $PIN"
  fi
else
  row "DEBT" "UNREAD — no SYMPTOM-INDEX.md; NOT a statement that debt is flat"
fi

# ── [9] PUSH — an unpushed close is how the 2026-08-16 fork grew 52 commits deep ────────────
row "PUSH" "ahead of upstream: $ahead (the close pushes; 0 after)"

printf '════════ close exit %d — values only; the judgment half is SKILL.md ════════\n' "$red"
exit "$red"
