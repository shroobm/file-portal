# 19 — Execution Plan for Opus 5: Everything That Remains

*Written S57 (2026-07-31) by the Fable 5 desktop session at Rab's request: "a thorough
dummy-proof plan for Opus 5" covering the rest of the gates. Per the prompt-crafting protocol,
this is a truthful record of circumstance: **you** are a Claude (likely Opus 5) session working
on Rab's Desktop (`bndit`@`DESKTOP-BNDIT`) or over SSH; **Rab** is the human whose hands do
everything this document marks RAB-ONLY. Nothing here assumes you remember anything. When this
doc and reality disagree, reality wins — measure, then update this doc.*

---

## 0. Before ANY work — the laws (each one paid for in blood; origins in parentheses)

1. **MUSTER first.** Verify memory loaded + the two clocks agree (git ledger row ↔
   `MEMORY.md` TIME-STATE ↔ cookie tally). Protocol: `session-bootstrap.md` in the memory
   library; keyword MUSTER. Open every session with a plan commit; close in lockstep; the
   ledger row is a SEPARATE follow-up commit — **never amend** (S-early lesson).
2. **The projection law.** The widget READS; Python owns pipeline truth (single-writer files:
   `events.jsonl`, `analyst-mode.txt`, `audit-mode.txt`, progress files, markers). New UI =
   read-only projection + levers that write only the backend's own config/marker files.
3. **The MSIX ghost laws (S29, S45, S48 — three separate disasters).** A packaged desktop-app
   Claude session's writes to AppData/registry can be silently virtualized: (a) NEVER install
   tools or adopt widget builds from a packaged session — **adoption is Rab's hand**: build →
   print SHA-8 → Rab closes the widget, `Copy-Item` + `Get-FileHash` in HIS shell, expects
   your SHA → double-click launch; (b) never verify a write from the surface that made it;
   (c) system configuration only from elevated UNPACKAGED shells (Rab) or over SSH.
4. **Verify-before-instruct (standing rule, memory `file-portal-verify-before-instruct`).**
   Any "click X / do Y" instruction about File Portal is checked against CURRENT source first.
   The ⚡ tile is a DRAG TARGET, not a switch; the watcher's control is the titlebar ⏻.
5. **Key material travels by file (scp), never clipboard** (S47: a hand-pasted pubkey silently
   truncated 73/106 bytes).
6. **Programmatic ssh/scp on this box**: ALWAYS `-o BatchMode=yes -o
   StrictHostKeyChecking=accept-new -o ConnectTimeout=10`. System32 OpenSSH keeps its OWN
   known_hosts (git ships a separate ssh) — without BatchMode, windowless processes hang
   forever at an invisible host-key prompt (S56: nine zombie scp pairs).
7. **Kill process TREES**: `proc.kill()`/single-pid kills leave the venv/console-script
   launcher's real python alive holding the GPU. `taskkill /pid N /t /f`, or in code the
   `_kill_tree` helper (S48/S52).
8. **Coexistence**: never convert or stream while Rab's little brother games (`query user`
   first — if `comed` is at the console, the seat is his). Streaming is GPU work. Sunshine
   mirrors the ACTIVE console session.
9. **Long remote jobs are queued (`scp → drop/`), never shell-tied.** An SSH disconnect kills
   shell children; the watcher owns queued work.
10. **Cookies**: Rab awards 🍪 for good work. Update `cookie-tally.md` (header AND a ledger
    entry — the S57 backfill happened because entries got skipped) + the TIME-STATE mirror,
    every time, before other work.
11. **Reports**: session/overnight summaries → `C:\Users\Bndit\Desktop\CLAUDES DESKTOP MESSAGES
    FOR BNDIT\YYYY-MM-DD -- title.txt`. Pipeline runs → Gmail draft to self. Both on sign-off.
12. **The sandboxed session cannot**: read firewall rules (`Get-NetFirewallRule` = denied),
    read `ProgramData\ssh` contents, kill Rab's processes, raw-ssh to the ThinkPad
    (`journalctl --user` additionally needs a login session — it will hang; have Rab run it).

## 1. The machine map (measured, 2026-07-31)

- **Repo**: `C:\Users\Bndit\Projects\file-portal`, branch `feat/library-pipeline`, remote
  GitHub `shroobm/file-portal`. Repo brain: `CLAUDE_README.md` (session protocol + Change
  Ledger). Design docs: `docs/15` (audit), `docs/16` (control room), `docs/17` (remote
  access), `docs/18` (levers & heartbeats — THE build plan this doc executes).
- **Pipeline root**: `C:\Users\Bndit\ml\library` — `drop/` (+`done/`, `failed/`,
  `.supersede/`), `anchor/`, `pending/`, `held/`, `events.jsonl`, `watcher.log`,
  `widget-boot.log`, `watcher-stderr.log`, `.gpu-lock`, `.convert-progress.json`,
  `.analyst-progress.json`, `analyst-mode.txt`, `audit-mode.txt`.
- **Python**: marker-env at `C:\Users\Bndit\ml\marker-env` (base CPython = uv-managed under
  `%APPDATA%\uv\python\…` — REAL since S48; if a venv launcher dies exit 0x67, the base is
  missing again). Converter code runs FROM THE REPO (`windows-converter/`), read fresh per
  convert — python-side changes need no widget rebuild.
- **Widget**: source `windows-widget/`; installed exe `C:\Users\Bndit\AppData\Local\File
  Portal\file-portal-widget.exe` (currently `7D403BD6`). Rebuild ritual: `cargo clippy
  --all-targets -- -D warnings` → `node --check` on touched JS → `cargo test` → `npm run
  build` (in `windows-widget/`) → hash `target\release\file-portal-widget.exe` → RAB adopts
  (law 3). Tauri's bundler patches the exe post-build — hashes differ between raw and bundled
  stages; hash what you stage.
- **ThinkPad** (`rab@archlinux`, tailnet 100.107.238.61): code checkout
  `~/file-portal-src` (service: `file-portal-converter`, systemd --user, WorkingDirectory
  `~/file-portal-src/linux-converter`); runtime `~/file-portal/` (`library/staging/`,
  `vault.git`, `vault-work`). Deploy = `cd ~/file-portal-src && git pull && systemctl --user
  restart file-portal-converter` (RAB runs it; the restart's startup sweep re-processes
  staging). Journal = `journalctl --user -u file-portal-converter` (RAB runs it).
- **Vault**: bare `~/file-portal/vault.git` on the ThinkPad; desktop clone
  `C:\Users\Bndit\Documents\Obsidian\Obsidian and Zennotes Vault\Library`. **6 notes** as of
  S56 (the 6th = Cybernetics, the first blessed book).
- **Remote access** (docs/17): sshd key-only on the desktop (tailnet-scoped), Sunshine
  installed + scoped, ThinkPad `moonlight-qt` paired. `claude` CLI 2.1.220 on PATH for
  `bndit` — an SSH session can run a MUSTER-clean Claude.

## 2. Current truth (so you don't re-fight settled battles)

- Stages A + B + C(first half) of docs/18 are SHIPPED and live-proven. Read docs/18 §8's
  table before planning anything.
- `held/` contains TWO bundles: Valentine `b6fbdd75f6242f53` (degeneration-fail — the Repair
  Bench's designated first customer; CANNOT be blessed, by design) and Cybernetics
  `c5afd9edcf620fc6` (the STALE degenerate copy; the good version is vaulted — ask Rab:
  cleanup or archaeology?).
- The audit lever is `report`; standing-enforce is an OPEN policy question for Rab.
- The bless flow: ✓ bless button → `assay.rs::bless` validates against the EVENT STREAM →
  scp's sha-bound `bless.json` into ThinkPad staging → exporter accepts `flag`+bless on its
  next sweep (a service restart). Per-bundle bless targeting is NOT built (the card-subject
  race — see Stage C2).

## 3. Stage C2 — analyst-only re-run + seam events + per-bundle targeting

> **SHIPPED S58 (2026-07-31)** — all three built, gated, and proved by harness; see CHANGELOG.
> The design decision below was signed by Rab at the top of that session: **receipts travel as
> a plain `~/file-portal/receipts.jsonl` on the ThinkPad, tailed by the widget over `tailscale
> ssh` on the vault bar's 45 s poll.** Neither offered option won — Rab took a third: keeping
> the records out of the vault entirely means the exporter's change is an append to a plain
> file, so the module that writes the vault gained no new git code. Rejected: receipts
> committed into the vault repo (machine records + a conflict surface inside the notes' own
> history) and a side `receipts` branch (git plumbing in the most dangerous module).
>
> **Still owed when this was written** (both need hands this session did not have):
> 1. **RAB — deploy the ThinkPad** (`cd ~/file-portal-src && git pull && systemctl --user
>    restart file-portal-converter`). Until then the remote receipts file does not exist; the
>    widget's fetch handles that as a normal empty answer (verified by probe), so nothing
>    breaks — the event stream simply shows no `export` rows yet.
> 2. **RAB — adopt the widget build**, then the live claude-code re-run (~17 min GPU, so check
>    `query user` first). Its `pass` should produce the first `exported-supersede` receipt and
>    replace vault note 5 in place.
>
> Left undone deliberately: the **drill-down** entries still carry no per-bundle buttons (the
> held ROWS on both surfaces do, which is what the card-flip race actually needed); adding them
> to the drill tree is cosmetic follow-up, not a gap in the remedy's reach.

**Precondition**: none. All desktop-side except the seam-events exporter half.
1. **Analyst-only re-run**: a `⟲ re-analyze` button beside ⟳ on audit cards. New marker
   `drop/.reanalyze/<source>.json` (mirror the supersede pattern: widget-authored, sha-bound,
   consume-once). `convert_and_ship` gains a resume mode that SKIPS Marker: load the bundle's
   existing markdown from `anchor/<bundle>/`, run the analyst + analyst-phase audit + ship.
   The claude-code book (vault note 5, analyst-phase `fail` from qwen3 looping in its own
   notes) is the first customer — its re-run ships a supersede (verdict must reach `pass`, or
   bless it if it stays `flag`).
2. **Per-bundle targeting**: bless and re-analyze buttons on EACH held row and drill-down
   entry (not just the card subject) — kills the mtime-touch ritual and the card-flip race.
   `data-src` per row; the backends already take explicit sources.
3. **Seam events**: exporter outcomes (`EXPORT-*` lines) must become desktop-visible facts.
   Design decision for Rab (STOP and ask): (a) exporter appends outcome records to a
   `receipts.jsonl` inside the VAULT repo (rides the existing clone pulls — zero new
   transport, but writes machine records into the vault), or (b) desktop polls a receipts
   file over scheduled scp (new transport, vault stays pure). Present both; build the signed
   one. Done-when: an `EXPORT-BLESSED`/`-HELD`/`-SKIP` shows in the widget's event stream
   without anyone reading a ThinkPad journal.
4. Gates + adoption per law 3; ThinkPad deploy per §1 if the exporter changed.

## 4. Stage D — chunking (THE SIGNED SPEC IS docs/18 §5.2 — follow it verbatim)

Parameters are DECIDED (S57): clean >600 pp / scan >400 pp; 200-page slices; clean cuts with
seams recorded in the manifest; slice batch = user lever `chunk-batch.txt` (8|16|32, default
16); resume by (source_sha, page_range); slice-prefixed progress; assets renumbered by
absolute page; audit on the merged book; **the conversion ledger** (record pages/lane/
chars-pp/s-pp/wall/chunked/slices/batch/peak-VRAM per successful conversion; estimator
upgrades from global median to similarity-based; every estimate later paired with its
actual). Build converter-side first (testable without the widget: drive `convert()` on a
synthetic long PDF — concatenate a small PDF with pymupdf to >600 pp for a cheap test book).
STOP for Rab before the first REAL long-book run (Damodaran is the acceptance test — his
call on timing; it monopolizes the GPU for ~1–2 h even chunked). Done-when: Damodaran
converts end-to-end in slices with resume proven (kill one slice mid-run, re-run, watch it
skip completed slices) and the wedge class is extinct.

## 5. Stage E — queue panel + Dock refresh + light theme

docs/18 §7's adopted mockup elements: a real queue panel (order, priority, est. start from
the ledger-fed estimator), per-item ⋮ menus, richer Dock conversion card, chunk-batch + other
levers as visible selectors, light theme (the S34 token layer already carries dark/light —
finish, don't re-architect). Pure frontend + read-only projections; the queue's ORDER control
needs care: the watcher's queue is `sorted(drop.iterdir())` — an ordering lever means the
watcher consults a sidecar order file (single-writer: the widget writes it, watcher reads —
STOP for Rab to sign that contract change).

## 6. Stage F — the algedonic line + hygiene

Any `died`/`stalled`/`fail`/`EXPORT-HELD` event unacknowledged for M minutes escalates:
Room banner + desktop morning note + Gmail draft (channels in law 11). M and the ack
mechanism = Rab's call (STOP and present options). Hygiene: `events.jsonl` rotation at
session close (the ledger row is the summary), `verified_from` vantage stamps in manifests,
promise-vs-actual lines in `done` events (feeds the S57 conversion ledger).

## 7. Stage G — the Repair Bench (prototype FIRST, under `prototypes/`)

Rab's design, his words load-bearing: **"the human IS the vision model."** Side-by-side
source-PDF page (pymupdf raster) and editable markdown, navigated by the audit's flagged
zones; core capability = screenshot → bundle `assets/` (collision-safe `_repair_pN_k.png`) →
embedded reference at the zone → `manifest["repairs"]` provenance → audit re-scores with
image credit. Valentine (4 table-wreck zones, held) is the first patient. Optional qwen3
text-assist panel; NO vision model needed. Prototype under `prototypes/repair-bench/` per
the quarantine convention (disposable, zero pipeline coupling) — graduate only after Rab
uses it on Valentine successfully.

## 8. docs/17 remainders (mostly RAB-ONLY)

- **Gate 5 checkride (RAB, physical)**: from outside the home — `tailscale ping
  desktop-bndit` must say DIRECT (not DERP), Moonlight bitrate ≤ ~70 % of measured home
  upload (fast.com once), 10 stable minutes. Then tick docs/17 §9.
- **HDMI dummy plug (RAB, hardware)**: seat it; verify monitor-off streaming keeps EDID.
- **§8 event-log spot-check**: from Rab's elevated shell once:
  `Get-WinEvent -LogName 'OpenSSH/Operational' -MaxEvents 20` — confirm remote sessions are
  auditable; note it in the ledger.
- **Sunshine web-UI remote origin**: only when wanted — add the tailnet origin to
  `csrf_allowed_origins` in Sunshine's config (RAB, elevated) + restart.
- **ViGEmBus**: install ONLY if couch-gamepad streaming becomes real (kernel driver,
  upstream discontinued — Rab's explicit call).
- **Gate 6 (WoL)**: stays deferred until Rab wants it (BIOS + Fast Startup OFF).

## 9. Standing open items (small, decide-with-Rab)

Cybernetics' stale held copy (cleanup vs archaeology); standing-enforce (does the audit
lever default to enforce now that bless exists?); Beer's replace-in-place supersede (needs a
`pass` re-convert or a Repair Bench pass — the vaulted degenerate copy is the deliberate
calibration specimen until then); Textor upgrade (source PDF re-download needed); keep_alive
middle for the analyst (~15–25 % wall tax, VRAM courtesy trade); `.ac-held-row` polish and
any UI debt noted in styles.css comments.

## 10. How to fail well

Stop and hand Rab the evidence when: a verification contradicts this doc; a kill/adopt/
deploy needs hands you don't have (laws 3, 12); a contract change touches the vault, the
watcher's queue semantics, or the audit policy (Rab signs those); or the GPU is contended
(law 8). A refused guard, a parked bundle, and an honest "the audit said no" are SUCCESSES —
this factory's soul is that nothing lands unproven. Ship the truth, close in lockstep, leave
a morning note. And if Rab hands you a cookie, log it before anything else.
