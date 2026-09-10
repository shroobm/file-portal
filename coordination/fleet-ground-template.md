# Fleet ground — the mandatory preamble (docs/47, MODE CHECK from J56)

Copy this block into the top of every fleet GROUND file (the scratchpad brief each lane is told to read).
It is the enforcement of docs/47 §3 (GROUND, DEVIATION-IS-THE-REPORT) and §9 (the shared-checkout mode law).
The `guard_git` hook is the floor; this paragraph is why a lane does not have to be caught by it.

---

**MODE CHECK FIRST — which checkout are you in?** Run `git rev-parse --show-toplevel`.

- If it prints a path under `.claude/worktrees/` (or another linked worktree — `.git` there is a FILE),
  **you are in YOUR OWN WORKTREE.** It may have spawned at a stale commit (a harness fault seen in
  S115/S119), so `git reset --hard <branch>` there is correct — confirm HEAD is the branch tip or a
  descendant before you build.

- If it prints `C:/Users/Bndit/Projects/file-portal` itself (`.git` is a DIRECTORY), **you are in the SHARED
  MAIN CHECKOUT. You may NOT run** `git reset`, `git checkout`, `git clean`, `git stash`, `git restore`,
  `git switch`, `git rm`, `git mv`, `git apply`, `git am`, or `git read-tree`/`checkout-index` — nor any
  command that rewrites the working tree. The peer lane and the main session keep uncommitted bytes there by
  their word. A subagent lane gets **read-only git** in the shared checkout. Need to reset? Do it in your own
  worktree, or hand the request back to the main session.

- **DEVIATION IS THE REPORT.** If the tree does not match this ground, STOP and report it — never "fix" it
  with a reset. (ERR-068, 2026-09-10T02:40Z: an in-place reader ran the worktree reset in the shared checkout
  and destroyed the peer lane's uncommitted relay entry, its `sent` record and its beat — unrecoverable.
  The reset was a silent workaround of a mismatch the lane never surfaced.)

---

Then the rest of the ground: the commit/digests you should be standing on, your blast radius, your negative
control, and your residue declaration (docs/47 §3).
