"""prototypes/analyst-lab/decoding/decoding_experiment.py -- THE ONE BOUNDED GPU EXPERIMENT (S119 R2).

Question: how much of the analyst's ~3 % window loss is the SAMPLER (temperature) versus the model's
judgement? Same chunks, same program prefix, same ollama endpoint; three request shapes:
  (a) SHIPPED  -- analyst._generate itself (whatever options the shipped code sends; the model's
                  baked Modelfile parameters fill the rest: `ollama show qwen3:8b`)
  (b) GREEDY   -- the same body + options {temperature: 0, seed: 7}
  (c) GREEDY+SYSTEM -- (b) + a stricter `system` line (5 chunks only, budget)
plus (b) repeated on 5 chunks to measure determinism.

MANDATORY PROTOCOL (the brief, verbatim in spirit):
  (i)   before ANY ollama call: C:/Users/Bndit/ml/library/.gpu-lock and chat-hold.json must BOTH be
        absent, else UNREAD and exit without a call;
  (ii)  write chat-hold.json in room_chat's exact schema from THIS process (pid = os.getpid());
        the watcher (watch_and_convert.chat_hold) defers every convert while this pid is alive;
  (iii) finally: delete chat-hold.json and POST keep_alive 0 (unload);
  (iv)  one generation at a time, sequential, never concurrent;
  (v)   abort immediately if .gpu-lock appears;
  (vi)  nvidia-smi memory before / during (once) / after.
CAP: <= 90 generations.

Writes: full texts to $TEMP/r2/gen_results.jsonl (book text stays OUT of the repo); a text-free
summary to ./results.json beside this file. Nothing under the library except the hold file, which
is removed in `finally`.
"""
from __future__ import annotations

import json
import os
import pathlib
import random
import re
import subprocess
import sys
import time
import urllib.request
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ddia_pairs  # noqa: E402  (sets sys.path to windows-converter + FP_PIPELINE quarantine)
import analyst  # noqa: E402
import text_norm as tn  # noqa: E402

LIB = pathlib.Path(r"C:\Users\Bndit\ml\library")
GPU_LOCK = LIB / ".gpu-lock"
HOLD = LIB / "chat-hold.json"
TEMP_OUT = pathlib.Path(os.environ.get("TEMP", r"C:\Temp")) / "r2"
TEMP_OUT.mkdir(parents=True, exist_ok=True)
RESULTS_JSONL = TEMP_OUT / "gen_results.jsonl"
LOG = TEMP_OUT / "experiment.log"
SUMMARY = HERE / "results.json"
CAP = 90
NUM = re.compile(r"\d[\d,.]*\d|\d")

STRICT_SYSTEM = ("You are a copy-typist, not an editor. Reproduce the user's markdown EXACTLY, word for "
                 "word and number for number, with only two permitted changes: join a word broken by a "
                 "mid-word hyphenation split, and make heading levels consistent. Never drop, merge, "
                 "reorder, paraphrase or add a sentence, paragraph, list item, table row or number.")


def log(msg: str) -> None:
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as h:
        h.write(line + "\n")


def nvsmi() -> str:
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader"],
                           capture_output=True, text=True, timeout=20)
        return r.stdout.strip()
    except Exception as e:  # noqa: BLE001
        return f"nvidia-smi failed: {e}"


def ollama_ps() -> str:
    try:
        with urllib.request.urlopen("http://localhost:11434/api/ps", timeout=10) as r:
            return r.read().decode("utf-8")[:300]
    except Exception as e:  # noqa: BLE001
        return f"ps failed: {e}"


def generate_with(prompt: str, options: dict, system: str | None = None) -> tuple[str, dict]:
    """The shipped body shape (analyst._generate) with extra options merged in."""
    body = {"model": analyst.MODEL, "stream": False, "keep_alive": analyst.KEEP_ALIVE_HOLD,
            "prompt": prompt, "options": {"num_ctx": analyst.NUM_CTX, **options}, "think": False}
    if system:
        body["system"] = system
    req = urllib.request.Request(analyst.OLLAMA_URL, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        reply = json.loads(r.read().decode("utf-8"))
    if reply.get("error"):
        raise RuntimeError(reply["error"])
    meta = {k: reply.get(k) for k in ("prompt_eval_count", "eval_count", "eval_duration", "total_duration",
                                      "load_duration", "prompt_eval_duration")}
    return reply["response"].strip(), meta


def unload() -> str:
    try:
        body = json.dumps({"model": analyst.MODEL, "keep_alive": 0}).encode("utf-8")
        req = urllib.request.Request(analyst.OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read().decode("utf-8")[:200]
    except Exception as e:  # noqa: BLE001
        return f"unload failed: {e}"


def score(chunk: str, out: str) -> dict:
    a = Counter(NUM.findall(chunk))
    b = Counter(NUM.findall(out))
    missing = a - b
    extra = b - a
    return {
        "survival": tn.chunk_survival(chunk, out),
        "ratio": tn.word_ratio(chunk, out),
        "fence_ok": analyst._tokens_of(out) == analyst._tokens_of(chunk),
        "think_leak": ("<think>" in out) or ("</think>" in out),
        "numerals_in": sum(a.values()),
        "numerals_missing": sum(missing.values()),
        "numerals_extra": sum(extra.values()),
        "numeral_examples": [(k, v) for k, v in list(missing.items())[:3]],
        "identical_to_input": out == chunk,
        "words_in": len(chunk.split()),
        "words_out": len(out.split()),
    }


def main() -> int:
    log(f"pid {os.getpid()} start; python {sys.executable}")
    # (i) preflight
    if GPU_LOCK.exists() or HOLD.exists():
        log(f"UNREAD: preflight refused -- .gpu-lock exists={GPU_LOCK.exists()} chat-hold exists={HOLD.exists()}")
        return 2
    m, chunks_in, outs, cs = ddia_pairs.pairs()
    prefix = analyst.load_program("readability")
    passed = sorted((r for r in cs.values() if "x" not in r and "s" in r), key=lambda r: r["s"])
    low20 = [r["i"] for r in passed[:20]]
    rej12 = [r["i"] for r in cs.values() if r.get("x") == "survival"]
    rest = [r["i"] for r in passed[20:]]
    rnd = random.Random(7)
    rand8 = sorted(rnd.sample(rest, 8))
    sample = low20 + rej12 + rand8
    det5 = low20[:5]
    plan = [(i, "a") for i in sample]
    plan_b = [(i, "b") for i in sample]
    # interleave a/b per chunk so a lock-abort leaves matched pairs
    order: list[tuple[int, str]] = []
    for pa, pb in zip(plan, plan_b):
        order.extend([pa, pb])
    order += [(i, "b2") for i in det5]
    order += [(i, "c") for i in det5]
    assert len(order) <= CAP, len(order)
    log(f"sample: low20={low20} rej12={rej12} rand8={rand8}; generations planned={len(order)}")
    before = nvsmi()
    log(f"nvidia-smi BEFORE: {before}; ollama ps: {ollama_ps()}")
    # (ii) hold, in room_chat's exact schema
    HOLD.write_text(json.dumps({
        "held_by": "research-R2", "pid": os.getpid(), "port": 0, "model": "qwen3:8b research",
        "since": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "_why": "S119 R2 decoding experiment; a convert must defer until this is gone",
    }, indent=1), encoding="utf-8")
    log(f"hold written: {HOLD} -> {HOLD.read_text(encoding='utf-8')[:160]!r}")
    during = None
    done = 0
    aborted = None
    t_all = time.perf_counter()
    try:
        for n, (i, setting) in enumerate(order, 1):
            if GPU_LOCK.exists():  # (v)
                aborted = f".gpu-lock appeared before generation {n}"
                log("ABORT: " + aborted)
                break
            chunk = chunks_in[i - 1]
            t0 = time.perf_counter()
            if setting == "a":
                out = analyst._generate(prefix + chunk)  # THE SHIPPED REQUEST, verbatim code path
                meta = dict(analyst._last_call)
            elif setting in ("b", "b2"):
                out, meta = generate_with(prefix + chunk, {"temperature": 0, "seed": 7})
            else:
                out, meta = generate_with(prefix + chunk, {"temperature": 0, "seed": 7}, system=STRICT_SYSTEM)
            dt = round(time.perf_counter() - t0, 1)
            sc = score(chunk, out)
            rec = {"n": n, "i": i, "setting": setting, "manifest_s": cs[i].get("s"), "manifest_x": cs[i].get("x"),
                   "secs": dt, "meta": meta, **sc, "output": out}
            with RESULTS_JSONL.open("a", encoding="utf-8") as h:
                h.write(json.dumps(rec, ensure_ascii=False) + "\n")
            done += 1
            log(f"[{n}/{len(order)}] chunk {i} {setting}: s={sc['survival']} r={sc['ratio']} fence={sc['fence_ok']} "
                f"num_missing={sc['numerals_missing']} {dt}s (manifest s={cs[i].get('s')} x={cs[i].get('x')})")
            if during is None:
                during = nvsmi()
                log(f"nvidia-smi DURING: {during}; ollama ps: {ollama_ps()}")
    finally:
        # (iii)
        try:
            HOLD.unlink(missing_ok=True)
        except OSError as e:
            log(f"hold unlink failed: {e}")
        u = unload()
        time.sleep(3)
        after = nvsmi()
        log(f"hold removed (exists={HOLD.exists()}); unload reply {u!r}; nvidia-smi AFTER: {after}; ollama ps: {ollama_ps()}")
        SUMMARY.write_text(json.dumps({
            "generations_done": done, "planned": len(order), "aborted": aborted,
            "wall_s": round(time.perf_counter() - t_all, 1),
            "sample": {"low20": low20, "rej12": rej12, "rand8": rand8, "det5": det5},
            "nvidia_smi": {"before": before, "during": during, "after": after},
            "strict_system": STRICT_SYSTEM,
            "results_jsonl": str(RESULTS_JSONL),
        }, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
