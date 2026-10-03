# Label corrections — every existing comment or docstring line a labelling wave corrected or deleted

**Why this file exists (Rab, Desk, 2026-10-03 20:53:49Z, verbatim):** "Make sure it's accurate please for the love of god
and don't mess up anything you don't want messing you up into the future without the right guard rails so that you know
that it was changed and what it was changed from and to in future sessions." His earlier word (20:39:08Z): "Anything that
is not an accurate description can be deleted and changed."

So: a labelling wave (S218 E8, 2026-10-03: Sonnet lanes adding docstrings, section labels and block comments under
`observability/label_gate.py` / `line_gate.py`, which prove every code line identical to HEAD) may correct or delete an
existing comment line that no longer describes the code — and every such change is a row HERE, in the same commit as the
change: the file, the old line verbatim, the new line verbatim (or `DELETED`), the code line that proves the old text
wrong, the wave, who made it, the commit. A future session reads the from→to here instead of diffing old commits.

**The guard rail:** `observability/label_corrections_check.py` re-reads every row against the working tree — every `NEW:`
line must be present in the file as a whole line, and no `OLD:` line may remain — and exits 1 on any mismatch (its
`--selftest` feeds it a true row, a false row and a deleted row). A row that stops matching means the file moved on
without this register: fix the register in the same commit, never the check.

**Format (parsed by the check; keep it exact):** a `### C-nnn · <path> · <wave/author> · <commit>` heading, then one or
more `OLD: ` lines (the old text, whitespace-stripped, one per original line), then one or more `NEW: ` lines (the new
text, one per new line; the single word `DELETED` when the line was removed), then a `PROOF: ` line (the code line that
proves the old text wrong) and a `WHY: ` line in plain words. Private files have their own register in the private repo
(`sittings/S218/label_corrections_private.md`, same format, checked with `--repo` and the register path).

### C-001 · windows-widget/src-tauri/src/assay.rs · wave 3 (by hand, 20:41Z) · e386777
OLD: // evidence card. (Read-only, no state — as first written; since then set_mode, reconvert and bless write
OLD: // audit-mode.txt, drop/.supersede and the bless receipts: see the block above.) Terracotta is the UI's to spend — this only reports.
NEW: // evidence card. Its writes are the header's list (audit-mode.txt; drop/.supersede/<source>.json and a copy of the
NEW: // PDF into drop/<source> for a reconvert; the bless receipt, which bless also scp's to the vault host); reanalyze
NEW: // spawns the converter, and reconvert/bless remove the files they made. Terracotta is the UI's to spend — this only reports.
PROOF: `fs::write(` of audit-mode.txt (set_mode); `fs::copy(&src, &dest)` into drop/<source> and the supersede marker (reconvert); `spawn_supervised(&mut cmd)` (reanalyze); `Command::new("scp")` and the bless receipt write (bless); `fs::remove_file` in reconvert and bless - the functions in the same file.
WHY: the header still called the module "read-only, no state" with a parenthetical admitting it was no longer true; his word of 20:39Z. The first NEW of 20:41Z ("everything else is a read") was itself wrong - the wave-4 truth check (Opus, 21:16Z) named the copy, the spawn, the scp and the removes; rewritten here before the commit.

### C-005 · windows-widget/src-tauri/src/assay.rs · wave 4, the truth check (Opus) via the session · (this commit)
OLD: // S31: the Assay — the Survival Audit's read side (docs/15 §13). Pure projection: Python
NEW: // S31: the Assay — the Survival Audit's read side (docs/15 §13), a projection plus the writes listed above: Python
PROOF: the module's own header line "Writes: audit-mode.txt, drop/.supersede/<source>.json, drop/<source>, a temporary .bless-<sha16>.json" and the `fs::write` / `fs::copy` / `scp` calls below.
WHY: "Pure projection" was true at S31 and is not now; the line kept the S31 history and gained the qualifier.

### C-002 · coordination/relay_numerations.py · wave 4, lane D02 (Sonnet) · (this commit)
OLD: # NR-13/14: the watcher's signals and the handler's turnaround need a signal log the watcher does not yet write
NEW: # NR-13/14: the watcher's signals and the handler's turnaround, read from the watcher's signal log
PROOF: `log = HERE / "private" / "relay-watch.log"` and `if log.exists(): parsed = [stamp.match(...) for line in io.open(log, ...)]` read that log; the next comment line says the tracked watcher writes it.
WHY: the comment said the log does not yet exist; the code below it reads the log.

### C-003 · .claude/hooks/warn_heredoc_selftest.py · wave 4, lane H01 (Sonnet) · (this commit)
OLD: a backslash, a backtick or a `$` → the ERR-054 warning; a plain `python -c "print(1)"` → silence — the NEGATIVE CONTROL; a
NEW: a backslash or a `$` → DENIED since S213, a backtick alone → the ERR-054 warning; a plain `python -c "print(1)"` →
NEW: silence — the NEGATIVE CONTROL; a
PROOF: warn_heredoc.py: `block_hits = sorted({h for prog in dash_c for h in re.findall(r"\\|\$", prog)})` then `if block_hits:` prints permissionDecision "deny".
WHY: since S213 a backslash or a `$` inside `python -c` is DENIED, not warned; the selftest's docstring still described the S170 warn-only posture.

### C-004 · docs/54-repair-road/scripts/A-ladder2_and_attribution.py · wave 4, the truth check (Opus) via the session · (this commit)
OLD: # character, same as ladder.py's step-1). Kept as its own function so this file does not import
NEW: # character except a newline (no re.DOTALL), same as ladder.py's step-1). Kept as its own function so this file does not import
PROOF: `return re.sub(r"\\(.)", r"\1", t)` - `.` without re.DOTALL does not match a newline, so a backslash ending a line is kept.
WHY: the comment (and the new docstring under it, corrected in the same edit) said "ANY single character"; a newline is the exception.
