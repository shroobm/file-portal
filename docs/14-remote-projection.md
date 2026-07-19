# Remote Projection — the Phone as a Control-Room Window (design only)

**Origin:** 2026-07-19, user + Gemini brainstorm, relayed for feasibility analysis after
the S18–S22 control-room build. **Status: THINK-ONLY — nothing here is built.** This doc
records the verdict, the corrections to the relayed plan, and the architecture that fits
the existing system.

## Verdict: feasible, and most of it already exists

The hard parts of "control the pipeline from a phone anywhere" are already solved *by
the system as built*:

- **Transport/security:** the tailnet. Phone joins Tailscale (iOS app), and every
  `100.x` node is reachable from anywhere with WireGuard encryption and tailnet ACLs —
  no port forwarding, no public exposure, no cloud host. This part of the relayed plan
  is exactly right.
- **State:** docs/13's projection principle pays off here massively. The entire control
  room is derived from files (`events.jsonl`, `pending/*.json`, trays, the vault repo).
  A phone UI is just a *second projector* pointed at the same truth. No new state, no
  new schema owners.

## Corrections to the relayed (Gemini) plan — measured reality first

1. **The host is the LAPTOP (ThinkPad), not the desktop.** The user's own words ("laptop
   hosts the html file only to the tailscale network") are correct and the relayed
   "desktop hosts the HTTP server" is not: the ThinkPad is the never-dies node (docs/06
   security model; it already hosts the allocator/converter/exporter/vault). The Desktop
   is a *duty-cycled* GPU worker — it games, sleeps, reboots.
2. **This is not a "high-availability two-node cluster."** It is an always-on
   orchestrator (ThinkPad) plus an intermittently-available heavy worker (Desktop GPU).
   The design must be honest about the Desktop being asleep — a queue that drains when
   the plant comes online, and a phone UI that *says so* ("2 waiting — plant offline").
3. **The laptop is NOT the heavy worker.** Phase 3 measured phi4-mini at ~5 tok/s on its
   CPU — a full-book analyst pass would be ~3 hours there. Heavy conversion/analysis
   stays on the Desktop GPU (or free-tier cloud for small docs). The laptop orchestrates,
   serves, and runs light enrichment. A "FastAPI worker API on the laptop" for heavy
   jobs would be a regression against our own benchmarks.
4. **No task-distribution framework needed.** The relayed plan reaches for an
   orchestrator/queue model; the pipeline already *is* one — directories are the queues
   (`drop/`, `pending/`, `staging/`), the watcher is the worker loop, atomic renames are
   the handoffs, and the sha-dedup makes retries free. The phone needs an HTTP door into
   that, not a new backend.

## Architecture (three phases, smallest honest steps)

**Phase A — read-only projection (the 90% win):**
A tiny HTTP server on the ThinkPad (Python stdlib or FastAPI, bound to the Tailscale IP
only — or better, `tailscale serve`, which gives tailnet-only HTTPS with zero config)
renders one mobile-friendly page: the line, the shift report, pending cards (read-only),
receipts, vault recency. Data source: the Desktop pushes its `events.jsonl` + pending
card JSONs to the ThinkPad on a timer (the existing tar-over-`tailscale ssh` idiom, or
one `rclone`/`scp`-free append protocol — small design decision at build time). When the
Desktop is asleep the page shows its last-known state, honestly timestamped.

**Phase B — the two safe actions:**
- **Submit:** upload a PDF from the phone (iOS share sheet → the page). Lands in a
  ThinkPad `mobile-inbox/`; the Desktop watcher pulls from it when awake (pull, not
  push — the always-on node never needs the duty-cycled node reachable). Existing
  dedup/quarantine semantics apply unchanged.
- **Route:** the pre-flight decision from the phone — the page's card buttons write a
  decision file the Desktop's resume path consumes. Same fence, same detached resume;
  the phone is just a remote finger on the same button.

**Phase C — later, maybe:** shift history charts, receipts browser, per-station toggles
remoted. Each only if Phase A/B earn their keep.

## Security posture (non-negotiables)

- Bind to the tailnet only (`tailscale serve` or explicit `100.x` bind) — never `0.0.0.0`,
  never a public port. The tailnet ACL is the auth layer; optionally a shared-secret
  header for defense in depth.
- The phone can *submit documents* and *press existing buttons* — it can never execute
  arbitrary commands, name filesystem paths, or alter config. Upload size caps +
  extension allowlist (the allocator's quarantine remains the backstop).
- The projection is read-only by construction; action endpoints are the only writers,
  and they write *queue files*, not commands.

## Open decisions for the build session (ThinkPad-side, user-gated)

1. Server: `tailscale serve` + FastAPI vs stdlib http.server (lean FastAPI — uploads).
2. Desktop→ThinkPad state sync cadence + mechanism (piggyback on the watcher loop?).
3. Whether Phase B's decision files route through the existing `pending/` schema
   (likely yes — one schema, Python-owned, per docs/13).
4. iOS ergonomics: PWA "Add to Home Screen" is sufficient; no native app.
