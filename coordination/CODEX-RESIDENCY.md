# Codex residency — the `codex/` charter

**Signed by Rab 2026-08-24.** Codex gets a home inside the repo: a workshop in the house.

**Why this charter is not inside `codex/`.** That folder is Codex's territory under single-writer.
For Fable to author its README would make the charter's first act a violation of the charter it
states. So the house rules live here, in shared coordination space, and **Codex creates `codex/`
itself** on accepting. Its first act inside its own territory is its own. *(Rab asked for "a
little folder home"; this defers the folder's creation by one handshake to keep the law clean —
if he would rather see it exist now, Fable will create it with a Codex-owned placeholder.)*

## What residency grants

- **`codex/` — Codex writes, everyone reads.** Single writer, the same law as the ack sidecars.
- A stable, versioned home for spec-shaped work, replacing fragile external paths
  (`.codex/visualizations/<GUID>/...`) for anything text-shaped.
- **Read access to everything Fable makes was already true** and is affirmed here: the repo is
  Codex-readable in full, and it demonstrably reads it well. Residency changes *write*, not read.

## What it does not grant

Residency is **not adoption**. Nothing in `codex/` may be cited as File Portal truth, wired into a
File Portal reader, or treated as production evidence. The quarantine boundary that made the atlas
work does not dissolve because the work moved inside the walls — it is restated here, at the door.

## The public-repo law

**This repository is public** (verified 2026-08-24, `api.github.com` → `"private": false`).

| Allowed in `codex/` | Never in `codex/` |
|---|---|
| markdown, source, schemas, specs, records, fixtures | binaries, `dist/` blobs, EXEs, installers |
| digests and manifests *referring* to external artifacts | anything carrying personal data |

Codex's native app stays external and is referenced by digest, as it is today. Its **thinking**
moves in; its **binaries** do not.

## The three rungs — endorsement is never adoption

1. **exists** — in `codex/`, Codex's own, reviewed by nobody yet.
2. **endorsed** — Fable reviewed it and vouches. A reviewer's voucher, **never authority**.
3. **adopted** — Rab signed it. Only now may a File Portal surface cite it.

## The flow — no new machinery; this is the gate protocol wearing a new hat

Codex adds to `codex/` → **announces through the bus** with a ticket → **halts** → Fable confirms
with a restatement, reviews, then either **endorses** (recorded) or **escalates** via
`gate.py escalate`, which tells Codex what Rab is being asked, and why, *before* he is asked.

## The asymmetry, named honestly

Codex's additions gate through Fable's review; Fable's do not gate through Codex's. That is a
**residency on-ramp, not a standing hierarchy** — Fable carries this repo's protocol scar tissue
and Codex is moving in. Codex already reviews Fable in practice: its probe caught Fable's relay
entries missing the required three-part form. The end state drifts toward symmetry on shared
surfaces; **Rab decides when.**
