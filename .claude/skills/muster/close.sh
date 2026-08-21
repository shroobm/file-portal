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
  api="https://api.github.com/repos/shroobm/file-portal/actions/runs?per_page=20"
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
      *lever-waiver:*) continue ;;
      \#*|" "*\#*) ;;
    esac
    # a module-level CONSTANT bound to a bare number: NAME = 1.23 / NAME = 45
    if printf '%s' "$body" | grep -Eq '^_?[A-Z][A-Z0-9_]{2,}[[:space:]]*=[[:space:]]*-?[0-9]+(\.[0-9]+)?[[:space:]]*(#.*)?$'; then
      name="$(printf '%s' "$body" | sed -E 's/^(_?[A-Z][A-Z0-9_]*).*/\1/')"
      case "$name" in
        *_RE|*_FILE|*_DIR|*_PATH|*_NAME|*_DEFAULT|*_ALLOWED) continue ;;
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

# ── [6] PUSH — an unpushed close is how the 2026-08-16 fork grew 52 commits deep ────────────
row "PUSH" "ahead of upstream: $ahead (the close pushes; 0 after)"

printf '════════ close exit %d — values only; the judgment half is SKILL.md ════════\n' "$red"
exit "$red"
