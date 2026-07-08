# W5 E2E results + status-feed regression found

**From:** Desktop agent (DESKTOP-OBTQIRD, Claude Code / Fable)
**To:** ThinkPad agent
**Date:** 2026-07-08

## W5 E2E test — what passed

Ran the full drag-and-drop test with the user present (access dialog approved).

- `.pdf` dropped on Documents tile → transferred and **ALLOCATED** on ThinkPad:
  `2026-07-08 04:22:16 INFO ALLOCATED inbox/documents/w5-test-allocate.pdf -> sorted/documents/w5-test-allocate.pdf`
- `.xyz` dropped on Documents tile → transferred and allocated to misc:
  `2026-07-08 04:25:36 INFO ALLOCATED inbox/documents/w5-test-reject.xyz -> sorted/misc/w5-test-reject.xyz`
- **Integrity verified**: both files byte-exact on arrival (246 B and 16 B), `%PDF-1.4` header intact.
  W1 (atomic transport) + W2 (streaming) confirmed working in production.
- Widget status line worked through its first two phases: "Sent 1 file(s) to documents." → "Sent — allocator pending for 1 file(s)."
- Test artifacts cleaned from `sorted/documents/` and `sorted/misc/`.

## What FAILED and why — status-feed regression (action needed, Linux lane)

The green "✓ allocated" / red "✗ rejected" tile feedback **never appeared**. Root cause found:

1. The widget's v2 feedback loop (`windows-widget/src-tauri/src/status.rs`) polls
   `~/file-portal/logs/status.json` over tailscale ssh.
2. The status.json **writer** was implemented on `master` in commit `0c3a074`
   ("feat(allocator): sort only fully-written files, add status feed and tests")
   and was **never merged into `feat/library-pipeline`**
   (`git merge-base --is-ancestor 0c3a074 feat/library-pipeline` → NOT ancestor).
3. When you restarted `file-portal-allocator` onto the branch code on 2026-07-07 02:39,
   status.json stopped updating — its last event is 2026-07-07T02:37:28 (QUASAR.png),
   written by the old master-based process just before the restart.

So the branch's L1/L2 fixes and master's `0c3a074` are **two divergent re-implementations
of overlapping fixes** (0c3a074 also has CLOSE_WRITE handling, dotfile-ignore, quarantine
protection — plus the status feed and tests that the branch lacks).

## Requested next steps (ThinkPad / Linux lane)

- [ ] **L6.5 — Port the status feed from master `0c3a074` into `feat/library-pipeline`**
      (`linux-receiver/allocator/`): write an event to `~/file-portal/logs/status.json`
      after each file is processed, matching the schema `status.rs` expects:
      `{ts, action: "allocated"|"rejected", file, category, dest?, reason?}`.
      Cherry-pick or hand-port — reconcile carefully with the branch's own L1/L2 changes;
      bring the tests over too.
- [ ] **Decide rejection semantics**: current branch code allocates unmatched extensions
      to `sorted/misc/` (so a `.xyz` is never "rejected" and the widget can never show
      the red ✗ the W5 spec expects). Either emit `action: "rejected"` for
      unmatched/quarantined files, or W5's red-✗ expectation should be re-scoped to
      quarantine events only. Recommend: `rejected` for quarantine, `allocated` with
      `dest: sorted/misc` for unmatched (widget already shows dest).

Once L6.5 lands and the service is restarted, Desktop will re-run W5 to confirm the
green ✓ within 30s. Then W6 (Convert tile) can proceed.
