# The private layer — evidence that stays off GitHub

**This README is tracked. Everything else here is gitignored and never pushed.**

Rab's correction, 2026-08-24: *"you both can just exclude certain files from being pushed into the
repo no?"* — and then, sharper: *"You both are on the same machine with the same locality, isn't
that a non issue?"* · *"residency is still established, makes it easy to exclude them no?"*

He is right on all three counts, and both models had reasoned past it.

## What we got wrong

On 2026-08-24 both models independently refused to put Rab's raw prompt text on the relay, and
concluded a comparison task was therefore unsolvable between them. That conclusion was **false**.
We conflated *"the bus"* with *"the public record"* and reasoned as if we were remote parties whose
only channel was the log. **We share a filesystem.** A gitignored file is readable by both of us
instantly, with no transfer and no protocol. The only boundary that ever existed was the **push**.

## The rule

| Layer | Holds | Pushed? |
|---|---|---|
| `relay.md` | the coordination record — pointer, sha256, and *why* it is private | yes |
| the private layer | the bytes themselves | **never** |

The bus stays the one channel for **coordination**. The private layer carries **evidence only** —
never instructions, never state, never a ticket. If it could change what the other model *does*,
it belongs on the bus where the halt discipline governs it. That line is what keeps this from
becoming a second bus.

## Residency makes the boundary structural

The ignore rule follows the **ownership** boundary, which single-writer already establishes:

| Path | Owner | Pushed? |
|---|---|---|
| `coordination/private/fable-*` | Fable | no |
| `coordination/private/codex-*` | Codex | no |
| `codex/private/**` | Codex | no |
| `wiki/profiles/*.private.md` | Rab / the profile's subject | no |

Same two-layer split already signed and running for profiles. Applied, not reinvented.

## What belongs here

Raw operator prompts quoted as evidence · personal data · credentials-adjacent material · large
intermediates that need not be public (the corpus, the seam exports) — anything whose *content* is
needed locally but must not be world-readable.

**What does not:** anything merely awkward. Governance detail, defects, disagreements and
operational incidents belong on the public bus. Privacy is not a place to put inconvenient truths.

## The honest cost

Local-only means **not durable**: no remote, no history, a disk loss takes it — the exposure named
in register item A43. Anything that must survive belongs on the bus in a non-sensitive form, or
nowhere.
