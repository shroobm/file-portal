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
import re
import subprocess
import time

MODEL = "qwen3:8b"
OLLAMA_URL = "http://localhost:11434/api/generate"
CHUNK_TARGET = 4000  # chars; well inside an 8k context with prompt + thinking room
NUM_CTX = 8192

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


def process(markdown: str) -> tuple[str, dict]:
    """Returns (markdown_out, analyst_meta). On any per-chunk fence violation or error the
    original chunk is kept; meta records pass/reject counts for the frontmatter."""
    fenced, embeds = fence(markdown)
    chunks = _chunks(fenced)
    out, passed, rejected = [], 0, 0
    t0 = time.perf_counter()
    for chunk in chunks:
        try:
            candidate = _generate(PROMPT + chunk)
        except Exception:
            out.append(chunk)
            rejected += 1
            continue
        if _tokens_of(candidate) == _tokens_of(chunk):
            out.append(candidate)
            passed += 1
        else:
            out.append(chunk)  # fence violated -> ship the un-analyzed original
            rejected += 1
    meta = {
        "model": MODEL,
        "chunks_passed": passed,
        "chunks_rejected": rejected,
        "duration_s": round(time.perf_counter() - t0, 1),
    }
    return unfence("\n\n".join(out), embeds), meta
