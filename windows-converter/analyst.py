"""Slice 2 — the link-fenced product analyst (docs/12).

Reformat converted markdown for readability with a local LLM, WITHOUT ever letting it
touch the packaging: every asset embed is swapped for an opaque token before the model
sees the text and re-injected verbatim after. If any chunk comes back with its token
multiset altered, that chunk is rejected and ships un-analyzed — the analyst can only
improve prose, never lose an asset (the qwen3:8b URL-invention hazard, docs/11 Phase 2).

GPU discipline: called only after Marker has exited (the Phase 2 serialization);
keep_alive=0 on every request so VRAM returns to baseline the moment we finish.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import fp_paths
import text_norm as tn

MODEL = "qwen3:8b"
OLLAMA_URL = "http://localhost:11434/api/generate"
# S79 — RESIDENCY. Measured on the S76 Beer with this module's own program and chunker:
#
#   keep_alive 0   mean 21.47 s/chunk = load  9.62 (44.8%) + prompt-eval 0.49 + gen 11.11
#   keep_alive 5m  mean 11.75 s/chunk = load  0.21 ( 1.8%) + prompt-eval 0.19 + gen 11.04
#   generation rate 75.7 tok/s cold vs 76.0 warm — IDENTICAL
#
# Every chunk was unloading a model and reloading it for the next one. Steady-state that is
# ~4.7 s per chunk (the first load off disk costs ~19.5 s), so 29-46% of the analyst's wall
# clock bought nothing at all. docs/19 §9 estimated this at "15-25%" — the estimate was low and
# is retired here rather than left to rot.
#
# The unload was a real VRAM courtesy to Marker on a 10 GB card, and it is still owed. What
# changes is WHEN it is paid: the model is held for the phase and released by an explicit act in
# process()'s finally, never by an elapsed timer. A timer is a promise no other stage can check,
# and it would leave ~5 GB resident exactly when the next book's convert wants the card. Release
# is an append, not an expiry — the permanence rule's shape, one stage over.
#
# The hold must simply outlast any gap BETWEEN chunks; it is not the thing that frees the card.
KEEP_ALIVE_HOLD = "30m"
GEMINI_MODEL = "gemini-flash-latest"  # stable alias, resolves to current Flash
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
CHUNK_TARGET = 4000  # chars; well inside an 8k context with prompt + thinking room
NUM_CTX = 8192
# J32-B (docs/54-repair-road, lever-waiver: threshold 0.50, action REJECT, signed Rab
# 2026-09-05). The fence (below) only proves the IMAGE TOKENS survived a chunk's rewrite; it
# sees a DELETED paragraph (the held University 4e run's chunk 23/78 lost 361/308 words) via
# this guard. This IS a per-chunk containment test (§5 R6, docs/15): a candidate that repeats
# or pads its input keeps every one of the input's own windows and scores ~1.0 regardless of
# length, so an INFLATED one is NOT caught here BY CONSTRUCTION -- J34 (OPEN-TASKS, PROPOSED,
# unsigned) is the output/input word-ratio guard that failure mode still needs. (Chunk 296,
# 673 words in / 5,164 out, is the observed real-world instance -- Observed 2026-09-05, replaying
# the 08-30 journal through this shipped function: 0.159, below THIS threshold, because its
# hallucinated output happens not to literally contain the input's windows either, not because
# this guard measures inflation; a duplicated or padded copy of the same input would still score
# ~1.0.) This is the accept-time guard on the deletion failure mode: the fraction of the INPUT
# chunk's own 12-word windows (text_norm.chunk_survival, the same normalisation ladder as J32-A)
# that still turn up, space-free, in the candidate. Below threshold -> reject, ship the original
# chunk.
ANALYST_CHUNK_SURVIVAL_MIN = 0.50
# Stage C (docs/18 §4C): per-chunk liveness, the S42 progress-file pattern — overwritten every
# chunk (zero flight-recorder growth); the file's mtime is the heartbeat the widget ages.
ANALYST_PROGRESS = fp_paths.root("analyst_progress")

# Measured end-to-end throughput (chars of input markdown per second, all-in:
# chunking + model load/reload + generation + fence checks). Sources: local =
# agent book 28 441 chars / 206.5 s (S15); gemini = measured in the S16 live test.
THROUGHPUT_CHARS_PER_S = {"local": 138.0, "gemini": 186.7}

# Both the assembled form (![[assets/x]]) and any residual inline form.
_EMBED = re.compile(r"!\[\[[^\]]+\]\]|!\[[^\]]*\]\([^)]*\)")
_TOKEN = re.compile(r"⟦IMG-(\d+)⟧")  # ⟦IMG-n⟧

# Programs (docs/13 "program slot"): the analyst's behavior IS its prompt text, one file
# per job in prompts/. Editing or adding a file re-tasks the same fenced model — tuning
# without training, versioned in git. Every program runs inside the same link-fence.
PROMPTS_DIR = Path(__file__).parent / "prompts"
DEFAULT_PROGRAM = "readability"


def load_program(program: str) -> str:
    path = PROMPTS_DIR / f"{program}.txt"
    return path.read_text(encoding="utf-8").strip() + "\n\n"


def fence(markdown: str) -> tuple[str, list[str]]:
    embeds: list[str] = []

    def _swap(match: re.Match) -> str:
        embeds.append(match.group(0))
        return f"⟦IMG-{len(embeds) - 1}⟧"

    return _EMBED.sub(_swap, markdown), embeds


def unfence(text: str, embeds: list[str]) -> str:
    return _TOKEN.sub(lambda m: embeds[int(m.group(1))], text)


def _chunks(text: str) -> list[str]:
    """Split on blank lines into ~CHUNK_TARGET-char pieces; never inside a paragraph."""
    out, cur, size = [], [], 0
    for para in text.split("\n\n"):
        if size + len(para) > CHUNK_TARGET and cur:
            out.append("\n\n".join(cur))
            cur, size = [], 0
        cur.append(para)
        size += len(para) + 2
    if cur:
        out.append("\n\n".join(cur))
    return out


# Free-tier Flash is 5 requests/min (verified on the user's quota dashboard,
# 2026-07-19): a 47-chunk book fired unpaced got 41 rate-limit failures in 57 s.
# 13 s spacing ≈ 4.6 RPM keeps a safety margin; 429s additionally retry with backoff.
_GEMINI_MIN_INTERVAL_S = 13.0
_gemini_last_call = 0.0
# NUM-6: the newest backend call's token counters (ollama prompt_eval/eval_count, Gemini
# usageMetadata) — read by process() right after each generate() so accepted-output tokens
# can be told apart from rejected ones. Single-threaded by the analyst's own design.
_last_call: dict = {}


def _generate_gemini(prompt: str) -> str:
    """One fenced chunk through Gemini Flash, paced under the free-tier RPM cap.
    The API key is read from the user environment and sent as a request header from
    THIS process — it is never on any argv (the curl form put it there, visible to any
    process lister: F-13/CWE-214, repaired S93), never logged, never embedded in code.
    Cloud routing: chunk text leaves the machine."""
    global _gemini_last_call
    key = os.environ.get("GEMINI_API_KEY") or ""
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set in environment")
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2},
    }).encode("utf-8")
    last_err = "unknown"
    for attempt in range(3):
        wait = _GEMINI_MIN_INTERVAL_S - (time.monotonic() - _gemini_last_call)
        if wait > 0:
            time.sleep(wait)
        _gemini_last_call = time.monotonic()
        # stdlib TLS proven against this exact endpoint by a keyless probe before the swap
        # shipped (docs/37 §4 T5b: expect a 4xx JSON — observed HTTP 403 PERMISSION_DENIED).
        req = urllib.request.Request(GEMINI_URL, data=body, headers={
            "Content-Type": "application/json", "x-goog-api-key": key})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                reply = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            # Gemini's errors arrive as HTTP statuses carrying the same JSON body curl used
            # to hand us on stdout — read it and keep the retry semantics exactly.
            try:
                err = json.loads(e.read().decode("utf-8", errors="replace")).get("error", {})
            except ValueError:
                err = {}
            code = err.get("code", e.code)
            last_err = f"gemini {code}: {str(err.get('message', 'unknown'))[:150]}"
            if code in (429, 500, 503):
                time.sleep(20 * (attempt + 1))  # backoff and retry rate/server errors
                continue
            raise RuntimeError(last_err) from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            # Transport-level failure — the old "curl exited N" path, same backoff.
            last_err = f"transport: {str(getattr(e, 'reason', e))[:150]}"
            time.sleep(15 * (attempt + 1))
            continue
        if "error" in reply:  # defensive: a 200 carrying an error block
            err = reply["error"]
            last_err = f"gemini {err.get('code', '?')}: {err.get('message', 'unknown')[:150]}"
            if err.get("code") in (429, 500, 503):
                time.sleep(20 * (attempt + 1))
                continue
            raise RuntimeError(last_err)
        parts = reply["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts).strip()
        # NUM-6: Gemini's usage metadata, when present; absent stays None — never invented
        usage = reply.get("usageMetadata") or {}
        _last_call.clear()
        _last_call.update({
            "prompt_tokens": usage.get("promptTokenCount"),
            "output_tokens": usage.get("candidatesTokenCount"),
        })
        # Flash sometimes wraps output in a markdown code fence despite instructions.
        if text.startswith("```"):
            text = re.sub(r"^```[a-z]*\n|\n```$", "", text)
        return text
    raise RuntimeError(f"gemini failed after 3 attempts: {last_err}")


def _generate(prompt: str) -> str:
    body = json.dumps({
        "model": MODEL, "stream": False, "keep_alive": KEEP_ALIVE_HOLD, "prompt": prompt,
        "options": {"num_ctx": NUM_CTX},
        "think": False,
    }).encode("utf-8")
    # urllib with bytes end to end (room_chat's ask() idiom; the PS quoting hazards of
    # docs/11 Phase 2 never applied in-process). Localhost — nothing leaves the machine.
    # A transport error raises to the caller, which ships the un-analyzed original —
    # exactly the curl-exited-nonzero path this replaces.
    req = urllib.request.Request(OLLAMA_URL, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            reply = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode("utf-8", errors="replace")).get("error", "")
        except ValueError:
            msg = ""
        raise RuntimeError(f"ollama: {msg or f'HTTP {e.code}'}") from None
    if reply.get("error"):
        raise RuntimeError(f"ollama: {reply['error']}")
    # NUM-6 (signed 2026-08-31, census N026): the backend's own token counters stop being
    # discarded — process() folds them into the run's meta and the goodput rate.
    _last_call.clear()
    _last_call.update({
        "prompt_tokens": reply.get("prompt_eval_count"),
        "output_tokens": reply.get("eval_count"),
    })
    return reply["response"].strip()


def unload() -> None:
    """Release the model from VRAM now — the explicit half of KEEP_ALIVE_HOLD.

    Best-effort by construction. The fail-safe rule (S42) is that progress/estimate/provenance
    bookkeeping may never change a conversion's outcome, and this runs in a `finally` after the
    book is already assembled. A failed unload costs VRAM until Ollama's own idle timer catches
    it; a raised exception here would cost the analysis, which is the worse trade.
    """
    try:
        body = json.dumps({"model": MODEL, "keep_alive": 0}).encode("utf-8")
        req = urllib.request.Request(OLLAMA_URL, data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60):
            pass
    except Exception:  # noqa: BLE001 — see docstring; this may never propagate
        pass


def _tokens_of(text: str) -> list[str]:
    return sorted(_TOKEN.findall(text))


# ---------- chunk-level resume (S61) ----------
#
# Built the morning a power cut killed Damodaran's analyst pass at chunk 936 of 969 — nine
# minutes from done, ~4 hours gone — because this module held every chunk in memory and wrote
# the markdown only at the end. Marker got slice resume in Stage D; this is the same discipline
# one stage over: each finished chunk is journalled to disk the moment it exists, so an outage
# costs one chunk (~16 s) instead of an afternoon.
ANALYST_WORK = fp_paths.root("analyst_work")


def _resume_key(fenced: str, backend: str, program: str) -> str:
    """Binds EVERYTHING that changes the output: the fenced source text, the backend, the prompt
    program, and the chunk size. Anything different produces a different key, so a stale journal
    can never be silently reused against text it was not written for."""
    h = hashlib.sha256()
    h.update(fenced.encode("utf-8"))
    h.update(f"|{backend}|{program}|{CHUNK_TARGET}".encode("utf-8"))
    return h.hexdigest()[:16]


def _chunk_hash(chunk: str) -> str:
    return hashlib.sha256(chunk.encode("utf-8")).hexdigest()[:16]


def _load_journal(path: Path, chunks: list[str]) -> dict[int, dict]:
    """Completed chunks from a previous run, keyed by 1-based index.

    Every record is re-validated against the chunk it claims to be (input hash), so a change in
    chunking can never splice the wrong text into a book. A torn final line — the power cut
    landing mid-write — simply fails to parse and that chunk is redone: the same append-only
    discipline as events.jsonl, where losing the tail is always the safe direction."""
    done: dict[int, dict] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return done
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
            i = int(rec["i"])
            if 1 <= i <= len(chunks) and rec.get("hash") == _chunk_hash(chunks[i - 1]):
                done[i] = rec
        except (ValueError, KeyError, TypeError):
            continue  # torn or malformed -> redo that chunk
    return done


def _append_journal(handle, i: int, chunk: str, status: str, text: str,
                    reason: str | None = None, survival: float | None = None) -> None:
    """One durable line per finished chunk. fsync because the whole point is surviving a power
    cut — a line sitting in the OS write cache would be exactly as lost as no line at all.

    `reason` (J32-B/SYM-074, added 2026-09-05): "fence" | "survival" | "think_leak" for a
    rejected chunk, absent for a passed one — the 08-30 journal shape had no such key at all,
    so it is only written when present, never as a null placeholder. `survival` rides beside
    it when it was computed (rejected-for-survival AND passed chunks both carry it; a fence
    or think-leak rejection never reaches the survival check, so it stays absent there)."""
    rec = {"i": i, "hash": _chunk_hash(chunk), "status": status, "text": text}
    if reason is not None:
        rec["reason"] = reason
    if survival is not None:
        rec["survival"] = survival
    try:
        handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    except (OSError, ValueError):
        pass  # journalling must never cost the analysis itself


def process(markdown: str, backend: str = "local",
            program: str = DEFAULT_PROGRAM) -> tuple[str, dict]:
    """Returns (markdown_out, analyst_meta). On any per-chunk fence violation or error the
    original chunk is kept; meta records pass/reject counts for the frontmatter.

    backend: "local" (qwen3:8b via Ollama, air-gapped) or "gemini" (Gemini Flash via
    API, cloud routing — chunk text leaves the machine; the user chooses per document).
    program: prompt file name (sans .txt) in prompts/ — the analyst's job description.
    """
    prompt = load_program(program)
    generate = {"local": _generate, "gemini": _generate_gemini}[backend]
    fenced, embeds = fence(markdown)
    chunks = _chunks(fenced)
    out, passed, rejected, failed = [], 0, 0, 0
    # J32-B/SYM-074 (signed Rab 2026-09-05): chunks_rejected's THREE ways of happening, named.
    rejections = {"fence": 0, "survival": 0, "think_leak": 0}
    t0 = time.perf_counter()

    # S61: pick up whatever a previous run finished before it died.
    work_dir = ANALYST_WORK / _resume_key(fenced, backend, program)
    journal_path = work_dir / "chunks.jsonl"
    done = _load_journal(journal_path, chunks)
    resumed = len(done)
    generated = 0  # chunks this run actually paid the GPU for — the honest rate denominator
    # NUM-6: backend token accounting (None-safe — a backend that reports no counters
    # yields honest None in the meta, never invented zeros)
    tokens_prompt = tokens_output = tokens_accepted = counted_calls = 0
    prompt_counted_calls = 0
    if resumed:
        print(f"ANALYST resuming: {resumed}/{len(chunks)} chunks already done "
              f"(journal {journal_path.name})", flush=True)

    def _progress(pos: int) -> None:
        # Best-effort per-chunk heartbeat — a write failure must never affect analysis.
        # The rate is measured over chunks GENERATED this run, never resumed ones: after a
        # resume, dividing by position would report a rate the GPU never achieved and an ETA
        # that quietly flatters itself (the S60 conversion-ledger lesson, one stage over).
        try:
            elapsed = time.perf_counter() - t0
            rate = round(elapsed / generated, 1) if generated else None
            ANALYST_PROGRESS.write_text(json.dumps({
                "n": pos, "total": len(chunks), "s_per_chunk": rate,
                "eta_s": int(rate * (len(chunks) - pos)) if rate else None,
                "resumed": resumed or None,
            }), encoding="utf-8")
        except OSError:
            pass

    _progress(resumed)
    handle = None
    try:
        try:
            work_dir.mkdir(parents=True, exist_ok=True)
            handle = open(journal_path, "a", encoding="utf-8")
        except OSError:
            handle = None  # unjournalled is worse, but never a reason to refuse the work
        for i, chunk in enumerate(chunks, 1):
            if i in done:
                rec = done[i]
                out.append(rec.get("text", chunk))
                status = rec.get("status")
                passed += status == "passed"
                rejected += status == "rejected"
                failed += status == "failed"
                if status == "rejected":
                    # A journal from before J32-B/SYM-074 never named a reason because "fence"
                    # was the ONLY way a chunk could be rejected when it was written — an old,
                    # reason-less record is attributed to "fence" rather than dropped from the
                    # breakdown (the breakdown's total must still equal chunks_rejected).
                    reason = rec.get("reason", "fence")
                    if reason in rejections:
                        rejections[reason] += 1
                continue
            try:
                candidate = generate(prompt + chunk)
            except Exception:
                out.append(chunk)  # API/backend error -> ship the un-analyzed original
                failed += 1
                generated += 1
                # DELIBERATELY NOT JOURNALLED. A failure here means the backend errored — an
                # ollama restart, a VRAM blip, a 5xx — which is exactly the kind of thing the
                # next run would succeed at. Persisting it would bake a transient hiccup into
                # the book forever, and resume would never retry it. Only deterministic outcomes
                # of a completed call (passed / rejected) are worth remembering.
                _progress(i)
                continue
            call_out = _last_call.get("output_tokens")
            call_prompt = _last_call.get("prompt_tokens")
            if call_out is not None:
                tokens_output += call_out
            if call_prompt is not None:
                tokens_prompt += call_prompt
                prompt_counted_calls += 1  # review M5: its OWN denominator — ollama omits
                # prompt_eval_count on fully cached prefills, so the prompt sum is partial
            counted_calls += call_out is not None
            reason, survival = None, None
            # SYM-074 (signed Rab 2026-09-05): qwen3:8b (a thinking model, asked "think":
            # false) leaked a bare `</think>` into shipped text twice (held University 4e
            # lines 8779 and 13744). Checked BEFORE the fence, on both backends (harmless on
            # Gemini): the tag is never stripped-and-kept — docs/12 says the analyst can only
            # be REJECTED, never edited, so the whole chunk is suspect, not just the tag.
            if "<think>" in candidate or "</think>" in candidate:
                out.append(chunk)
                rejected += 1
                rejections["think_leak"] += 1
                status, text, reason = "rejected", chunk, "think_leak"
            elif _tokens_of(candidate) == _tokens_of(chunk):
                # The fence passed: the asset tokens survived. J32-B (signed Rab 2026-09-05,
                # threshold 0.50, action reject) checks the OTHER failure mode the fence
                # cannot see — a deleted paragraph or a runaway inflation — by measuring how
                # much of the INPUT chunk's own windows still turn up in the candidate.
                survival = tn.chunk_survival(chunk, candidate)
                if survival is not None and survival < ANALYST_CHUNK_SURVIVAL_MIN:
                    out.append(chunk)  # survival guard tripped -> ship the un-analyzed original
                    rejected += 1
                    rejections["survival"] += 1
                    status, text, reason = "rejected", chunk, "survival"
                else:
                    out.append(candidate)
                    passed += 1
                    status, text = "passed", candidate
                    if call_out is not None:
                        tokens_accepted += call_out  # NUM-6: only ACCEPTED output earns goodput
            else:
                out.append(chunk)  # fence violated -> ship the un-analyzed original
                rejected += 1
                rejections["fence"] += 1
                status, text, reason = "rejected", chunk, "fence"
            generated += 1
            if handle:
                _append_journal(handle, i, chunk, status, text, reason=reason, survival=survival)
            _progress(i)
    finally:
        if handle:
            try:
                handle.close()
            except OSError:
                pass
        # The heartbeat never outlives the run — staleness must not be able to lie.
        try:
            ANALYST_PROGRESS.unlink(missing_ok=True)
        except OSError:
            pass
        # S79: hand the card back. The model was held across chunks (KEEP_ALIVE_HOLD); this is
        # the act that ends the hold, and it runs whether the phase finished, failed, or was
        # interrupted — the same reason the heartbeat is cleared here. Local backend only:
        # Gemini holds nothing on this machine.
        if backend == "local":
            unload()
    raw_duration = time.perf_counter() - t0  # unrounded for the rate — a 0.0 display-round
    duration = round(raw_duration, 1)        # must not erase a real (fast) run's goodput
    meta = {
        "model": GEMINI_MODEL if backend == "gemini" else MODEL,
        "backend": backend,
        "program": program,
        "chunks_passed": passed,
        # J32-B/SYM-074 (2026-09-05): ALL rejections now, not fence violations alone — see
        # "rejections" below for the breakdown by reason.
        "chunks_rejected": rejected,
        "chunks_failed": failed,  # backend/API errors after retries
        # J32-B/SYM-074: chunks_rejected's breakdown by reason — sums to chunks_rejected
        # (an old, reason-less resumed record is counted as "fence", the only reason that
        # existed before either ticket; see the resume branch above).
        "rejections": dict(rejections),
        "chunks_resumed": resumed,  # carried from an earlier run's journal
        "chunks_generated": generated,  # NUM-6 (census N006): paid backend calls, now named
        "duration_s": duration,
        # NUM-6 (census N026/N286): the backend's own token counters, aggregated instead of
        # discarded, and the docs/34-required rate with its conditions IN the record. None =
        # the backend reported no counters (honest absence, never zero).
        "tokens_prompt_total": tokens_prompt if prompt_counted_calls else None,
        "tokens_prompt_counted_calls": prompt_counted_calls if prompt_counted_calls else None,
        "tokens_output_total": tokens_output if counted_calls else None,
        "tokens_counted_calls": counted_calls if counted_calls else None,
        "tokens_accepted_output": tokens_accepted if counted_calls else None,
        "goodput_accepted_tok_s": (round(tokens_accepted / raw_duration, 2)
                                   if counted_calls and raw_duration > 0 else None),
        # review M5: every partial-sum names its own denominator, and the conditions name
        # what sits inside the wall (resumed skips, API pacing, the terminal unload) and
        # the this-run scope of the accepted numerator
        "goodput_conditions": ("THIS-run accepted-output tokens / whole-phase wall seconds "
                               "(wall includes resumed-chunk skips, API pacing, and the "
                               "terminal model unload; prompt totals are partial sums over "
                               "tokens_prompt_counted_calls — cached prefills report none)"),
    }
    # The book is assembled and about to be written — the journal has done its job.
    shutil.rmtree(work_dir, ignore_errors=True)
    return unfence("\n\n".join(out), embeds), meta


def gpu_busy(threshold_mib: int = 2000) -> tuple[bool, int]:
    """Is the GPU meaningfully occupied (e.g. a game)? Used by the pre-flight card."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        used = int(out.splitlines()[0])
        return used > threshold_mib, used
    except Exception:
        return False, -1


# The free tier enforces a rolling ~20-request window on flash (429 body, verified
# live 2026-07-19: metric generate_content_free_tier_requests, limit 20). Documents
# above this chunk count will throttle even with pacing — recommend local.
FREE_TIER_WINDOW_CHUNKS = 18

EVENTS_FILE = fp_paths.root("events")
RULES_FILE = fp_paths.root("rules")


def measured_rates(backend: str, max_samples: int = 12) -> list[float]:
    """chars/s of recent completed analyst runs for this backend, newest last —
    the event stream turning into self-calibrating ETAs (docs/13)."""
    rates: list[float] = []
    try:
        for line in EVENTS_FILE.read_text(encoding="utf-8").splitlines():
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if (ev.get("stage"), ev.get("event")) != ("analyst", "done"):
                continue
            if ev.get("backend") != backend:
                continue
            chars, dur = ev.get("chars"), ev.get("duration_s")
            if chars and dur:
                rates.append(chars / dur)
    except OSError:
        pass
    return rates[-max_samples:]


def eta_range(chars: int, backend: str) -> tuple[int, int]:
    """(typical, slow) seconds from measured history; static fallback under 3 samples."""
    rates = sorted(measured_rates(backend))
    if len(rates) < 3:
        rate = THROUGHPUT_CHARS_PER_S[backend]
        return round(chars / rate), round(chars / (rate * 0.6))
    median = rates[len(rates) // 2]
    slow = rates[max(0, len(rates) // 10)]  # ~p10 slowest observed
    return round(chars / median), round(chars / slow)


def load_rules() -> dict:
    try:
        return json.loads(RULES_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def preflight(markdown_chars: int) -> dict:
    """The JSON the Tauri pre-flight card renders before the user picks a route.
    ETAs come from measured all-in throughput, not theoretical tok/s; the gemini ETA
    includes the RPM pacing floor, which dominates on large documents."""
    busy, vram_mib = gpu_busy()
    n_chunks = max(1, -(-markdown_chars // CHUNK_TARGET))  # ceil
    over_window = n_chunks > FREE_TIER_WINDOW_CHUNKS
    local_lo, local_hi = eta_range(markdown_chars, "local")
    gem_lo, gem_hi = eta_range(markdown_chars, "gemini")
    pacing_floor = round(n_chunks * _GEMINI_MIN_INTERVAL_S)
    gem_lo, gem_hi = max(gem_lo, pacing_floor), max(gem_hi, pacing_floor)
    eta_gemini = gem_lo
    if over_window:
        recommendation = "local"
    elif busy:
        recommendation = "gemini"
    else:
        recommendation = None  # genuinely the user's choice
    return {
        "chars": markdown_chars,
        "est_tokens": markdown_chars // 4,
        "est_chunks": n_chunks,
        "gpu_busy": busy,
        "gpu_vram_mib": vram_mib,
        "recommendation": recommendation,
        "backends": {
            "local": {
                "model": MODEL,
                "privacy": "100% air-gapped",
                "eta_s": local_lo,
                "eta_range_s": [local_lo, local_hi],
                "note": "GPU busy — will contend with whatever is using it" if busy else None,
            },
            "gemini": {
                "model": GEMINI_MODEL,
                "privacy": "cloud routing — text leaves this machine",
                "eta_s": eta_gemini,
                "eta_range_s": [gem_lo, gem_hi],
                "cost": "API free tier (NOT covered by AI Plus — verified 2026-07-19)",
                "warning": (
                    f"{n_chunks} chunks exceeds the ~{FREE_TIER_WINDOW_CHUNKS}-request "
                    "free-tier window — throttling likely, local recommended"
                ) if over_window else None,
            },
        },
    }
