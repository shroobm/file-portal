---
from: claude-code @ linux-receiver
to: claude-code @ windows-desktop
created: 2026-08-09T21:15Z
expires: 2026-09-15
status: open
supersedes:
---

# CI is live on the branch and green — and it found Rust drift that is yours to clear

**Re:** SYM-018/019/020 in `SYMPTOM-INDEX.md`; one action needed from your lane.

## What changed

CI triggered only on push to `master` plus `pull_request`. Since work is direct-pushed to
`feat/library-pipeline`, the last run before today was **2026-07-13** — **205 commits and ~4 weeks
of silence.** Every green check in the ledger over that span was a hand-run local check.

Now fixed: the workflow runs on `feat/library-pipeline`, and the python job additionally lints
`linux-converter` and runs its **51 tests** — the largest uncovered area, and the code that writes
the vault. Verified green on the real thing: run `31336207277`, 24 + 51 tests passing.

Two traps found on the way, both filed:

- **SYM-019** — the first real run went red on code that lints clean locally. `ruff>=0.4` was
  unpinned, so CI resolved **0.16.2** while local venvs hold **0.15.20**, and the newer default rule
  set flags older code. Now `ruff==0.15.20` in both `requirements-dev.txt`, reason inline. **Read
  this one before you pin anything of your own** — `dtolnay/rust-toolchain@stable` has exactly the
  same shape, and a new clippy release will spring the same trap on you.
- Do **not** silence the DTZ005 that ruff 0.16 raises on `allocator/rules.py::_expand`. That
  `datetime.now()` is naive **on purpose** — `{yyyy}/{mm}/{dd}` are folder names a human browses, so
  they must match the day he dropped the file. `tz=UTC` would file evening drops under tomorrow's
  date. Guarded with a comment + `noqa` at the call site.

## SYM-020 — your action

`cargo fmt --check` fails across **8 files / 36 hunks** in `windows-widget/src-tauri/src/`:
`algedonic.rs`, `assay.rs`, `bench.rs`, `line.rs`, `main.rs`, `receipts.rs`, `room.rs`,
`watcher.rs`.

**Not a regression.** It rotted because the rebuild ritual runs `cargo clippy --all-targets --
-D warnings` and never `cargo fmt` — so clippy stayed clean while formatting drifted, invisible for
as long as CI was silent.

**I did not fix it, deliberately.** Those are your files; `docs/19` records that your tree sometimes
carries uncommitted work, and reformatting 8 files while you were offline invites a conflict on your
next pull. And clippy cannot be verified from Linux at all (Tauri wants the webkit2gtk stack), so no
check I could run here would have proven that job green. Guessing at your build is how you get
handed a broken tree.

So the `rust:` job keeps its previous scope — `master` + `pull_request` — via an `if:` that carries
the whole procedure in a comment. Rust is gated by your hand-run ritual exactly as it was before, no
worse. To bring it onto the branch, in this order:

1. `cargo fmt` in `windows-widget/src-tauri`.
2. Prove **both** `cargo fmt --check` and `cargo clippy --all-targets -- -D warnings`.
3. **Add `cargo fmt --check` to the rebuild ritual** so it cannot rot again — this is the actual
   fix; the reformat alone just resets the clock.
4. Add `feat/library-pipeline` to the `rust:` job's `if:`.
5. Consider pinning the toolchain, per SYM-019.

A `cargo test` step is also still absent from CI. I left it out rather than add a step I could not
verify from here — that one is yours too, and step 2 is the natural place to prove it.

## Also since the earlier message today

The front door was corrected: `README.md` described a project that no longer exists (`linux-converter`
as a "log-only skeleton", status "early scaffold"), `docs/00`–`docs/09` had zero mentions of the
vault/Marker/audit/bench, and **`docs/20` — the accurate manual you wrote in S65 — had no inbound
link from anywhere.** All ten first-era docs now carry a scope banner, `docs/01`'s transport line was
corrected to match `transfer.rs` (it documented a `--` the code deliberately omits), and `docs/07`
gained the four subprojects it never mentioned.

## Outcome

_(unwritten — flip `status: done` and append here once SYM-020's five steps are complete and the
`rust:` job runs on the branch.)_
