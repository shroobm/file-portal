# docs/33 — Circle: does an embedded assistant fit File Portal?

**Commission (Rab, S79, 2026-08-15):** *"based on the design principle do a /circle to see if it
would fit… examine exactly what would be needed to implement this, research and develop a sound
plan, and attempt to negotiate the potential problems before implementation."*

**The design under assessment.** A button in the Room loads a local model (llama.cpp, already
installed and serving Ollama's own GGUF); a chat window opens and greets the operator with a
model-loaded confirmation; a second button unloads it. **A convert cannot happen while the chat
is loaded, and vice versa.** Purpose: help an operator navigate the widget and answer questions
about the project itself — Rab's words, *"like a mini you."*

**Method divergence, declared.** Rab barred subagents for this session, so the Circle's
independent lanes were passes run by one head with deliberately different methods (law recovery
from the docs · source reading · a grep sweep for precedent). Lanes that share a head share its
blind spots. This Circle is weaker than S74's and S78's for that reason, and the finding most
likely to be missed is the one nobody thought to grep for.

---

## 1. The questions, answered first

**Q1 — Does a generated-text surface fit the projection law?** **No, not as written.** It needs
an explicit amendment, and the amendment is Rab's to sign. See §2.1.

**Q2 — Does an assistant answering navigation questions violate verify-before-instruct?**
**Yes, as specified.** It is lawful only as a *citation engine*. See §2.2.

**Q3 — Can the mutual exclusion be built lawfully?** **Yes**, and it must actually be built —
there is no mutex today. See §2.3.

**Q4 — Is `bench.rs`'s pattern reusable?** **Yes, and it is the right foundation** — but a
copy-paste ships three defects. See §2.4–2.6.

**Q5 — Overall: does it fit?** **The infrastructure fits cleanly. The doctrine does not fit
without one amendment Rab must sign** — because in the whole history of this widget, no surface
has ever displayed a sentence the machine composed.

---

## 2. Findings, most severe first

### 2.1 TENSION — the projection law has no room for a generated sentence

docs/13, first law: the widget *"renders and requests, never owns … **Any surface of the widget
must be reconstructible by reading the filesystem.**"*

A chat reply is not reconstructible. Ask twice, get different words. Under the letter of the
law, a chat panel is not a permissible surface.

**Precedent check (`Observed 2026-08-15`):** a grep across `windows-widget/src/room.js`,
`main.js` and `index.html` for `ollama|llm|prompt|generate|chat` returns **nothing**. Every panel
that exists — `queuePanel`, `stationRail`, `kpiTiles`, `convertPanel`, `assayPanel`,
`eventsPanel` — renders values read from disk. **This would be the first non-derived surface in
the widget's history.**

The law's *purpose* survives the amendment, though. docs/29 §1 names it: this is *"a law written
to prove the UI cannot do harm."* It forbids the UI to invent state. A reader that quotes does
not invent.

**Proposed amendment, for Rab's pen:**

> The chat may never assert pipeline state in its own words. Any live number, verdict or
> status it shows must be rendered through the existing projection path, verbatim. The model
> may explain documentation and point at a surface; it may not restate what that surface says.

With that, the law holds: the panel's *state* content is still `project(f)`, and only the
*explanatory prose* is generated. Without it, the widget's founding law is quietly broken by its
newest feature — which is precisely the erosion this project keeps paying for.

### 2.2 VIOLATION — verify-before-instruct, as specified

The standing rule (memory `file-portal-verify-before-instruct`, S48): *any "click X / do Y"
instruction about File Portal is checked against CURRENT source first, **never from recall**.*

A model answering from baked context **is** answering from recall. That is the definition. The
rule exists because a Claude session told Rab the ⚡ tile was a switch; it is a drag target. An
8B model will make that class of error more often and with more confidence, and the operator it
misleads is by construction the one least able to catch it.

**The only lawful shape is cite-or-refuse:** every navigational claim carries a citation the
operator can open (`docs/20 §6`, `main.js:556`), or the assistant declines. No citation, no
answer. That converts it from an oracle into a librarian, moves the verification to where the
rule requires it, and — as a side effect — makes it more useful, because a pointer to the manual
outlives a paraphrase of it.

### 2.3 VIOLATION — `.gpu-lock` is not a lock, and an hour ago I said it was

`watch_and_convert.py:33` — `LOCK_FILE = BASE / ".gpu-lock"  # busy signal for the future
control-room card`. It is **written** at `:77` before a convert and **deleted** at `:86` after.
**Nothing anywhere reads it as a gate** (`Observed 2026-08-15`).

There is no mutual exclusion in this pipeline today. A file named `lock` locks nothing — the
exact defect Rab named when he said the surface *"has a name that was built on the intuitive,
and not the engineering logic it deserves."*

**My own error, first-class:** I told Rab "the signal already exists" and designed against it.
That was an inference stated as an observation, in a session whose entire subject is that
failure.

**Lawful mutex — two files, two owners, no shared writer** (the `analyst-mode.txt` pattern:
widget writes intent, Python re-reads per use):

| Direction | Reads | Written by |
|---|---|---|
| chat wants to load | `.gpu-lock` | converter (widget only reads — the projection law, correctly) |
| convert wants to start | `chat-hold.json` | **widget** (new file, widget is sole writer) |

Load is two-phase: write the hold, *then* read `.gpu-lock`; if the lock is there, remove the hold
and refuse. Recording precedes action (docs/28's chokepoint), and the ordering makes the chat
yield to the pipeline — a convert is expensive and interruption-hostile; a chat session is
neither.

### 2.4 FRAGILE — `bench.rs`'s readiness wait would report a healthy server dead

`bench.rs:152-167` waits `30 × 200 ms` = **6 seconds**, then returns *"bench server did not come
up — see bench-stderr.log"*. Correct for `bench.py` (stdlib, instant). **llama-server takes
~20 s to load an 8B model cold** (`Observed 2026-08-15`: 19.54 s first load, ~4.7 s warm).

A copy-paste of this pattern fails every cold start, tells the operator the server is dead while
it is loading normally, and leaves an orphan the next attempt collides with. The wait must scale
to model load and the message must distinguish *still loading* from *died*.

### 2.5 BLEED — port range collision

`bench.rs:80-84` scans **7077..7097** — the bench's range. A chat server taking 7077 makes the
next Repair Bench open fail or land on a port the bench window does not expect. The chat needs
its own range.

### 2.6 Gap — a new config key, and the convention that hides the feature

`bench_script()` derives its path from the repo layout, so the bench needed no config. **llama-server
lives outside the repo** (`C:\Users\Bndit\ml\llama\`), so a key is unavoidable:
`llama_server_exe: String`.

That is not a cost — `config.rs`'s convention is **empty key = feature hidden** (docs/20 §11), so
the button simply does not exist on a machine that has not set it up, including the ThinkPad.
The feature is opt-in by construction.

### 2.7 Owed — docs/29 §5.4, in the same commit

Every field the panel projects — model name, quant, port, resident VRAM, hold state, token counts
— must be **rendered or dispositioned in the commit that adds it**. The detector runs `--since`
at close and will find them. This is the law most likely to be skipped in the excitement of a
new surface, and the one whose whole history is that retrospective sweeps do not prevent it.

### 2.8 HELD — what checked out clean

`bench.rs`'s spawn discipline is genuinely the right foundation and inherits four paid-for
lessons intact: detached spawn with null stdin/stdout, a last-words stderr file, `adopt_into_job`
(S37 — dies with the widget by any exit), slow work off the UI thread, and window creation on the
main thread with reuse-or-create by label. Its `BenchState` shape (one live at a time, replace on
a different target) is exactly the chat's lifecycle. Its four unit tests are a template.

---

## 3. The gate

### 3.1 Mechanical — unambiguous under signed criteria, may be built

1. Readiness wait scaled to model load, with *loading* distinguished from *died* (§2.4).
2. A distinct port range for the chat server (§2.5).
3. `llama_server_exe` config key, empty-hides-the-feature (§2.6).
4. The quarantined prototype itself, under `prototypes/`, zero pipeline coupling.
5. Cite-or-refuse plumbing and the curated context bundle.

### 3.2 Semantic — Rab's pen, and nothing is built until they land

1. **The projection-law amendment (§2.1).** Generated prose as a widget surface at all, and the
   rule that live state is quoted, never restated. This changes what "surface" means in a corpus
   where that word has had one meaning since docs/13.
2. **The watcher deferral gate (§2.3).** It adds a refusal path to the conveyor — the module
   where a mistake means a book silently does not convert. docs/19 §5 places this class squarely
   with Rab.

### 3.3 Evidence-insufficient — do not guess

Whether an 8B (or 1.7B) model is *good enough* at this task. Nobody has measured it. The
acceptance test is Rab's own ten questions — the things he or a new operator would actually type
at 2am — and they decide whether curated context suffices or retrieval is required. Designing the
context window before seeing the workload would be choosing a proxy and calling it the property.

---

## 4. What the next Circle inherits

Whether §3.2's two signatures were taken before anything was built. Whether §2.7 was honoured in
the same commit or deferred "just this once". And the standing prediction from docs/32 §6: the
next instance of proxy substitution appears in whatever is built next to enforce a rule — which
here is the mutex, since a lock is a proxy for exclusion, and this Circle has already caught one
lock that locked nothing.
