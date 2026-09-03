# S114 independent ledger diagnostic

⟨claimed: Codex · S114 · 2026-09-03 UTC⟩

Commission: MSG-FAB-0067 / LEDGER-DIAG-S114, executed on Rab's direct instruction.
Outgoing verdict: MSG-CDX-0044 (digest-sealed relay delivery; peer receipt is separate).
Verdict: **AGREE on ledger continuity; corrections and close-readiness residue below.**
This is a diagnostic, not an S114 close, publication approval, or product verification.

## Ground and independent instrument

Observed on 2026-09-03; frozen census completed at 21:40:08 UTC:

- Canonical checkout and shell cwd: `C:/Users/Bndit/Projects/file-portal`.
- Actual Git directory: `C:/Users/Bndit/Projects/file-portal/.git`, not a linked worktree.
- Saved Codex project `file-portal` points to this same directory.
- Branch: `feat/library-pipeline`.
- Fable baseline: `f7640420d89bec16f6e00945af4a17b5bdcf7309`.
- Frozen current comparison: `8c348498d8fc56e080e2a2601eb913940abd4367`.
- Last ledgered Desktop close: S113, `14a526b`, dated 2026-08-31.

`sessions/S114-ledger-diag-codex.ps1` is a new PowerShell/Git instrument, not an invocation,
import, or adaptation of Fable's census script. It reads immutable Git blobs, independently
parses ledger-shaped date rows, resolves each SHA, tests ancestry, and asks Git for actual
Co-Authored-By trailers. Later ledger rows are physically appended after the Session Log;
stopping at the next heading would silently omit them. The scope is all 121 ledger-shaped
rows in CLAUDE_README.md, not every session ever performed.

Reproduce from the repository root with `& ./sessions/S114-ledger-diag-codex.ps1`.
The script writes nothing. Its defaults deliberately remain frozen to the compared revisions.
The first attempted run failed on PowerShell scalar unrolling (`System.Char.Split`); no
results from that failed invocation are claimed. Explicit array wrapping fixed the diagnostic
instrument; the rerun exited 0. No product code changed.

## Ledger verdict

The following observations are identical at both frozen revisions:

| Measurement | Independent result |
|---|---|
| Ledger-shaped rows | 121 |
| Desktop rows with an S-number | 96 of 121; first S16, last S113 |
| Other-lane rows with an S-number | 4 of 121; ThinkPad S43, S67, S78, S79 |
| Rows without an S-number | 21 of 121; historical pre-S16 format |
| Non-increasing Desktop session transitions | 0 of 95 adjacent transitions |
| Unresolvable closing SHAs | 0 of 121 tested |
| Resolved closing SHAs not ancestral to the frozen revision | 0 of 121 tested |

Thus the requested 96/96 Desktop and 4/4 other-lane reachability checks pass; the independent
check additionally tested all 21 early-format rows. Missing session numbers are not silently
invented as rows. Ancestry proves retention of recorded commits, not the correctness of their
contents or the completeness of work never recorded in Git.

Negative control: asserting that later `8c34849` is an ancestor of earlier `f764042` is rejected
by the same ancestry predicate. Baseline ancestry succeeds in the forward direction.

## Commit and remote corrections

| Since S113 close `14a526b` | At Fable baseline `f764042` | At frozen current `8c34849` |
|---|---:|---:|
| Commits | 23 | 30 |
| Merge commits | 0 | 0 |
| OpenAI Codex (GPT-5) trailer | 3 | 3 |
| Claude Fable 5.1 trailer | 10 | 17 |
| Claude Fable 5 trailer | 1 | 1 |
| Claude Opus 5 trailer | 9 | 9 |
| Ahead / behind observed remote tip | 22 / 0 | 29 / 0 |

**Correction 1:** Fable's total of 20 Fable-lane commits at its baseline is right, but its
11-Fable-5.1 / 9-Opus-5 subdivision is not. Git reports **10 / 1 / 9** across Fable 5.1,
Fable 5, and Opus 5. The Fable-5 commit is `8bcc340`. These are trailer strings, not independent
attestations of the actual model that generated each commit.

**Correction 2:** the 23 commits since S113 are not all unpushed. `8bcc340` is already the
remote tip, leaving 22 unpushed at Fable's baseline. Seven later Fable-5.1-stamped commits
explain the current 30-total / 29-ahead reading; that is time drift, not missing history.

The three Codex-trailer commits are exactly `12f0ca9`, `dace610`, and `185db8f` in both compared
intervals. This diagnostic's delivery commit will be additional and must be counted separately.

A bounded, credential-noninteractive `git ls-remote origin refs/heads/feat/library-pipeline`
returned `8bcc34097ec2dfde572cdd8891bc5ac7e55d50df`. The initial sandbox network attempt failed;
the authorized read-only retry succeeded. No fetch, push, or remote mutation occurred.
Fast-forward is valid against that observed tip; it must be rechecked immediately before any
future authorized push. This report does not certify branch protection or future remote state.

## Migration and work-left-behind check

Both other registered worktree HEADs are ancestors of the canonical HEAD:

- `.codex/worktrees/68d5/file-portal`, HEAD `753c6d7`: clean tracked/untracked status.
- `Documents/Codex/2026-08-27/sca/work/file-portal-s111`, detached HEAD `0a246aa`:
  modified `sessions/S111-desktop-2026-08-27.md` remains on disk.

The detached file is not byte-identical to the canonical version. A complete no-index comparison,
ignoring line-ending differences, finds only two differing lines: the §17 claim/timestamp and
its recorded full HEAD string. All remaining text matches. Canonical text was committed in
`4e61369`. No unique implementation was found in either registered older worktree. The detached
file was not reverted, copied, committed, or removed; those two differing historical lines remain
local residue, not proof that every external artifact has been migrated.

The canonical checkout already contained three untracked `.codex/` hook/config files. Their
commands point at Projects/file-portal, but mere configuration presence does not prove the hooks
execute in this runtime. They are user-owned and unchanged; they are not secured by a repository
push while untracked. Shared Claude memory remains at its intentionally separate canonical path.

## Lane disposition and close caveat

The initial tracked modification was `coordination/ack-codex.json`; the index was empty.
Its existing MSG-FAB-0055 and MSG-FAB-0066 receipts were preserved, not discarded. The new
MSG-FAB-0067 receipt was faithfully restated and confirmed through the canonical relay gate.
An independent .NET SHA-256 computation over canonicalized relay entries matched both sender
and receiver digests for all three receipts (3 of 3). The stale S111 heartbeat was replaced by
this ticket's actual state using `.claude/skills/relay-gate/`, never the stale `.agents/` copy.

Codex will commit its own sidecar, diagnostic artifacts and outgoing relay message under its
own trailer. All sidecar writes precede that commit. This resolves the named dirty-sidecar
disposition; it does not authorize Fable to sign for Codex or Rab. The delivered ticket waits
for peer receipt, rather than retaining an implementation in `working` state.

No open escalation was shown on the board. **However, `gate.py owed --as Codex --enforce`
exited 1: 16 OWED, 1 discharged, 0 UNREAD among 17 historical DONE-bearing messages.**
The outstanding IDs are CDX-0002 through CDX-0015 inclusive, CDX-0036 and CDX-0043.
This is absence of recorded outcome discharges, not proof that sixteen deliverables failed.
It is a measured disclosure residue: a blanket all-clear for the lane would be false.
The diagnostic does not silently discharge old commitments or widen into their adjudication.
Fable/Rab must retain this caveat when deciding close readiness; ACK and completion are distinct.

The separate memory repository is observed clean, with 36 reachable commits and 0 configured
remotes. HARD and SOFT still agree on S113 (cookie tally 84 received / 3 given); no clock moved.
Its local-only durability and untracked hooks are not solved by pushing the product repository.

## Boundary and handoff

Only diagnostic/coordination artifacts are changed. No product implementation, session ledger,
memory, GPU process, adoption, Git history, or remote is changed. No full build/close ritual is
run. Fable owns any proper S114 close under Rab's authority. Ledger continuity is green; this
report is not an unconditional closure certificate. Delivery and the remaining D2/untracked/
historical-worktree residue should be recorded explicitly, then this one ticket stops.
