#!/usr/bin/env bash
# wiki.sh — the mechanical half of the /wiki skill (judgment half: SKILL.md).
#
# Subcommands:
#   check                      verify the whole wiki against its laws (the gate)
#   stale                      list pages whose verification stamp lags HEAD
#   new <slug> "<title>" <section>     scaffold a new page + print its INDEX line
#   new-profile <name>         scaffold a profile pair (public + gitignored private)
#
# Design laws enforced here (the numbers ARE the contract; see SKILL.md for why):
#   INDEX.md  <= 120 lines — the map must stay readable in one gulp
#   pages     <= 200 lines — a page that outgrows this splits or points
#   every page listed in INDEX; every relative link resolves
#   frontmatter: title / section / last-verified / verified-against / sources
#   *.private.md is NEVER tracked (the repo is PUBLIC) — a tracked one is a red
#
# Exit discipline (muster convention): only a MEASURED red exits 1.
# UNREAD is reported as UNREAD and never claims clean — and never blocks.

set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
WIKI_ROOT="${WIKI_ROOT:-$REPO_ROOT/wiki}"
INDEX="$WIKI_ROOT/INDEX.md"
INDEX_CAP=120
PAGE_CAP=200

REDS=0; UNREADS=0
red()    { echo "  RED     $*"; REDS=$((REDS+1)); }
ok()     { echo "  ok      $*"; }
unread() { echo "  UNREAD  $*"; UNREADS=$((UNREADS+1)); }

is_default_root() { [ "$WIKI_ROOT" = "$REPO_ROOT/wiki" ]; }

# Strip CR so CRLF files measure the same as LF (SYM-029 class).
lines_of() { tr -d '\r' < "$1" | wc -l | tr -d ' '; }

list_pages() {
  # Every governed page: wiki/*.md and wiki/profiles/*.md, minus INDEX and private layers.
  find "$WIKI_ROOT" -maxdepth 2 -name '*.md' 2>/dev/null \
    | grep -v '/INDEX\.md$' | grep -v '\.private\.md$' | sort
}

cmd_check() {
  echo "wiki check — root: $WIKI_ROOT"

  # -- the map itself
  if [ ! -f "$INDEX" ]; then
    red "INDEX.md missing at $INDEX"
  else
    n=$(lines_of "$INDEX")
    if [ "$n" -gt "$INDEX_CAP" ]; then red "INDEX.md is $n lines (cap $INDEX_CAP) — compact it; the map must stay one gulp"
    else ok "INDEX.md $n/$INDEX_CAP lines"; fi
  fi

  # -- every page: caps, frontmatter, membership
  while IFS= read -r page; do
    [ -z "$page" ] && continue
    base="${page#$WIKI_ROOT/}"
    n=$(lines_of "$page")
    if [ "$n" -gt "$PAGE_CAP" ]; then red "$base is $n lines (cap $PAGE_CAP)"; fi
    for field in title: section: last-verified: verified-against:; do
      if ! head -12 "$page" | tr -d '\r' | grep -q "^$field"; then
        red "$base missing frontmatter field '$field'"
      fi
    done
    if [ -f "$INDEX" ] && ! tr -d '\r' < "$INDEX" | grep -q "$base"; then
      red "$base not listed in INDEX.md — an unmapped page is invisible"
    fi
  done <<EOF
$(list_pages)
EOF

  # -- every INDEX target exists
  if [ -f "$INDEX" ]; then
    while IFS= read -r target; do
      [ -z "$target" ] && continue
      case "$target" in http*|\#*) continue;; esac
      t="${target%%#*}"
      if [ ! -e "$WIKI_ROOT/$t" ] && [ ! -e "$REPO_ROOT/$t" ]; then
        red "INDEX.md links to '$t' which does not exist"
      fi
    done <<EOF
$(tr -d '\r' < "$INDEX" | grep -oE '\]\([^)]+\)' | sed 's/^](//;s/)$//')
EOF
  fi

  # -- relative links inside pages resolve (same-dir, wiki-root, or repo-root)
  while IFS= read -r page; do
    [ -z "$page" ] && continue
    base="${page#$WIKI_ROOT/}"; dir="$(dirname "$page")"
    while IFS= read -r target; do
      [ -z "$target" ] && continue
      case "$target" in http*|\#*|mailto*) continue;; esac
      t="${target%%#*}"
      if [ ! -e "$dir/$t" ] && [ ! -e "$WIKI_ROOT/$t" ] && [ ! -e "$REPO_ROOT/$t" ]; then
        red "$base links to '$t' which does not resolve"
      fi
    done <<EOF2
$(tr -d '\r' < "$page" | grep -oE '\]\([^)]+\)' | sed 's/^](//;s/)$//')
EOF2
  done <<EOF
$(list_pages)
EOF

  # -- the privacy gate: no *.private.md may be tracked (repo is PUBLIC)
  if is_default_root && command -v git >/dev/null 2>&1; then
    tracked_private=$(cd "$REPO_ROOT" && git ls-files 'wiki/**.private.md' 'wiki/*.private.md' 2>/dev/null)
    if [ -n "$tracked_private" ]; then
      red "PRIVATE LAYER TRACKED IN A PUBLIC REPO: $tracked_private — untrack immediately"
    else
      ok "no private layer tracked"
    fi
  else
    unread "privacy gate (needs git + default root)"
  fi

  # -- verification stamps are real ancestors, not invented SHAs
  if is_default_root && command -v git >/dev/null 2>&1; then
    while IFS= read -r page; do
      [ -z "$page" ] && continue
      base="${page#$WIKI_ROOT/}"
      sha=$(head -12 "$page" | tr -d '\r' | grep '^verified-against:' | awk '{print $2}' | tr -d '"'"'"'')
      if [ -n "$sha" ] && ! (cd "$REPO_ROOT" && git merge-base --is-ancestor "$sha" HEAD 2>/dev/null); then
        red "$base verified-against $sha is not an ancestor of HEAD — a stamp that lies"
      fi
    done <<EOF
$(list_pages)
EOF
  else
    unread "stamp-ancestry gate (needs git + default root)"
  fi

  echo
  if [ "$REDS" -gt 0 ]; then
    echo "RESULT: $REDS red(s), $UNREADS unread — FAILING (exit 1)"; exit 1
  elif [ "$UNREADS" -gt 0 ]; then
    echo "RESULT: 0 reds, $UNREADS unread — PASSING, NOT claiming clean"; exit 0
  else
    echo "RESULT: CLEAN (measured)"; exit 0
  fi
}

cmd_stale() {
  head_sha=$(cd "$REPO_ROOT" && git rev-parse --short HEAD 2>/dev/null)
  [ -z "$head_sha" ] && { echo "UNREAD: git unavailable"; exit 0; }
  echo "HEAD is $head_sha — pages verified against older commits:"
  found=0
  while IFS= read -r page; do
    [ -z "$page" ] && continue
    sha=$(head -12 "$page" | tr -d '\r' | grep '^verified-against:' | awk '{print $2}' | tr -d '"'"'"'')
    d=$(head -12 "$page" | tr -d '\r' | grep '^last-verified:' | awk '{print $2}' | tr -d '"'"'"'')
    if [ -n "$sha" ] && [ "$sha" != "$head_sha" ]; then
      echo "  ${page#$WIKI_ROOT/}  (verified-against $sha, last-verified ${d:-?})"; found=1
    fi
  done <<EOF
$(list_pages)
EOF
  [ "$found" -eq 0 ] && echo "  none — every stamp is at HEAD"
  exit 0
}

cmd_new() {
  slug="$1"; title="$2"; section="$3"
  out="$WIKI_ROOT/$slug.md"
  [ -f "$out" ] && { echo "REFUSED: $out exists"; exit 1; }
  head_sha=$(cd "$REPO_ROOT" && git rev-parse --short HEAD 2>/dev/null || echo UNKNOWN)
  today=$(date -u +%Y-%m-%d)
  cat > "$out" <<PAGE
---
title: $title
section: $section
last-verified: $today
verified-against: $head_sha
sources: []
---

> **Summary.** One paragraph: what this page is, for a reader who reads nothing else.

## Open items

- (pointers into OPEN-TASKS.md / SYMPTOM-INDEX.md only — never duplicates)
PAGE
  echo "scaffolded $out"
  echo "ADD THIS LINE to INDEX.md under '$section' (placement is judgment, not automation):"
  echo "- [$title]($slug.md) — <one-line hook>"
}

cmd_new_profile() {
  name="$1"
  pub="$WIKI_ROOT/profiles/$name.md"; priv="$WIKI_ROOT/profiles/$name.private.md"
  [ -f "$pub" ] && { echo "REFUSED: $pub exists"; exit 1; }
  if ! (cd "$REPO_ROOT" && git check-ignore "wiki/profiles/$name.private.md" >/dev/null 2>&1); then
    echo "RED: wiki/profiles/*.private.md is NOT gitignored — fix .gitignore before creating profiles."
    echo "The repo is public; refusing to scaffold a private layer that would be tracked."
    exit 1
  fi
  head_sha=$(cd "$REPO_ROOT" && git rev-parse --short HEAD 2>/dev/null || echo UNKNOWN)
  today=$(date -u +%Y-%m-%d)
  cat > "$pub" <<PAGE
---
title: Profile — $name
section: Profiles
last-verified: $today
verified-against: $head_sha
sources: []
---

> **$name** — role, working agreements, and interfaces. Personal content lives in the
> gitignored private layer, never here: this repository is public.

## Role
## Working agreements
## Signature domains (what only $name decides)
## Interfaces (where to reach them, where they read)

## Open items
PAGE
  cat > "$priv" <<PAGE
# $name — private layer (GITIGNORED — verify with: git check-ignore $priv)
# Personal notes, co-written with any model. Never committed, never pushed.
PAGE
  echo "scaffolded $pub and $priv (private layer confirmed ignored)"
  echo "ADD to INDEX.md Profiles section: - [Profile — $name](profiles/$name.md) — <hook>"
}

case "${1:-}" in
  check)        cmd_check ;;
  stale)        cmd_stale ;;
  new)          [ $# -ge 4 ] || { echo "usage: wiki.sh new <slug> \"<title>\" <section>"; exit 1; }
                cmd_new "$2" "$3" "$4" ;;
  new-profile)  [ $# -ge 2 ] || { echo "usage: wiki.sh new-profile <name>"; exit 1; }
                cmd_new_profile "$2" ;;
  *) echo "usage: wiki.sh {check|stale|new <slug> \"<title>\" <section>|new-profile <name>}"; exit 1 ;;
esac
