"""Slice 2 — the link-fenced product analyst (docs/12).

Reformat converted markdown for readability with a local LLM, WITHOUT ever letting it
touch the packaging: every asset embed is swapped for an opaque token before the model
sees the text and re-injected verbatim after. If any chunk comes back with its token
multiset altered, that chunk is rejected and ships un-analyzed — the analyst can only
improve prose, never lose an asset (the qwen3:8b URL-invention hazard, docs/11 Phase 2).

GPU discipline: called only after Marker has exited (the Phase 2 serialization);
keep_alive=0 on every request so VRAM returns to baseline the moment we finish.
"""

import json
import os
import re
import subprocess
import time

MODEL = "qwen3:8b"
OLLAMA_URL = "http://localhost:11434/api/generate"
GEMINI_MODEL = "gemini-flash-latest"  # stable alias, resolves to current Flash
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
CHUNK_TARGET = 4000  # chars; well inside an 8k context with prompt + thinking room
NUM_CTX = 8192

# Measured end-to-end throughput (chars of input markdown per second, all-in:
# chunking + model load/reload + generation + fence checks). Sources: local =
# agent book 28 441 chars / 206.5 s (S15); gemini = measured in the S16 live test.
THROUGHPUT_CHARS_PER_S = {"local": 138.0, "gemini": 186.7}

# Both the assembled form (![[assets/x]]) and any residual inline form.
_EMBED = re.compile(r"!\[\[[^\]]+\]\]|!\[[^\]]*\]\([^)]*\)")
_TOKEN = re.compile(r"⟦IMG-(\d+)⟧")  # ⟦IMG-n⟧

PROMPT = (
    "You are a formatting editor. Improve this converted-book markdown chunk for "
    "readability in Obsidian: fix mid-word hyphenation splits (e.g. 'unexpect edly' -> "
    "'unexpectedly'), normalize heading levels, keep paragraphs intact. Do NOT summarize, "
    "reword, add, or remove content. Placeholders like ⟦IMG-3⟧ mark images: keep every "
    "one exactly as-is, in place. Return ONLY the corrected markdown, no preamble.\n\n"
)


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


def _generate_gemini(prompt: str) -> str:
    """One fenced chunk through Gemini Flash, paced under the free-tier RPM cap.
    The API key is read from the user environment and passed via header inside the
    child process's argv — it is never logged, printed, or embedded in code.
    Cloud routing: chunk text leaves the machine."""
    global _gemini_last_call
    key = os.environ.get("GEMINI_API_KEY") or ""
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set in environment")
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2},
    })
    last_err = "unknown"
    for attempt in range(3):
        wait = _GEMINI_MIN_INTERVAL_S - (time.monotonic() - _gemini_last_call)
        if wait > 0:
            time.sleep(wait)
        _gemini_last_call = time.monotonic()
        proc = subprocess.run(
            ["curl", "-s", "-X", "POST", GEMINI_URL,
             "-H", "Content-Type: application/json",
             "-H", f"x-goog-api-key: {key}",
             "--data-binary", "@-"],
            input=body.encode("utf-8"), capture_output=True, timeout=300,
        )
        if proc.returncode != 0:
            last_err = f"curl exited {proc.returncode}"
            time.sleep(15 * (attempt + 1))
            continue
        reply = json.loads(proc.stdout.decode("utf-8"))
        if "error" in reply:
            err = reply["error"]
            last_err = f"gemini {err.get('code', '?')}: {err.get('message', 'unknown')[:150]}"
            if err.get("code") in (429, 500, 503):
                time.sleep(20 * (attempt + 1))  # backoff and retry rate/server errors
                continue
            raise RuntimeError(last_err)
        parts = reply["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts).strip()
        # Flash sometimes wraps output in a markdown code fence despite instructions.
        if text.startswith("```"):
            text = re.sub(r"^```[a-z]*\n|\n```$", "", text)
        return text
    raise RuntimeError(f"gemini failed after 3 attempts: {last_err}")


def _generate(prompt: str) -> str:
    body = json.dumps({
        "model": MODEL, "stream": False, "keep_alive": 0, "prompt": prompt,
        "options": {"num_ctx": NUM_CTX},
        "think": False,
    })
    # curl with a UTF-8 body file-free: pass via stdin (PS quoting hazards, docs/11 Phase 2,
    # do not apply here — this runs inside Python with bytes end to end).
    proc = subprocess.run(
        ["curl", "-s", "-X", "POST", OLLAMA_URL,
         "-H", "Content-Type: application/json", "--data-binary", "@-"],
        input=body.encode("utf-8"), capture_output=True, timeout=900,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"curl exited {proc.returncode}")
    reply = json.loads(proc.stdout.decode("utf-8"))
    if reply.get("error"):
        raise RuntimeError(f"ollama: {reply['error']}")
    return reply["response"].strip()


def _tokens_of(text: str) -> list[str]:
    return sorted(_TOKEN.findall(text))


def process(markdown: str, backend: str = "local") -> tuple[str, dict]:
    """Returns (markdown_out, analyst_meta). On any per-chunk fence violation or error the
    original chunk is kept; meta records pass/reject counts for the frontmatter.

    backend: "local" (qwen3:8b via Ollama, air-gapped) or "gemini" (Gemini Flash via
    API, cloud routing — chunk text leaves the machine; the user chooses per document).
    """
    generate = {"local": _generate, "gemini": _generate_gemini}[backend]
    fenced, embeds = fence(markdown)
    chunks = _chunks(fenced)
    out, passed, rejected, failed = [], 0, 0, 0
    t0 = time.perf_counter()
    for chunk in chunks:
        try:
            candidate = generate(PROMPT + chunk)
        except Exception:
            out.append(chunk)  # API/backend error -> ship the un-analyzed original
            failed += 1
            continue
        if _tokens_of(candidate) == _tokens_of(chunk):
            out.append(candidate)
            passed += 1
        else:
            out.append(chunk)  # fence violated -> ship the un-analyzed original
            rejected += 1
    meta = {
        "model": GEMINI_MODEL if backend == "gemini" else MODEL,
        "backend": backend,
        "chunks_passed": passed,
        "chunks_rejected": rejected,  # fence violations only
        "chunks_failed": failed,  # backend/API errors after retries
        "duration_s": round(time.perf_counter() - t0, 1),
    }
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


def preflight(markdown_chars: int) -> dict:
    """The JSON the Tauri pre-flight card renders before the user picks a route.
    ETAs come from measured all-in throughput, not theoretical tok/s; the gemini ETA
    includes the RPM pacing floor, which dominates on large documents."""
    busy, vram_mib = gpu_busy()
    n_chunks = max(1, -(-markdown_chars // CHUNK_TARGET))  # ceil
    local_rate = THROUGHPUT_CHARS_PER_S["local"]
    gemini_rate = THROUGHPUT_CHARS_PER_S["gemini"]
    over_window = n_chunks > FREE_TIER_WINDOW_CHUNKS
    eta_gemini = round(n_chunks * _GEMINI_MIN_INTERVAL_S + markdown_chars / gemini_rate)
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
                "eta_s": round(markdown_chars / local_rate),
                "note": "GPU busy — will contend with whatever is using it" if busy else None,
            },
            "gemini": {
                "model": GEMINI_MODEL,
                "privacy": "cloud routing — text leaves this machine",
                "eta_s": eta_gemini,
                "cost": "API free tier (NOT covered by AI Plus — verified 2026-07-19)",
                "warning": (
                    f"{n_chunks} chunks exceeds the ~{FREE_TIER_WINDOW_CHUNKS}-request "
                    "free-tier window — throttling likely, local recommended"
                ) if over_window else None,
            },
        },
    }
