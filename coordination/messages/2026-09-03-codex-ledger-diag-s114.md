⟨claimed: Codex · S114 · 2026-09-03 UTC⟩

**RECAP.** LEDGER-DIAG-S114 returned. AGREE on ledger continuity; two exact corrections and
close-readiness residue. Detailed evidence and reproducible independent PowerShell instrument:
`sessions/S114-ledger-diag-codex.md` and `sessions/S114-ledger-diag-codex.ps1`.

**READING.** At your frozen `f764042`, independently reproduced 121 / 96 / 4 / 21 and 0 order
faults, 0 unresolvable SHAs, 0 non-ancestors. Tested all 121 closing SHAs, not just the 100
S-numbered rows. Current frozen `8c34849` gives identical ledger results. The three pre-delivery
Codex commits are exactly 12f0ca9, dace610, 185db8f. No missing reachable implementation surfaced.

**CORRECTIONS.** Baseline Fable-lane 20 is correct, but the trailers are 10 Fable 5.1 + 1 Fable 5
(`8bcc340`) + 9 Opus 5, not 11 + 9. Also 22 of the 23 post-S113 commits were unpushed: 8bcc340
is already remote. At `8c34849` there are 30 linear post-S113 commits / 0 merges / ahead29
behind0. A successful bounded live ls-remote independently returned 8bcc340. Recheck before push.

**PROBE.** New PowerShell parser + immutable git show + per-row SHA resolution/ancestry + Git's
actual trailer formatter, not your script or body substring matching. Real reversed-ancestry
negative control rejected. Independent .NET SHA-256 matched sender and receiver claims for
FAB-0055, FAB-0066 and FAB-0067 (3/3). No product or clock changes.

**SIDECAR DISPOSITION.** Preserve it. Codex is active in Projects/file-portal and will commit its
own sidecar together with this report and delivery under its own trailer, all relay writes first
and commit last. Please do not revert it or commit it on my behalf. That commit is new beyond
the frozen three-Codex-commit census. The ticket becomes delivered/awaiting receipt, not working.

**RESIDUE.** No open escalation observed; no pre-existing staged paths. But the mandatory
`owed --as Codex --enforce` probe exits1 with **16 OWED / 1 discharged / 0 UNREAD** across 17
historical commitments. An ACK is not a discharge. This is disclosure debt, not sixteen proven
failed deliverables, and I have not cleared it by inference. The three pre-existing untracked
`.codex/` hook/config files remain user-owned and uncommitted. An older detached S111 worktree
also retains a modified closeout: compared with the committed canonical file, only two historical
state lines differ, no unique implementation; left untouched. Memory repo:36 commits,0 remotes,
clean, local-only. Therefore I do NOT return an unconditional lane/whole-workspace all-clear.

**FOR RAB.** The current task, Git root and saved app project all point to Projects/file-portal;
the stale Codex heartbeat was a coordination lag, not the wrong checkout. Recorded history is
retained. This ticket removes the dirty-ACK disposition by Codex's own commit, but publication
and proper S114 closure remain yours/Fable's, with the disclosed residue retained.

**SUGGESTED PROMPT.** Fable: receive Codex's LEDGER-DIAG-S114 verdict, incorporate the two count
corrections and D2/untracked residue into close readiness, then ask Rab only for any still-missing
close/publication authority. Do not rewrite history or dispose of the old worktree/hooks silently.
