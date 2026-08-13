# docs/26 — The Mass Audit: findings and the gate

**What this is.** The durable record of the S74 self-assessment Circle (2026-08-13), run on
Rab's commission: *"is every visual element you designed, implemented? Do you think you had
done a good job, based on the criteria you set for yourself?"* Method: three independent
verification lanes (subagents with non-overlapping scopes, seeded suspicions + open sweeps,
"do not soften") reconciled by the controller. All file:line citations reference the tree at
`481cd3c` (S74 close). This document is the reference frame for the repair slice (S75) and
the signature sheet below. The methodology itself is packaged as the user-global `/circle`
skill.

**The commissioned answers.**
1. *Implemented?* — Yes: every visible element across Dock/Room/Wall/Bench/drill traced to
   live, data-driven source (lane B); nothing fabricated; nothing untraceable. The docs/25
   mass system covers exactly the signed slices (Wall + rail); Dock and Bench correctly
   await slices 3–4.
2. *Good by own criteria?* — The core held (grammar glow discipline, projection law,
   density, zero deps, token containment). The edges did not: one photographed bleed, one
   self-created accessibility trap, colour-grammar erosion, honesty instruments never wired
   to the glass, and two contradictions inside docs/25's own text.

---

## Verdict vocabulary

HELD (checked, clean) · VIOLATION (breaks stated law) · EROSION (letter holds, meaning
spent thin) · TENSION (criteria self-contradict; human arbitrates) · BLEED (unintended
cross-surface interaction) · HONEST-BUT-CONFUSING (true data, misleading presentation) ·
FRAGILE (correct by accident of implementation) · DEAD (declared but unwired).

## What HELD (lane A + B + C convergent)

- Summons glow sites: exactly two conditions per surface (Gate-with-cards, Assay-fail);
  `fp-ga*/gv*` modulators structurally inert without their summons (`room.js:214,881`;
  CSS custom-property containment).
- Projection law: byte-audit (harness-s74-audit.html) — Room innerText 1 diff char (live
  clock), Wall zero; S74 glow derivations use only existing VM fields.
- Room density: byte-verified unchanged across S73–S74.
- Zero dependencies; station glyphs `▚⚙✳◎⇈▤` byte-identical on all surfaces.
- `--fp-*` consumers: only the sanctioned Wall + rail + modulator blocks.
- `survival 1.000 + fail` on a degeneration case is CORRECT (recall-only metric; loops
  repeat text, they don't delete it).

## Findings — ranked

| # | Verdict | Finding | Evidence (tree `481cd3c`) | Gate |
|---|---|---|---|---|
| F1 | VIOLATION | Reduced-motion incomplete: 7 uncovered animations; 2 **structurally uncollapsible** (assay pulse written as inline `style` animation — inline outranks any media query; the S74 workaround protecting the thock created the trap) | `room.js:210,219,222` (rail), `:878,883` (Wall); worst offender `drill-in` scale-zoom `styles.css:256`; also `vault-glow :396`, `vault-spin :408,555`, `#st-assay.fail :607`, micro-transitions `:116,170` | **Mechanical → S75** |
| F2 | BLEED | Dock's `#status` + `#algedonic-chip` absent from the surface hide-list → status text renders over the Wall hero (photographed by Rab); `#status` min-height + titlebar ⇒ **Wall overflows viewport ~40 px on every launch**; algedonic chip can sit on the Wall up to 30 s | hide rule `styles.css:72-77` (6 of 8 siblings listed); `#status` `index.html:46`, never hidden; overflow: `styles.css:205-206,562`; writer `room.js:624` → `main.js:52-54` | **Mechanical → S75** (Wall-only hide; the Room keeps its sink) |
| F3 | EROSION | Terracotta the *colour* spent on busy/hot/low-score/brand/evidence while glow stayed disciplined — a converting station wears clay ring+glyph on the Wall where colour reads before a 10 px LED at 3 m; clay now carries ≥5 meanings | `room.js:207-212` (rail active), `:864` (Wall Convert), `:260,269,288-292,346,856`; `styles.css:259,552,630,669`; spinning clay sparks `:406-409,553-556` | **Semantic → signature** (decide with slice 3) |
| F4 | HONEST-BUT-CONFUSING + hidden fabrication | `doc_survival` **fabricated as 1.0 when nothing was measurable** (`total_windows == 0`, no-text-layer scans) — meter renders 100%, indistinguishable from perfect; `pages_scored` projected but displayed nowhere; `reverse_sample` (the promised precision tripwire, docs/15) computed, written, **read by nobody** | `fidelity_audit.py:369` (`else 1.0`), `:326-335,385-388`; `assay.rs:135`; display sites `main.js:772,850`, `room.js:379,437` | **Semantic → signature** (null-not-1.0 + show pages_scored; own mini-session) |
| F5 | HONEST-BUT-MISLEADING | Wall hero "SURVIVAL AVG" = lifetime unweighted mean over anchor+pending+held, failures included, `fidelity` and `agreement` metrics mixed, inflated by F4's fabricated 1.0s; drives a colour threshold in hero type | `room.rs:56-98`; `room.js:855-856` | **Semantic → signature** (window/split or relabel) |
| F6 | HONEST-BUT-CONFUSING | "agreement lane" — metric *kind* (`fidelity`\|`agreement`, `fidelity_audit.py:342`) rendered in the lane slot; lanes are `clean`/`scan`; both rendered "lanes" are fictional | `main.js:790,797`, `room.js:389,393` (template `${kind} lane`) | **Semantic → signature** (relabel "scan lane · agreement witness") |
| F7 | TENSION | docs/25 bans "any motion longer than 400 ms" (Part 6 refusals) with no carve-out, while its own Part 3 requests an underglow "breathing slowly" and its concept strip demos the identical 2.6 s breathe that shipped | `docs/25:171,201,233-234` vs `styles.css:127,224` | **Semantic → signature** (amend: travel vs ambient-idle) |
| F8 | VIOLATION (signed) / TENSION | The Wall/Room ambient terracotta radial washes are unconditional clay glow — literally against "nothing else may glow terracotta"; signed in S73 as the hero's floor light | `styles.css:68-71` vs `docs/25:141` | **Semantic → signature** (carve-out or desaturate) |
| F9 | DEAD | `#st-lib` (▤ in the Dock station line) declared, referenced once, never written — permanently "—"; the visible "Library · up to date" comes from the separately-wired `#vault-bar` | `index.html:36`, `main.js:393` | **Mechanical → S75** (wire, don't delete — the six-station grammar wants its ▤ alive) |
| F10 | FRAGILE | Wall verdict bloom gated by string-sniffing `"clay"` from a CSS var name — rename the token and the law silently vanishes | `room.js:891` | **Mechanical → S75** (derive from `sv.word`) |
| F11 | DEFECT | `assay-pulse` + `vault-glow` keyframes hardcode `rgba(217,119,87,…)` — ignore light theme (`--clay:#c15f3c`) and the indigo/teal accent levers | `styles.css:400-403,611-614` | **Mechanical → S75** (token-derived) |
| F12 | DEFECT | `${st.kind}` interpolated unescaped in main.js (room.js escapes it); null renders divergently ("null lane" vs " lane") | `main.js:790,797` vs `room.js:389,393` | **Mechanical → S75** (esc + parity; the *relabel* stays F6/semantic) |
| F13 | TENSION (resolved, recorded) | docs/25 Part 3 says the ACTIVE station glows; charter + concept footnote say hand-required-only. S73 built the charter, recorded the decision | `docs/25:171` vs `:141,201`; `sessions/S73` §8.1 | Closed — document reconciliation rides F7's amendment |
| F14 | GAP (process) | Slice 1's "60 fps trace" proof gate never machine-run — deliberately deferred to Rab's adoption (SYM-001 rationale, recorded) | `docs/25:210`; `sessions/S73` §8.4 | Open — big-screen + perf remain human gates |
| F15 | DEVIATED (inherited) | Part 3's "transform/opacity only → compositor-cheap" vs shipped box-shadow transitions — inherited from the plan's own concept CSS; prose never corrected | `docs/25:170,88-89` vs `styles.css:116` | Semantic-lite → fold into F7's docs/25 amendment |

## The signature sheet (semantic — Rab's pen, with recommendations)

1. **F8 wash** — recommend: keep + sign the ambient-chrome carve-out (≤ current 7–13% clay,
   never animated, outside the summons grammar).
2. **F7/F13/F15 docs/25 amendment** — recommend: "no *travel* motion > 400 ms; ambient
   opacity idles exempt; all motion collapses under reduced-motion"; fix the Part 3 row's
   active-wording and the compositor claim in the same pass.
3. **F6 relabel** — recommend: "scan lane · agreement witness" / "clean lane · fidelity
   witness".
4. **F4+F5 survival honesty** — recommend: `null` not 1.0 when unmeasurable; `pages_scored`
   on the card; Wall avg windowed or relabelled "lifetime". Touches Python + manifests —
   own mini-session.
5. **F3 terracotta colour policy** — recommend: busy moves off clay (flow/neutral + mass);
   clay becomes summons-only in colour as well as glow. Decide WITH slice 3 so Dock+rail
   change once.

## Standing context recorded at filing (Rab, in-chat, 2026-08-13)

The Repair Bench's operating doctrine is UNDISCOVERED: no canonical example of a good
repair exists yet; target entropy loss 0.01–1.00% as a minimum-operator-work measure
(acknowledged non-guaranteeable). A discovery mission (agents; semantic + visual catering
to operator simplicity) is queued AFTER this sheet resolves. Bench-dependent signatures
(transcribe thresholds, audit credit) are deprioritized until that doctrine session.

## What the next Circle inherits

S75 executes the Mechanical column. Its acceptance is a `/circle` run against this
document. The signature sheet then gates everything semantic; slice 3 (Dock) follows on
the cleaned base; the operator-simplicity discovery mission follows the signatures.
