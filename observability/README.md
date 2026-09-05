# `observability/` — the read side

The write side of this project is strong: docs/28's chokepoint means recording precedes the
write, and the repair ledger means no write escapes the record. Nothing ever governed the
**read** side. docs/29 named the gap — every law in the corpus with teeth governs what may be
*written*, none governs what must be *read*, so a producer can write a key into a shared
payload and a consumer pays **zero cost** to ignore it. The S77 census counted **~83 fields**
computed correctly, persisted correctly, and reaching no human at all.

This directory is docs/29 §5 made mechanical.

| File | What it is |
|---|---|
| `glass_detector.py` | §5.1 — walks every dict a producer returns or persists, checks each key against the renderers |
| `dispositions.json` | §5.2 — the lane map, and the signed-silence record |
| `acceptance.py` | The detector's own acceptance: docs/29 §7 as an answer key |
| `schema_registry.py` | A4 — regenerates filesystem-contract keys/paths from the real writers and checks consumer parity |
| `schemas.json` | The deterministic generated registry; evidence, never a second handwritten source of truth |
| `schema_registry_selftest.py` | Hermetic positive and planted-negative controls for A4 |

## Run it

```bash
python observability/glass_detector.py
```

```bash
python observability/acceptance.py
```

```bash
python observability/schema_registry.py --check
python observability/schema_registry_selftest.py
```

The A4 check is narrower and stronger than the glass census. It covers the signed filesystem
contracts (`events.jsonl`, `coverage_rescore --json`, slice `.done`, both progress files, and
the conversion ledger), preserves event variants and nested JSON paths, and exits nonzero if a
writer changes without regeneration or a consumer names a path that writer does not emit. It
is static and stdlib-only: no converter module is imported and no live pipeline file is read.
Dynamic spreads must resolve from source or the check fails `UNREAD`; they never disappear into
a partial green registry. Run `--write` only when the writer change is intentional, inspect the
diff, then run the selftest. `.intake-state.json` and `.convert-estimate.json` are named in the
registry as explicit exclusions from this signed ticket, not silently implied coverage.

`--since <ref>` is **the signed mode** — §5.4's same-commit rule, the census restricted to the
keys *this change* introduced, which is the only mode that prevents the class rather than
finding it later. The closeout ritual runs exactly this against the previous ledger SHA
(`CLAUDE_README.md` §4, `docs/21` §3):

```bash
python observability/glass_detector.py --since <last ledger SHA>
```

Other flags: `--enforce` (exit 1 on any unsigned glitch), `--lane bench`, `--json`.

## What a run tells you

Every key lands in one of three buckets:

- **glass** — a renderer names it. Silent, nothing to do.
- **signed silence** — `dispositions.json` names it, with a disposition and a reason.
- **GLITCH** — neither. This is docs/29's definition: a real terminus whose §5.3 step-4 answer
  is *nowhere*.

The detector never decides which of the five dispositions a field deserves; it only refuses to
let the question go unasked. Before adding an entry, walk §5.3 **in order** — the sharpest
question is step 4, *"does this already have a home anywhere, live or archival?"*. `REPAIRS.md`
is a home. A receipt is a home. Silence is a defect only when the answer is nowhere.

## Read this before trusting a clean run

The detector is a **floor**. What it reports is real; what it passes is *not proven*.

1. **Generic key names are not checkable this way.** `name`, `mode`, `kind`, `size` will find an
   incidental match in any renderer and score `glass`. Distinctive names are checked well.
   (`id` and `ts` are shorter still and never reach this test at all — see 5.)
2. **"Referenced" is not "reaches a human."** This is the law's own gap, and there is a live
   example: `pages_scored` is read by both `main.js` and `room.js` — as the *denominator* that
   positions run marks, never as a number anyone sees. It satisfies §5.1 while docs/29 §7.2's
   complaint ("never printed", the one number that unmasks a vacuous `survival 1.000`) still
   stands. `acceptance.py` pins this case deliberately so the gap stays visible instead of
   being mistaken for a pass.
3. **Only string-literal keys are seen.** `{**r, "anchor_line": at}` contributes `anchor_line`
   and nothing of `r`'s own keys. Computed and f-string keys are invisible.
4. **Dead code counts as a renderer.** A key named only in an unreachable branch scores glass.
5. **Keys shorter than three characters never enter the census at all.** `MIN_KEY_LEN = 3`
   (`glass_detector.py:64`) — a one- or two-character name cannot carry a meaningful
   word-boundary search. Measured on today's tree: `id`, `ts`, `at`, `by`, `mb`, `q`, `n`, `i`
   — **10 `lane:key` signatures at 38 sites**, silently skipped. It changes no verdict *today*:
   every one of the ten is named by a renderer and would have scored `glass` anyway. Disclosed
   because the exemption is silent, not because it is currently wrong — a short key that goes
   dark goes dark invisibly.
6. **The detector knows key *names*, not producer *sites*.** A lane's renderers are
   concatenated into one flat blob, so a key is cleared by *any* payload naming it — never
   specifically the payload it was produced into. This is why docs/29 §7.10's finding is
   invisible. There are three `setdefault("repairs", …)` sites, and the keys come from two of
   them: `model`, `gates` and `secs` are persisted by the **transcribe** record
   (`bench.py:862-865`, appended at `:866`), `cycle` by the **collapse** record
   (`bench.py:943-946`). None is read back from the manifest by anything, yet all four score
   `glass` off the *transcribe proposal*'s `gateLine()` (`bench.html:838`) and the *collapse
   preview* (`bench.html:887`) — the same names carried on different payloads.
   *(docs/31 §1.9 cited `bench.py:944-948` for all four, and the first correction of this line
   moved the numbers without fixing the conflation. Two passes to get a citation right is worth
   recording: the census tells you a key is clear, never which payload cleared it.)* §7.10's own wording is
   "goes dark **once persisted**", and the detector cannot express "once". Whether it gains
   site-awareness is docs/31 §5.2 item 4, unsigned.

No stdlib-only static check fixes these. They are precisely why **§5.4's same-commit timing
rule is the part that actually prevents the class**, and this script is only the net stretched
underneath it. Retrospective sweeps find glitches; only concurrency stops them.

## Why the acceptance harness is end-to-end

It runs against the real trees, never fixtures. A fixture would share the extractor's
assumptions about what a producer *looks like*, and two checks that share an assumption are one
check (SYM-001). That is not hypothetical here: the first version of the detector tested for
`Return(Name)` and `Return(Dict)`, while the repo's two largest producers return a **tuple**
holding the payload — so it silently missed `seams` and `chunks_resumed`, two of the ten
findings it exists to reproduce. The answer key caught it in the first run. A fixture would
have passed.

## Signed, and still unsigned

**SIGNED — Rab, 2026-08-14, docs/29 §8 decision 3.** Two things at once: the **same-commit
timing rule** (§5.4), and **where the detector runs — the CLOSEOUT RITUAL, in `--since` mode**,
the census scoped to the keys that session introduced. **Not CI.** The standing backlog stays
advisory and blocks nothing. The ritual step lives at `CLAUDE_README.md` §4; `docs/21` carries
it in §3 (derived sources) and §4 row 5 (Observable Contract).

*(This section read "has not been signed… wired into nothing" for the whole of S78 — while
`docs/29:185` cited this very file as the authority on the built tool. A citation loop, and the
observability class reproduced inside the instrument built to detect it. Found by docs/31 §1.4,
not by anything mechanical. Kept here rather than quietly overwritten, because the tool's own
subject is what happens when a recorded fact reaches nobody.)*

**Still open** — labelled by docs/29 §8's own item numbers, so decision 3 is the gap:

- **§8.1** — the converse projection law (§4) as stated.
- **§8.2** — the five dispositions (§5.2) and the six-step procedure (§5.3). Note that
  `dispositions.json`'s `dispositions` block is still `{}`: the signed-silence mechanism this
  directory exists to serve has never been exercised on one real judgment.
- **§8.4** — whether the Observable Contract moves from EXTENDED to **CORE** tier. Today a
  session that ships no code may skip it entirely, which is exactly how a stored-but-unshown
  value survives a closeout.
- **§8.5** — which of §7's debt gets wired, and in what order. **The census is not yet
  trustworthy enough to disposition against** (docs/31 §5.3): 22 keys score `glass` off producer
  trees wrongly listed as renderers, and 7 of 8 checked omissions are wrong — mostly limit 6
  above. Mechanical fixes, then re-run, then disposition.

And docs/31 §5.2 opens a sheet of its own on this tool: site-awareness (limit 6), whether a
signed `GLASS` should be distinguishable from glass-by-reference, and the lane topology.

## Keys the harvester cannot see (S115, 2026-09-05)

The detector's writer census is an AST walk over dict literals and `emit()` calls. A manifest key
assigned by **subscript** — `manifest["marker_body"] = {...}`, `fid["final"] = final`,
`fid["reaudit"] = {...}` — is invisible to it, exactly as J24's bare `blocks` key was. Measured on
2026-09-05 (S115, lane 1 and the INTEGRATION refuter, `wf_6fca68fd-b1d`): adding a
`converter:marker_body` disposition for such a key does not resolve anything — it trips the
acceptance harness's *stale signature* check ("the key is gone, the disposition remains"),
139/139 → 140/141. So the six J31/J33 manifest keys — `fidelity.final{text_audited, reference}`,
`fidelity.reaudit{repairs_digest}`, `marker_body{file, bytes, sha256}` — carry **no** entry in
`dispositions.json` by design, and this note is their record: they are EVIDENCE (read by
`reaudit()` and by the exporter's `_record_marker_body`, never rendered), and a future harvester
that learns subscript assignment will surface them for a real disposition. Related: since J32-B /
SYM-074, `chunks_rejected` counts ALL rejections (fence + survival + think_leak), not fence only —
`converter:rejections`'s reason carries the widening.
