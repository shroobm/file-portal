#!/usr/bin/env bash
# dumps/dump.sh — the ONLY writer of dumps/LEDGER.md.
#
# Why a script and not a convention: a hand-typed id or digest is a future SYM-039. The id, the
# UTC stamp and the sha256 are all derivable, so none of them is typed. docs/21 §3: nothing
# derivable is written by hand.
#
#   bash dumps/dump.sh <category> "<subject>" <file>
#   <producer> | bash dumps/dump.sh evidence "<subject>" -
#
# Categories: qa | coordination | evidence | transcripts
#
# Writes the bytes into dumps/<category>/, appends ONE row to LEDGER.md, and prints a
# pointer+digest line shaped for pasting into relay.md.
set -u

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ledger="$here/LEDGER.md"

die() { printf 'dump: %s\n' "$1" >&2; exit 1; }

[ $# -ge 3 ] || die "usage: dump.sh <qa|coordination|evidence|transcripts> \"<subject>\" <file|->"

cat_in="$1"; subject="$2"; src="$3"
case "$cat_in" in
  qa|coordination|evidence|transcripts) : ;;
  *) die "unknown category '$cat_in' (qa|coordination|evidence|transcripts)" ;;
esac
[ -d "$here/$cat_in" ] || die "category dir missing: dumps/$cat_in"

# --- author lane: declared, never guessed -------------------------------------------------
lane="${DUMP_LANE:-}"
[ -n "$lane" ] || die "set DUMP_LANE (e.g. DUMP_LANE=Fable) — a dump with no author is unattributable"

# --- next id: derived from the ledger, at write time (SYM-045: re-read the counter NOW) ----
last=$(grep -oE '^\| D[0-9]{4} ' "$ledger" 2>/dev/null | grep -oE '[0-9]{4}' | sort -n | tail -1)
[ -n "${last:-}" ] || last=0
id=$(printf 'D%04d' $((10#$last + 1)))

ts=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
day=$(date -u '+%Y%m%d')

# --- slug the subject for a filename ------------------------------------------------------
slug=$(printf '%s' "$subject" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//; s/-$//' | cut -c1-60)
[ -n "$slug" ] || slug="untitled"

ext="md"
if [ "$src" != "-" ]; then
  [ -f "$src" ] || die "no such file: $src"
  case "$src" in *.*) ext="${src##*.}" ;; esac
fi
name="${id}-${day}-${slug}.${ext}"
dest="$here/$cat_in/$name"
part="$here/$cat_in/.part-${name}"

# --- ATOMIC: write .part- then rename. A reader never sees a torn file. -------------------
if [ "$src" = "-" ]; then
  cat > "$part" || die "could not write $part"
else
  cp "$src" "$part" || die "could not copy $src"
fi
[ -s "$part" ] || { rm -f "$part"; die "refusing to record an EMPTY dump — nothing was captured"; }

bytes=$(wc -c < "$part" | tr -d ' ')
sha=$(sha256sum "$part" | cut -d' ' -f1)
mv -f "$part" "$dest" || die "rename failed"

# --- ledger row: APPENDED, never rewritten -----------------------------------------------
if [ ! -f "$ledger" ]; then die "LEDGER.md missing — refusing to create it silently"; fi
printf '| %s | %s | %s | %s | %s | %s | `%s` |\r\n' \
  "$id" "$ts" "$lane" "$cat_in" "$subject" "$bytes" "$sha" >> "$ledger"

# --- the pointer, shaped for the bus ------------------------------------------------------
printf '\n'
printf 'DUMPED  %s  %s bytes\n' "$id" "$bytes"
printf '  path    dumps/%s/%s\n' "$cat_in" "$name"
printf '  sha256  %s\n' "$sha"
printf '  ledger  row appended (tracked — survives the bytes)\n'
printf '\n'
printf 'For relay.md — pointer + digest, bytes never cross the bus:\n'
printf '  **DUMP %s** · `dumps/%s/%s` · `sha256:%s` · %s bytes · ⟨%s⟩ %s\n' \
  "$id" "$cat_in" "$name" "$sha" "$bytes" "$lane" "$ts"
