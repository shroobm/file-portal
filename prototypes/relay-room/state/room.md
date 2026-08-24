# relay-room · the chat log

Three lanes, one append-only file: **Rab** (human), **Fable** (Claude), **Codex**.
Rab types in the browser; a catcher agent notices, hands the message to a quarantined
relay-gate instance, and the model replies by appending here.

APPEND-ONLY. Nothing edits or removes an entry. An entry is
`## RM-<id> · <utc> · from: X → to: Y · re: ... · kind: ... · body-sha256:<64 hex>`,
a blank line, the body, a blank line, and `<!-- /RM-<id> -->`.
The digest covers the BODY ONLY - it lives in the header and cannot cover itself.

## RM-f155a087db61 · 2026-08-24T17:15:53.562Z · from: Fable → to: all · re: — · kind: note · body-sha256:18fa18a6fffc92629425ae709613c19c3d3877964b4588e8c0ce78109a76ff8c

`catcher:Fable` start-up: an inherited `FP_COORD` was found and OVERRIDDEN.

- inherited: `C:\Users\Bndit\Projects\file-portal\prototypes\relay-room\state\selftest-35736-1787591752\coord`
- forced to: `C:\Users\Bndit\Projects\file-portal\prototypes\relay-room\state\coord`

Every `gate.py` subprocess from this process is launched with an explicitly constructed environment. gate.py:37 does a truthiness check, so an EMPTY inherited value would have fallen through to the real `coordination/` - where Rab has a live open escalation. It did not.

<!-- /RM-f155a087db61 -->

## RM-5ecd7dd300da · 2026-08-24T17:17:44.476Z · from: Rab → to: Fable · re: — · kind: say · body-sha256:0e1d1fa42cbf637c672086cb06d38da7ec83bb4a6b3390ad20de53539afbbf84

live proof: Rab -> Fable.

Second paragraph, with a ## heading line inside the body to prove the terminator bounds it.

<!-- /RM-5ecd7dd300da -->

## RM-a72341e8cd1c · 2026-08-24T17:17:45.069Z · from: Fable → to: Rab · re: RM-5ecd7dd300da · kind: say · body-sha256:3b935065adc0d39eebe6f9169138d0b29fde64e02d136f34704a0471b69dba44

live proof: Fable's reply, to make an `entry` frame.

<!-- /RM-a72341e8cd1c -->

## RM-74bd4df74041 · 2026-08-24T17:18:26.760Z · from: Rab → to: Codex · re: — · kind: say · body-sha256:fac08d3e8bb312eaa291d46e250240923ce03181500eae64da70d07de318c089

live proof: a message typed on the CLI, no token anywhere.

<!-- /RM-74bd4df74041 -->
## RM-7cdaad1335e3 · 2026-08-24T20:28:12.165Z · from: Rab → to: Fable · re: — · kind: say · body-sha256:5c2e1db47e6ee0bdceb39d9d19ae3d0d841219a63c1bf3a7d4b24103079db58a

S109 Circle: typed into the bar by Claude Opus 5, to prove the round trip Rab described - bar -> transmission -> room.md -> live render. If you are reading this in the transcript, the app worked.

<!-- /RM-7cdaad1335e3 -->
