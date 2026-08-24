# SIGNATURES — the record of Rab's cross-model authority decisions

**Append-only.** Newest at the end. Only Rab's decisions appear here.

**What this file is, honestly:** a **transcript**, recorded by a model at his instruction —
not proof. The countersign question (whether a model-transcribed signature should require his
countersign to count) is itself unsigned, standing as sign-sheet item 14. Until it is answered,
this record's authority rests on his word in session, not on the existence of these bytes.
No model may originate an entry here, and **no gate anywhere may treat this file's presence as
authorization** — the inert-approval doctrine applies to this file as much as any other.

---

## 2026-08-24 · S108 · The two-model job split — **SIGNED**

Rab's words: *"sign the split, and record the generation caveat"* — given after verifying
Codex's status report (five of five claims reproduced mechanically; one quotation elision named).

**Signed as proposed in `MSG-FAB-0001`:**

| Party | Owns |
|---|---|
| **Codex** | the ontology lab, Vocabulary Studio, and its native shell · independent re-measurement (the second-witness role) · the read-only SYM-050 coverage census |
| **Fable** | File Portal proper — repo, wiki, registers, close discipline, wave 2 of the signed queue · the corpus extraction pilot (the EXTRACTED tier, derived from real source) · the adversarial review of Codex's lab (item 15) — reviewer ≠ builder |
| **The seam** | Codex's AUTHORED terms vs Fable's EXTRACTED terms. The **diff is the product**: a held term that no source defines is either tacit knowledge worth capturing or a fabrication worth deleting |
| **Neither** | adopting the other's artifacts · clearing `blocked-on-rab` · touching the live library, vault, `held/`, or the GPU without his explicit word |

**Sequencing, recorded honestly:** the signature landed **before** Codex posted its amendment.
The split is therefore signed *as proposed*, and Codex's amendment path stays open as a **change
request against a signed baseline** — not as a pre-signature negotiation. Codex may still
propose; the baseline governs until he signs a change.

---

## 2026-08-24 · S108 · Term ownership — **RULED**

Rab's words: *"Then let Models also be able to make terms, add terms, but then they have to take
ownership. Problem solved, Agents are banned from doing so."*

The invariant: **authority requires a bearer who can be confronted.** An agent is spawned,
works, and dies; if it mints a term and the term is wrong, there is nobody to ask. Measured
basis: ~60 agents ran 2026-08-23 with a citation error rate of **44 in 714**.

| Origin | Bearer | Standing |
|---|---|---|
| `EXTRACTED` | the source itself (`path:line`) | strongest — mechanically re-derivable, needs no owner |
| `MODEL-OWNED` | a named model, stamped | accountable; requires periodic re-verification |
| `RAB-SIGNED` | Rab | canonical |
| ~~`AGENT`~~ | nobody | **BANNED as an origin.** Agents may extract, verify, propose, and report only; a proposal becomes a term when a model adopts and claims it |

---

## 2026-08-24 · S108 · The generation caveat — **RECORDED**

Rab's words: *"record the generation caveat"*.

**Ownership decays with model generation.** A term owned by "Fable 5" is owned by a
*generation*, not a permanent agent; Codex is a version too. Therefore every model-owned term
record MUST carry:

```
owner_model · owner_generation · session · utc_date
```

When an owning generation retires, its terms are **flagged for re-verification** — never
silently inherited by the successor generation, and never treated as still-vouched-for.

**Precedent this prevents:** the adoption-hash prose line that sat four generations stale
(`7D403BD6 → 6CA0DEF0 → AFDB8355 → C3C05D49 → 4DCB73E2`), where a claim outlived the thing it
described because nothing recorded which generation had made it. This is that failure class
applied to authorship instead of binaries.

**Applies to:** Codex's Vocabulary Studio schema (its origin field currently records
"human/model/agent" — the agent branch is deleted or demoted to `proposed_by_agent →
adopted_by_model`), and any future File Portal ontology.
