# docs/34 — The Measurement Language

**Status:** design law, S81 (2026-08-15). Binds every measured number this project states — in a
closeout, a ledger row, a commit message, a chat reply, or on a surface.

**Who reads this:** the operator and the machine, equally. It is written so that a person who has
never seen this repository can read one of our numbers and a stranger's benchmark and have the two
mean the same thing. Nothing here is invented vocabulary. Every term is the term the field already
uses; where our house word differs, §6 translates it.

---

## 0. Why this exists

S79 measured llama.cpp against Ollama and recorded the result as *"+27 % tok/s and 1.72×
batching."* At S80's open those numbers could not be used. Not because they were wrong — nobody
knows whether they were wrong — but because the sentence does not say **what was counted, over
what clock, under what conditions**. `+27 %` of which tokens? Input or output? Warm or cold? One
request or many? Against which build?

A number stated that way is not a measurement. It is a rumour with a decimal point.

This is Rab's S79 law — **a name must carry a mechanism** — applied to quantities. A rate must
carry its numerator, its denominator, and its conditions, or it may not be stated at all.

---

## 1. The five costs inside one request

Every request to a local model pays up to five separable costs. Almost every misleading benchmark
in circulation comes from quoting one and implying another.

| # | Cost | What is happening | Paid when |
|---|---|---|---|
| 1 | **Load** | weights are read from disk into VRAM | only on a cold start |
| 2 | **Prefill** | the input tokens are processed to build the KV cache | every request, proportional to input length |
| 3 | **Decode** | output tokens are produced, one at a time | every request, proportional to output length |
| 4 | **Transport** | HTTP, JSON encode/decode, process hop | every request |
| 5 | **Queue** | waiting behind other requests | only under concurrency |

**Prefill and decode have different physics.** Prefill is compute-bound and highly parallel — it
processes the whole prompt at once. Decode is memory-bandwidth-bound and sequential — each token
waits for the one before it. On the same hardware and model, prefill routinely runs **3–10×** the
tokens per second that decode does. Reporting a single blended "tok/s" therefore says almost
nothing: change the ratio of input length to output length and the blended figure moves without
anything about the machine having changed.

> **Observed, S81:** on this card, qwen3:8b, a 15-token prompt: prefill 339.6 tok/s, decode
> 56.1 tok/s — a 6.1× difference **within one request**.

---

## 2. The vocabulary

These are the standard terms. Use them; do not coin alternatives.

| Term | Definition | Also called in the wild | Unit |
|---|---|---|---|
| **prefill** | processing input tokens before the first output token | prompt processing, `pp`, prompt eval | tokens; ms |
| **decode** | producing output tokens, sequentially | generation, `tg`, eval, predict | tokens; ms |
| **prefill throughput** | prefill tokens ÷ prefill duration | prompt tok/s, `pp` rate | tokens/s |
| **decode throughput** | decode tokens ÷ decode duration | generation tok/s, `tg` rate | tokens/s |
| **TTFT** | request sent → first output token received | time to first token | ms |
| **TPOT** | mean time between successive output tokens | inter-token latency, ITL | ms/token |
| **end-to-end latency** | request sent → last byte received, transport included | e2e, wall time, round trip | s |
| **load time** | weights disk → VRAM, until the server answers healthy | cold start, model load | s |
| **cold / warm** | whether load time is inside the number or outside it | — | — |
| **concurrency** | requests in flight simultaneously | — | count |
| **batch size** | requests the *server* fuses into one forward pass | — | count |
| **goodput** | throughput counting **only** output that passed acceptance | — | tokens/s |
| **p50 / p95** | median / 95th percentile of a sample | — | same as measured |

**`throughput` is never used bare.** It is always *prefill throughput* or *decode throughput*. An
unqualified "tok/s" is not admissible in this project.

**Concurrency ≠ batch size.** Concurrency is what the client does; batch size is what the server
does in response. S79's "1.72× batching" names neither, which is one of the reasons it cannot be
banked.

**Goodput is the one that pays the bills here.** The analyst's output is only worth anything if it
passes the image fence — a truncated rewrite drops trailing `⟦IMG-n⟧` and the un-analyzed original
ships. Tokens produced and then rejected are waste, not throughput. Where a rate is quoted for the
analyst, prefer goodput and say so.

---

## 3. The seven rules for stating a number

1. **Name the numerator and the denominator.** "Decode throughput 56.1 tok/s" — output tokens over
   decode-phase seconds. Not "56 tok/s".
2. **Never mix cold and warm in one figure.** Load is reported separately or excluded explicitly.
   A cold first request can be 10× the wall time of the warm ones after it; averaging them
   produces a number describing no real request.
3. **State `n`, and a spread.** A bare mean hides its own dispersion. Give `n` and either p50/p95
   or min–max. One measurement is `n=1`, and must say so.
4. **A ratio prints both of its sides.** Not "1.72× faster" but "1.72× (A 96 tok/s vs B 56 tok/s,
   both warm decode)". A speedup whose two halves are not shown cannot be checked, and cannot be
   re-derived when the conditions change.
5. **A percentage prints its base.** "+27 %" is meaningless without "of what, measured how".
6. **A rate requires a duration the backend actually reported.** If the timing field is missing,
   the honest output is `UNREAD` — never `0.0 tok/s`, never a silent fallback to wall time
   presented as if it were the model's own clock. (SYM-031: a failed probe may not render as a
   reading.)
7. **Sampling never promotes.** N chunks measured is `Inferred` about the corpus, never `Observed`
   about all of it. Say which, and give N.

**Corollary — state the build.** A rate belongs to a specific engine build, model file, and
hardware. llama.cpp reports `system_fingerprint` (e.g. `b10448-ad1de39e0`); Ollama reports its
`version`. Record it beside the number, or next month's comparison is against an unknown.

---

## 4. Where the numbers come from — the field map

`Observed 2026-08-15` (S81) by direct probe of both backends. **Do not quote a field that is not
in this table without probing for it first.**

### Ollama — `POST /api/generate`, `"stream": false`

| Field | Meaning | Unit |
|---|---|---|
| `load_duration` | cost 1, model load | **nanoseconds** |
| `prompt_eval_count` | prefill tokens | tokens |
| `prompt_eval_duration` | prefill duration | **nanoseconds** |
| `eval_count` | decode tokens | tokens |
| `eval_duration` | decode duration | **nanoseconds** |
| `total_duration` | server-side end-to-end | **nanoseconds** |
| `done_reason` | why generation stopped (`stop`, `length`) | — |

### llama.cpp `llama-server` — `POST /v1/chat/completions`

| Field | Meaning | Unit |
|---|---|---|
| `usage.prompt_tokens` | prefill tokens | tokens |
| `usage.completion_tokens` | decode tokens | tokens |
| `usage.prompt_tokens_details.cached_tokens` | prefill tokens served from cache | tokens |
| `timings.prompt_n` / `timings.prompt_ms` | prefill tokens / duration | tokens; **milliseconds** |
| `timings.prompt_per_second` | prefill throughput, server-computed | tokens/s |
| `timings.predicted_n` / `timings.predicted_ms` | decode tokens / duration | tokens; **milliseconds** |
| `timings.predicted_per_second` | decode throughput, server-computed | tokens/s |
| `timings.cache_n` | tokens reused from the KV cache | tokens |
| `system_fingerprint` | engine build | — |
| `choices[0].finish_reason` | why generation stopped (`stop`, `length`) | — |

> ### ⚠ The unit trap
> **Ollama reports nanoseconds. llama.cpp reports milliseconds.** They are the same shape of
> number in the same position of the same kind of response, and they differ by **10⁶**. A rate
> computed with the wrong divisor is not obviously wrong — it is off by a factor of a million,
> which reads as either absurd or, worse, plausible after a second mistake. Convert both to
> **seconds** at the boundary, once, and never carry a raw duration further than that.

> ### ⚠ Cached prefill is not measured prefill
> Both backends reuse the KV cache across requests that share a prefix. When `cached_tokens` or
> `cache_n` is non-zero, part of the prefill did not happen.
>
> Note carefully what the fields mean: **`timings.prompt_n` counts only the tokens actually
> processed**, not the prompt's length. A fully cached prompt therefore reports `prompt_n = 1` and
> yields a rate that is arithmetically correct, internally consistent, and a description of a
> one-token prefill. It is not wrong. It is meaningless, which is harder to notice.
>
> **The rule: a prefill rate is withheld — `UNREAD` — when more than 20 % of its prompt arrived
> from cache.** Not footnoted, withheld. A number that is correct and materially meaningless is
> still a lie told to whoever reads it next. Below that threshold the shared portion is the ~90
> token program prefix, which is structural and harmless.
>
> **Measure so it does not arise:** start from a **proven-cold card** — unload the model before
> taking the baseline, which drops the KV cache with it — then warm up on a chunk you will *not*
> time, send distinct prompts, and where the engine allows it (`"cache_prompt": false` on
> llama-server) turn reuse off for the measurement.
>
> **When the cache is invisible.** Ollama exposes **no** cache-hit field at all, so the 20 % rule
> above cannot be evaluated for it — the guard is blind precisely where you cannot see the danger.
> Two defences, and you need both. *Structural:* unload first, so the cache is empty by
> construction rather than by hope. *Empirical:* the warmup — which follows a proven-cold card, so
> its prefill is real — becomes the run's **measured reference for this hardware**, and any later
> rate more than **3×** it is withheld. A measured reference is preferred to a hardcoded ceiling,
> which would rot the first time the card changes.
>
> `Observed, S81`, the third instance in one session: with a previous run's engine still resident,
> Ollama reported prefill at **61,093 / 63,619 / 65,393 tok/s** on a card whose honest figure is
> ~4,000–6,000 — and the same run printed a VRAM "baseline" of **7,323 MiB** taken while a model
> was loaded, which would have made its own unload check pass trivially. Neither raised an error.
>
> `Observed, S81` — the harness written to obey this document walked into this trap **twice on its
> first two runs**: it warmed up on a chunk it then measured (prefill reported **37,729 tok/s**
> against **4,801** for the next chunk), and its second llama.cpp arm re-sent the first arm's exact
> prompts, receiving 524 and 1,166 tokens free. Both readings were confident, both were nonsense,
> and neither raised an error. This paragraph exists because writing the warning down was not
> sufficient to avoid the thing warned about.

### The independent second clock

Both tables above are the **server's own** account of itself. A rate derived from them shares every
assumption the server makes, so two such rates are one check (SYM-001). The harness therefore also
records **client-side wall time** per request — a differently-shaped measurement that includes
transport and cannot be wrong in the same way. Server time should be slightly *less* than wall
time. If it is ever *greater*, the mapping is wrong, and the discrepancy is the alarm.

---

## 5. Conditions that must accompany any rate

A number without these is not re-derivable, and by rule 6 of docs/21 cannot be promoted past
`Historical`:

- **model** — file or tag, and ideally its hash
- **engine build** — `system_fingerprint` / version
- **hardware** — which card
- **context length** (`-c` / `num_ctx`) and whether flash attention is on
- **warm or cold**, and for a prefill rate, **how the cache was proven empty**
- **concurrency** — 1 unless stated
- **n** — how many requests the figure summarises, and how many were excluded (stalls, cache hits)
- **the command that reproduces it**

---

## 6. House words → standard words

Our vocabulary is allowed, but it must be translatable on sight. This table is the contract.

| House word | What it is in standard terms |
|---|---|
| **the card** | the GPU (one RTX 3080, 10 GiB) |
| **chunk** | one request's input unit — ~4,000 characters of book markdown |
| **arm** | an experimental condition; one configuration under test |
| **the gate** | the acceptance criterion a candidate must pass to be adopted |
| **the fence** | the output-validity check — image-placeholder multiset equality |
| **residency** | keeping weights loaded between requests (`keep_alive`) |
| **the link fence** | the rule that no LLM may alter asset embeds; enforced by the fence |
| **wall clock** | end-to-end latency, client-side |
| **the analyst** | the LLM rewrite pass over converted markdown |

---

## 7. A worked example

**Not admissible:**

> llama.cpp is 27 % faster.

Which tokens? Which phase? Warm? How many requests? Which build? Nothing here can be checked, and
nothing can be re-derived once anything changes.

**Admissible** — and this is the real S81 measurement, not an invented illustration:

> **Decode throughput, warm, concurrency 1, n=8, cold-started card:** llama.cpp
> `b10448-ad1de39e0` + `enable_thinking:false` **97.7 tok/s** (p50 98.9, min 92.2, max 100.3) vs
> Ollama 0.32.13 **102.6 tok/s** (p50 102.3, min 101.0, max 104.9) — **0.95×**.
> **Prefill throughput**, same conditions: 3,766.3 tok/s (p50 3,843.6) vs 4,650.7 (p50 4,580.1) —
> **0.81×**. qwen3:8b, RTX 3080, `-c 8192`, flash attention on, llama.cpp cache hits 0, Ollama
> cache state `UNREAD`, llama.cpp cold load 16.3 s excluded. 8 of 266 chunks — `Inferred` about
> the book. Reproduce: `python windows-converter/backend_parity.py -n 8`.

The second is longer. It is also the only one of the two worth writing down, because it is the
only one still checkable in six months by someone who was not there.

**And note what it says.** S79 recorded `+27 %` in llama.cpp's favour. Measured this way,
llama.cpp is **slower on both phases** — 0.95× decode, 0.81× prefill. The grammar did not make
that result; it made it *visible*, and it is the reason the rules exist.

### 7.1 A trap the vocabulary itself exposes

`Observed, S81`: **Ollama 0.32.13 runs `llama-server` as its own inference engine** —
`AppData\Local\Programs\Ollama\lib\ollama\llama-server.exe`, spawned by `ollama serve`. So a
comparison labelled "Ollama vs llama.cpp" is not engine versus engine. **It is the same engine
under two sets of flags**, and the differences are in the flags:

| | Ollama's own invocation | ours |
|---|---|---|
| batch / ubatch | `-b 1024 -ub 1024` | defaults (`-b 2048 -ub 512`) |
| template | `--no-jinja --chat-template chatml` | `--jinja` (the embedded template) |
| flash attention | `auto` | `on` |
| context | `-c 8192 --context-shift --keep 4` | `-c 8192` |

A smaller micro-batch processes the prompt in more passes, which is the leading candidate for the
0.81× prefill gap — and it is a *hypothesis with an experiment attached*, not a conclusion. State
the flags whenever the engines are named, or a configuration difference will be reported as an
engine difference. Rule: **name the invocation, not just the product.**

---

## 8. Where this is enforced

- **`windows-converter/backend_parity.py`** prints in this vocabulary and refuses to print a rate
  whose duration it did not observe. If the harness and this document ever disagree, **the harness
  is wrong** — a document may describe an instrument, but an instrument may not invent a word the
  document does not define.
- **`docs/22-engineering-manual.html` §18** carries it for the operator.
- **docs/21** supplies the epistemic tag; this file supplies the units. A number needs both: *what
  kind of claim it is*, and *what it counts*.

---

## 9. What this cannot do

It cannot make a measurement correct — only legible and checkable. A number can satisfy every rule
here and still be measured on the wrong workload, which is the failure this project has made most
often. Legibility is the floor, not the proof.
