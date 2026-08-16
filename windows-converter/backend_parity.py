#!/usr/bin/env python3
"""Backend parity harness — is a candidate backend allowed to replace Ollama for the analyst?

WHY THIS EXISTS. S79 measured llama.cpp against Ollama and recorded the outcome as prose:
"Ollama ~814 per chunk; llama.cpp 1,380-2,048, twice hit the cap." No harness was kept, so at
S80's open those numbers could not be re-derived from anything in the repo — only quoted. A
number that cannot be re-measured cannot be promoted past `Historical` (docs/21 rule 3), which
made an otherwise-finished investigation unbankable. This file is the missing half.

WHAT THE GATE IS. Not speed. The analyst's output is a near-verbatim REWRITE of its input, so a
correct chunk lands close to its own size and stops on its own. Two ways that breaks:

  * the model THINKS out loud, spending its budget on reasoning that is not the deliverable;
  * the output runs to the cap (`finish_reason: length`), truncating the chunk mid-book.

Truncation drops trailing image placeholders, so `analyst._tokens_of` rejects the chunk and the
UN-ANALYZED original ships. The failure is silent and lands in the vault. Hence the gate:
completion tokens comparable to Ollama's on the SAME chunks, `stop` on every one, fence clean.

WHAT S80 MEASURED (Valentine, 5 chunks, qwen3:8b both sides):

    ollama --think:false            2,307 tok   max 633    stop 5/5   fence 5/5
    llama.cpp --jinja               14,893 tok  max 4,526  stop 5/5   fence 5/5   <- 6.46x
    llama.cpp --jinja +no-think     2,300 tok   max 633    stop 5/5   fence 5/5   <- -0.3%

`--jinja` ALONE FAILS THE GATE, and fails it upward: it makes llama.cpp apply qwen3's embedded
chat template, whose default is thinking ON. The analyst has always sent Ollama `"think": False`
(analyst.py). The llama.cpp counterpart is `chat_template_kwargs.enable_thinking = false`, and
with it the two backends land within 2.1% per chunk. `--jinja` is necessary and NOT sufficient.

SAMPLING NEVER PROMOTES. N chunks measured is `Inferred` about the book, never `Observed` about
all of it (docs/21 rule 2). Raise -n before trusting this with a migration.

ONE LAB PROCESS ON THE CARD, EVER (SYM-022). Ollama is unloaded and VRAM proven back to baseline
before llama-server is started. Never run this while a conversion is running.

    python backend_parity.py                     # default: held Valentine, 5 chunks
    python backend_parity.py --book PATH -n 12
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import analyst

LLAMA_EXE = Path(r"C:\Users\Bndit\ml\llama\llama-server.exe")
# The Ollama blob IS the gguf — same bytes, so the comparison cannot drift on weights.
# Verified S80: this sha resolves to exactly one manifest, registry.ollama.ai/library/qwen3/8b.
MODEL_GGUF = Path(r"C:\Users\Bndit\.ollama\models\blobs"
                  r"\sha256-a3de86cd1c132c822487ededd47a324c50491393e6565cd14bafa40d0b8e686f")
DEFAULT_BOOK = Path(r"C:\Users\Bndit\ml\library\held\b6fbdd75f6242f53"
                    r"\Best Practices for Equity Research Analysts - James J Valentine (2011).md")
PORT = 7117  # room-chat owns 7110-7119; the bench owns 7077-7096. Do not borrow either.


def vram_mib() -> int:
    """MiB in use. Raises rather than returning a number nobody watched (SYM-031)."""
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                         capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        raise RuntimeError(f"nvidia-smi exited {out.returncode}: {out.stderr.strip()}")
    return int(out.stdout.strip().splitlines()[0])


def post(url: str, body: dict, timeout: int = 900) -> dict:
    raw = json.dumps(body).encode("utf-8")
    proc = subprocess.run(["curl", "-s", "-X", "POST", url,
                           "-H", "Content-Type: application/json", "--data-binary", "@-"],
                          input=raw, capture_output=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"curl exited {proc.returncode}: {proc.stderr.decode('utf-8')[:200]}")
    return json.loads(proc.stdout.decode("utf-8"))


def _row(rec: dict) -> str:
    return (f"  chunk {rec['chunk']:>4}  in {rec['in_chars']:>5}c/{rec['prompt_tok']:>5}t  "
            f"out {rec['out_chars']:>5}c/{rec['out_tok']:>5}t  stop={rec['stop']:<8} "
            f"fence={'ok' if rec['fence'] else 'VIOLATED'}  think={rec['think_chars']:>6}c  "
            f"{rec['wall_s']}s")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", type=Path, default=DEFAULT_BOOK)
    ap.add_argument("-n", "--chunks", type=int, default=5)
    ap.add_argument("--out", type=Path, default=Path(__file__).with_name("backend_parity.json"))
    args = ap.parse_args()

    base = vram_mib()
    print(f"VRAM baseline: {base} MiB", flush=True)

    fenced, embeds = analyst.fence(args.book.read_text(encoding="utf-8"))
    chunks = analyst._chunks(fenced)
    program = analyst.load_program(analyst.DEFAULT_PROGRAM)
    print(f"book: {args.book.name}\n  {len(embeds)} embeds - {len(chunks)} chunks "
          f"@ target {analyst.CHUNK_TARGET}", flush=True)

    step = max(1, len(chunks) // (args.chunks + 1))
    picked = [(i, chunks[i]) for i in range(step, len(chunks), step)][:args.chunks]
    print("  sampled: " + ", ".join(str(i) for i, _ in picked)
          + f"\n  a sample never promotes a claim about all {len(chunks)} chunks\n", flush=True)

    results: dict[str, list[dict]] = {}

    print("=" * 78 + "\nARM - ollama /api/generate think:false (production today)\n" + "=" * 78,
          flush=True)
    arm = []
    for i, chunk in picked:
        t0 = time.perf_counter()
        r = post(analyst.OLLAMA_URL, {
            "model": analyst.MODEL, "stream": False, "keep_alive": analyst.KEEP_ALIVE_HOLD,
            "prompt": program + chunk, "options": {"num_ctx": analyst.NUM_CTX}, "think": False,
        })
        if r.get("error"):
            raise RuntimeError(f"ollama: {r['error']}")
        text = r["response"].strip()
        rec = {"chunk": i, "in_chars": len(chunk), "prompt_tok": r.get("prompt_eval_count"),
               "out_tok": r.get("eval_count"), "stop": r.get("done_reason"), "out_chars": len(text),
               "fence": analyst._tokens_of(text) == analyst._tokens_of(chunk), "think_chars": 0,
               "wall_s": round(time.perf_counter() - t0, 1)}
        arm.append(rec)
        print(_row(rec), flush=True)
    results["ollama_think_false"] = arm

    # SYM-022: the card carries one lab process. Prove the release, do not assume it.
    print("\n  releasing ollama (keep_alive 0)...", flush=True)
    post(analyst.OLLAMA_URL, {"model": analyst.MODEL, "keep_alive": 0}, timeout=60)
    for _ in range(60):
        time.sleep(2)
        if vram_mib() <= base + 300:
            break
    print(f"  VRAM now {vram_mib()} MiB (baseline {base}) - card is free\n", flush=True)

    errlog = Path(__file__).with_name("backend_parity-llama-stderr.log")
    proc = subprocess.Popen(
        [str(LLAMA_EXE), "-m", str(MODEL_GGUF), "-ngl", "99", "-c", str(analyst.NUM_CTX),
         "--flash-attn", "on", "--jinja", "--host", "127.0.0.1", "--port", str(PORT)],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=open(errlog, "wb"),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        t0, ready = time.perf_counter(), False
        while time.perf_counter() - t0 < 300:
            if proc.poll() is not None:  # EXITED is not "did not come up"
                raise RuntimeError(f"llama-server exited {proc.returncode} loading; see {errlog}")
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2) as h:
                    if json.loads(h.read()).get("status") == "ok":
                        ready = True
                        break
            except Exception:  # noqa: BLE001 - still LOADING
                time.sleep(0.5)
        if not ready:
            raise RuntimeError("llama-server alive but never answered /health (timeout, not crash)")
        print(f"llama-server up in {time.perf_counter() - t0:.1f}s on :{PORT}\n", flush=True)

        for label, extra in (
            ("llamacpp_jinja_default", {}),
            ("llamacpp_jinja_nothink", {"chat_template_kwargs": {"enable_thinking": False}}),
        ):
            print("=" * 78 + f"\nARM - {label}\n" + "=" * 78, flush=True)
            arm = []
            for i, chunk in picked:
                body = {"model": "qwen3", "stream": False,
                        "messages": [{"role": "user", "content": program + chunk}], **extra}
                t1 = time.perf_counter()
                r = post(f"http://127.0.0.1:{PORT}/v1/chat/completions", body)
                if "choices" not in r:
                    raise RuntimeError(f"llama.cpp: {json.dumps(r)[:300]}")
                ch, usage = r["choices"][0], r.get("usage", {})
                text = (ch["message"].get("content") or "").strip()
                rec = {"chunk": i, "in_chars": len(chunk), "prompt_tok": usage.get("prompt_tokens"),
                       "out_tok": usage.get("completion_tokens"), "stop": ch.get("finish_reason"),
                       "out_chars": len(text), "think_chars": len(
                           ch["message"].get("reasoning_content") or ""),
                       "fence": analyst._tokens_of(text) == analyst._tokens_of(chunk),
                       "wall_s": round(time.perf_counter() - t1, 1)}
                arm.append(rec)
                print(_row(rec), flush=True)
            results[label] = arm
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=30)
        except Exception:  # noqa: BLE001
            proc.kill()
        print("\nllama-server terminated.", flush=True)

    print("\n" + "=" * 78 + "\nPARITY (gate = tokens + stop reason + fence, NOT speed)\n" + "=" * 78)
    print(f"{'arm':<26}{'tokens':>9}{'max':>8}{'not-stop':>10}{'fence bad':>11}{'vs ollama':>11}")
    ref = sum(r["out_tok"] for r in results["ollama_think_false"])
    verdict_ok = []
    for label, rows in results.items():
        tot = sum(r["out_tok"] for r in rows)
        bad_stop = sum(1 for r in rows if r["stop"] != "stop")
        bad_fence = sum(1 for r in rows if not r["fence"])
        print(f"{label:<26}{tot:>9}{max(r['out_tok'] for r in rows):>8}{bad_stop:>10}"
              f"{bad_fence:>11}{100.0 * (tot - ref) / ref:>+10.1f}%")
        verdict_ok.append((label, abs(tot - ref) / ref <= 0.10 and not bad_stop and not bad_fence))

    print("\nPASSES THE GATE (within 10% of ollama, all stop, fence clean):")
    for label, good in verdict_ok:
        print(f"  {'PASS' if good else 'FAIL'}  {label}")
    args.out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nraw -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
