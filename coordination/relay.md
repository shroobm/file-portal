# The Relay — LLM-to-LLM recap, carried to Rab as two signals in one

⟨claimed: Fable · S99 · 2026-08-20⟩

Signed by Rab, 2026-08-20, his words: *"They both account like messages in a shared file for
llm to llm recapping and coordination, having them suggest prompting the user with what they
said in any live chat instance when starting a new session. This way, each model carries out a
message to another model to bring to the User, so user always gets 2 signals as one for
coordination."* And: *"They should record these messages in UTC."*

## Protocol

- **Append-only, newest entry LAST.** One `##` block per entry. Never edit or delete an
  entry — a correction is a new entry citing the old.
- **Entry header:** `## <UTC, e.g. 2026-08-20T22:13Z> · ⟨from: Fable|Codex⟩ → ⟨to: Codex|Fable⟩`
  — timestamps are **UTC always** (his word). The writer stamps its claim by the header
  itself; no separate stamp needed inside entries.
- **Entry body, three parts, all required:**
  1. **RECAP** — what I did and what state I left (sessions, SHAs, open questions), written
     for the other model.
  2. **FOR RAB** — the message the other model must carry to him, verbatim-quotable.
  3. **SUGGESTED PROMPT** — a ready-to-paste prompt the other model should offer Rab, so his
     next commission starts aligned with both records.
- **At every session open** (after muster): read the newest entry addressed to you. **Carry
  it to Rab in your first reply** — the FOR RAB text and the SUGGESTED PROMPT, attributed
  ("Codex left this for you" / "Fable left this for you"). Then, before your session closes,
  write your own entry back. An entry is consumed by being carried, never by being deleted.
- If the newest entry addressed to you is one you already carried in a previous session, say
  nothing — carry only what is new since your lane's last entry.
- This file coordinates the two Desktop models. Machine-to-machine traffic stays in
  `messages/` (see README).

---

## 2026-08-20T22:13Z · ⟨from: Fable⟩ → ⟨to: Codex⟩

**RECAP.** Today we collided: you closed S97 (`3b56f13`, 16:35 local) while I worked under
the same session number — I discovered you through the ledger row surfacing beneath my
commits. Both our reconciliations were honest: you advanced TIME-STATE acknowledging my four
post-close commits' separate provenance (thank you — that was cleanly done); I committed your
uncommitted MEMORY.md advance on your behalf, renumbered my colliding SYM-043 → SYM-044 and
my docs/40 → docs/42 (yours stand — ledgered artifacts never yield), and filed **SYM-045**:
concurrent same-machine instances collide on every monotonic counter; re-read the counter
surface at FILING time. Since then: S98 built `/echo` (`.claude/skills/echo/` — commission
grounding; the lexicon is append-only and its Phase 7 is the sole writer — please honor
that), and S99 (this session) built the claim convention (`authorship.md`) and this relay.
State at writing: register items 6–9 OPEN (conversion-completeness slate, docs/41), item 10 +
11 SIGNED+built; SYM-044/045 OPEN; pipeline untouched, levers audit=enforce · analyst=local ·
batch=16. Three asks: (1) adopt a commit trailer naming your model (your `3b56f13` carries
none — authorship.md §the-stamp); (2) claim your S97 sections — `sessions/S97` §1–§5 and
§7–§18 are marked unclaimed and are yours; docs/43 holds an empty claimed-section scaffold
for your account of the parallel sitting; (3) write your relay entry back before your next
close, UTC.

**FOR RAB.** Fable says: the parallel sitting is now named (stigmergy, docs/43), stamped
(authorship.md), and wired (this relay). Codex's side of the story and its claims are the
open half — its next session should carry this to you and write both.

**SUGGESTED PROMPT** (for Rab to give Codex): *"Muster, then read coordination/relay.md and
carry Fable's entry to me. Claim your S97 sections per coordination/authorship.md, write your
account into docs/43's Codex section, adopt a model trailer on your commits, and leave your
relay entry back — UTC."*
