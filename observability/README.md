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

## Run it

```bash
python observability/glass_detector.py
```

```bash
python observability/acceptance.py
```

Useful flags: `--enforce` (exit 1 on any unsigned glitch), `--lane bench`, `--json`, and
`--since HEAD~1` for §5.4's same-commit rule — the census restricted to keys *this change*
introduced, which is the only mode that prevents the class rather than finding it later.

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

1. **Generic key names are not checkable this way.** `name`, `id`, `kind`, `size` will find an
   incidental match in any renderer and score `glass`. Distinctive names are checked well.
2. **"Referenced" is not "reaches a human."** This is the law's own gap, and there is a live
   example: `pages_scored` is read by both `main.js` and `room.js` — as the *denominator* that
   positions run marks, never as a number anyone sees. It satisfies §5.1 while docs/29 §7.2's
   complaint ("never printed", the one number that unmasks a vacuous `survival 1.000`) still
   stands. `acceptance.py` pins this case deliberately so the gap stays visible instead of
   being mistaken for a pass.
3. **Only string-literal keys are seen.** `{**r, "anchor_line": at}` contributes `anchor_line`
   and nothing of `r`'s own keys. Computed and f-string keys are invisible.
4. **Dead code counts as a renderer.** A key named only in an unreachable branch scores glass.

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

## Unsigned

docs/29 §8 decision 3 — **whether this runs in CI, in the closeout ritual, or both** — has not
been signed. Until it is, the detector is **report-only** and wired into nothing. `--enforce`
exists and works; nothing calls it.

Also open (§8): the converse projection law as stated · the five dispositions and the six-step
procedure · the same-commit timing rule · whether docs/21 §5's Observable Contract moves from
EXTENDED to **CORE** tier (today a session that ships no code may skip it entirely, which is
exactly how a stored-but-unshown value survives a closeout) · and which of §7's debt gets wired,
in what order.
