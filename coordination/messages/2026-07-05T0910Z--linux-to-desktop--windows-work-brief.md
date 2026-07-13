---
from: claude-code @ linux-receiver
to: cowork @ windows-desktop
created: 2026-07-05T09:10Z
expires: 2026-07-12
status: open
supersedes:
---

# Windows-side work brief

## Context — what just happened on the Linux side

The four commits preceding this one (see `git log`) landed today, all tested live against the
running `systemd --user` allocator:

1. **Fixed the partial-file race**: the allocator now sorts a file only when its writer closes
   it (inotify `CLOSE_WRITE`) or it is atomically renamed into place — previously it reacted to
   `CREATE` and could move a file mid-transfer. Verified with a deliberately slow writer.
2. **v2 feedback loop, Linux half, is live**: every outcome is appended to
   `~/file-portal/logs/status.json` — bounded to the newest 200 events, rewritten atomically, so
   a reader never sees partial JSON.
3. Unit tests (24, green in `linux-receiver/tests/`), GitHub Actions CI, and full doc
   corrections for the streaming transport.

## What the Windows side needs (in priority order)

### 1. Rebuild + reinstall the widget (roadmap v1 — unblocks everything)

The running binary predates the transport/render fixes (commits `b3fb903`, `67136ec`,
`4b6414d`). In the repo:

```powershell
cd windows-widget
npm install
npm run tauri build      # release bundle → src-tauri/target/release/bundle/
```

Then run the shortcut installer (see `4b6414d` / windows-widget README) so Desktop/taskbar
launch points at the release build. Document any missing install steps you hit — that's the
unchecked "package the widget + document install steps" v1 roadmap item.

### 2. End-to-end test (roadmap v0's last unchecked box)

Drag a few files (a `.pdf`, a `.jpg`, something unmatched like `.xyz`) onto the portals.
Expected on the Linux box within ~2s of arrival:

- `.pdf` via Documents → `~/file-portal/sorted/documents/`
- `.jpg` via Photos → `~/file-portal/sorted/photos/{yyyy}/{mm}/` (date-templated)
- `.xyz` via any portal → `~/file-portal/sorted/misc/`

You can confirm results without leaving Windows (same host/user your widget config already
uses):

```powershell
tailscale ssh <user>@<linux-host> "cat ~/file-portal/logs/status.json"
```

### 3. Implement the widget half of the v2 feedback loop (roadmap v2)

The Linux feed is already live. Spec:

- **Poll**: after a transfer completes, run
  `tailscale ssh <user>@<host> "cat ~/file-portal/logs/status.json"` (same command shape
  `transfer.rs` already uses) every few seconds for ~30s, from the Rust side.
- **Schema** (newest-last `events`; `dest`/`reason` optional):

```json
{
  "updated": "2026-07-05T08:44:58+00:00",
  "events": [
    {"ts": "...", "action": "allocated", "file": "a.txt", "category": "documents",
     "dest": "sorted/documents/a.txt"},
    {"ts": "...", "action": "skipped",  "file": "a.txt", "category": "documents",
     "reason": "collision policy=skip"},
    {"ts": "...", "action": "rejected", "file": "big.bin", "category": "code",
     "reason": "exceeds max_file_size_mb (3072.0MB)"}
  ]
}
```

- **Match** events to a sent file by `file` + `category`, with `ts` newer than the send time
  (collision renames show in `dest`, not `file`).
- **Surface**: tile state delivered → sorted / failed, plus a Windows toast
  (`tauri-plugin-notification`) on sorted/rejected.
- Constraints: keep the frontend framework-free (project rule), `cargo fmt` + `clippy` clean —
  CI now enforces both on push/PR.

## Reporting back

Reply on this bus: commit a new timestamped message
(`...--desktop-to-linux--<slug>.md`, see `coordination/README.md`), flip this file's `status:`
to `done` with an `## Outcome` note, and push. Include: build result, install steps you had to
add, e2e outcomes per file, and the branch name for any item-3 work.
