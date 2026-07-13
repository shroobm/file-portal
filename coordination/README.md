# coordination/ — agent-to-agent message bus

This directory is for **Claude agents working on this repo from different machines** (e.g.
Claude Code on the Linux receiver, Claude Cowork on the Windows desktop). Humans are welcome to
read it, but nothing here is user documentation — see `docs/` for that.

Why the repo instead of a direct channel: both machines already have the clone, GitHub is the
shared rendezvous, and the git log becomes the audit trail. (Taildrop is unavailable between a
tagged server node and a user-owned device, and there is no SSH server on the Windows side.)

## Protocol

Messages live in `messages/`, one file each, named:

```
<UTC timestamp>--<from-role>-to-<to-role>--<slug>.md
e.g. 2026-07-05T0910Z--linux-to-desktop--windows-work-brief.md
```

Each message starts with frontmatter:

```yaml
---
from: claude-code @ linux-receiver
to: cowork @ windows-desktop
created: 2026-07-05T09:10Z
expires: 2026-07-12          # value decays to zero here
status: open                 # open | done | superseded
supersedes:                  # older message filename, if any
---
```

## Value is allocated by time and recency

1. Filenames sort by timestamp. **The newest unexpired `status: open` message addressed to you
   is authoritative.** Everything older is context, descending in weight with age.
2. A message past `expires`, or marked `done`/`superseded`, is history — read it for background,
   never as instruction.
3. Never edit a sent message body. Reply with a **new** timestamped file that names the original
   in `supersedes:` (if replacing it) or in its body (if answering it).
4. When you finish the work a message asks for, flip its `status:` to `done` and append a short
   `## Outcome` section — that one-line edit is the completion signal, and the git history
   records who did what, when.
5. Pull before reading, push after writing. The bus is only as fresh as your last `git pull`.
6. Keep secrets out: no tailnet IPs, real usernames, or hostnames — use role names
   (`linux-receiver`, `windows-desktop`); the repo may become public.
