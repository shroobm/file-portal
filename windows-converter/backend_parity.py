#!/usr/bin/env python3
"""Backend parity harness — may a candidate backend replace Ollama for the analyst?

Answers two separate questions, because they fail for different reasons and one does not imply
the other:

  THE TOKEN GATE (S80)  Does the candidate produce output of the same SIZE, stopping on its own,
                        passing the image fence? A backend that rambles or truncates corrupts
                        books regardless of how fast it is.
  THE THROUGHPUT ARM    Given equal output, is it faster — and by how much, on which phase?
      (S81)             Speed is only admissible AFTER the token gate passes; a fast backend that
                        writes the wrong thing is not a faster backend.

VOCABULARY IS FIXED BY docs/34-measurement-language.md. This file is that document's first
consumer and prints in its terms: prefill and decode are reported separately and never blended,
every rate names its numerator and denominator, `n` and a spread accompany every mean, ratios
print both of their sides, and a duration the backend did not report renders UNREAD rather than
0.0. If this harness and docs/34 ever disagree, THIS FILE IS WRONG — a document may describe an
instrument, but an instrument may not invent a word the document does not define.

WHY THE HARNESS EXISTS AT ALL. S79 measured llama.cpp and recorded "+27 % tok/s and 1.72×
batching" as prose. No harness was kept, so at S80's open the figures could not be re-derived,
only quoted, and quoting is what docs/21 rule 3 forbids. An investigation that had actually been
done was unbankable because nobody could say what had been counted.

WHAT S80 MEASURED (Valentine, 5 chunks, qwen3:8b both sides), token gate:

    ollama --think:false            2,307 tok   max   633   stop 5/5   fence 5/5
    llama.cpp --jinja              14,893 tok   max 4,526   stop 5/5   fence 5/5   <- 6.46x
    llama.cpp --jinja +no-think     2,300 tok   max   633   stop 5/5   fence 5/5   <- -0.3%

`--jinja` ALONE FAILS THE GATE, and fails it upward: it makes llama.cpp apply qwen3's embedded
chat template, whose default is thinking ON. analyst.py has always sent Ollama `"think": False`;
the llama.cpp counterpart is `chat_template_kwargs.enable_thinking = false`. `--jinja` is
necessary and NOT sufficient.

WHAT S81 MEASURED (same book, n=8, warm, concurrency 1, cold-started card), throughput:

    ollama 0.32.13              prefill 4,650.7 tok/s   decode 102.6 tok/s   e2e  6.7 s
    llama.cpp +no-think         prefill 3,766.3 tok/s   decode  97.7 tok/s   e2e  7.0 s
                                        = 0.81x                 = 0.95x

S79's "+27 %" DOES NOT REPRODUCE. Measured this way llama.cpp is slower on both phases.

AND THE COMPARISON'S PREMISE IS WRONG. Ollama 0.32.13 runs llama-server as its OWN engine
(AppData\\Local\\Programs\\Ollama\\lib\\ollama\\llama-server.exe, parent `ollama serve`). This is not
engine vs engine - it is ONE ENGINE UNDER TWO SETS OF FLAGS. Ollama invokes it with
`-b 1024 -ub 1024 --no-jinja --chat-template chatml --flash-attn auto --context-shift`; we use the
`-ub 512` default and `--jinja`. The micro-batch gap is the leading candidate for the 0.81x
prefill difference - a hypothesis with an experiment attached, not a conclusion. Whoever picks
this up: vary the flags on one engine before concluding anything about two products.

WHAT S82 FOUND WHEN n WAS RAISED TO 30 - AND WHY THE RATIOS ABOVE ARE NOT ADMISSIBLE.

The gap did not merely persist at n=30, it WIDENED: decode 0.77x (was 0.95x), prefill 0.62x (was
0.81x). A result that strengthens with sample size reads as confirmation. It was an artefact of
ARM ORDER. The arms run in fixed sequence, so the incumbent is always measured on a cool idle
card and the candidates always after 20+ minutes of sustained load. Decode rate regressed on
POSITION vs on OUTPUT LENGTH: ollama (1st) -0.24 / -0.50; llama.cpp default (2nd) -0.78 / -0.33;
nothink (3rd) -0.36 / -0.15. The candidates are dominated by position, and the nothink arm's
outputs are near-constant (mean 678 tokens), so length cannot explain it. Decisive: the SAME
config on the SAME chunks gave 97.7 tok/s in a 7-minute run and 77.7 in a 25-minute one, -20.5 %;
and a short run immediately afterwards measured OLLAMA ITSELF at 71-79 tok/s against its own
100-103 on a cool card. A longer run means more drift, so the artefact scales with n exactly as a
real effect would (SYM-035).

Hence the A-B-A control below: the incumbent is measured FIRST and LAST, the drift is published,
and >5 % drift WITHHOLDS every cross-arm ratio. What survives all of this is the TOKEN GATE - a
comparison of output CONTENT, which is order-independent.

SAMPLING NEVER PROMOTES. N chunks measured is `Inferred` about the book, never `Observed` about
all of it (docs/21 rule 2). Raise -n before trusting this with a migration - but note that at
n=30 raising it exposed the method rather than confirming the result, which is the better outcome
and the reason to keep doing it.

ONE LAB PROCESS ON THE CARD, EVER (SYM-022). Ollama is unloaded and VRAM proven back to baseline
before llama-server starts. Never run this while a conversion is running.

    python backend_parity.py                 # token gate + throughput, 5 chunks
    python backend_parity.py -n 12
    python backend_parity.py --gate-only     # skip throughput (faster, no warmups)
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import analyst
import fp_paths

LLAMA_EXE = Path(r"C:\Users\Bndit\ml\llama\llama-server.exe")
# The Ollama blob IS the gguf - same bytes, so the comparison cannot drift on weights.
# Verified S80: this sha resolves to exactly one manifest, registry.ollama.ai/library/qwen3/8b.
MODEL_GGUF = Path(r"C:\Users\Bndit\.ollama\models\blobs"
                  r"\sha256-a3de86cd1c132c822487ededd47a324c50491393e6565cd14bafa40d0b8e686f")
DEFAULT_BOOK = (fp_paths.root("held") / "b6fbdd75f6242f53"
                / "Best Practices for Equity Research Analysts - James J Valentine (2011).md")
# S83: this was 7117 - INSIDE room-chat's range, directly under this do-not-borrow comment. It
# never bit only because room-chat was down. A do-not-borrow comment that borrows is SYM-032's
# shape in miniature: the words carried no mechanism.
PORT = 7127  # room-chat owns 7110-7119; the bench owns 7077-7096. Do not borrow either.

UNREAD = "UNREAD"          # docs/34 rule 6 - never 0.0 for a duration nobody reported
# A warm chunk of this size takes ~3-25 s. 300 s is a stall, not a slow request. The analyst's
# own ceiling is 900 s because THERE the cost of giving up is a lost page; here it is a lost
# measurement, which is cheaper to retry than to wait out.
REQUEST_TIMEOUT_S = 300
NS_PER_S = 1e9             # ollama reports NANOseconds
MS_PER_S = 1e3             # llama.cpp reports MILLIseconds - a 10^6 difference, see docs/34 §4


# ── the unit boundary ────────────────────────────────────────────────────────────────────────
#
# docs/34 §4's trap: the two backends report the same quantities, in the same shape, in the same
# position, in units that differ by a factor of a MILLION. Both are converted to SECONDS here,
# once, at the edge. No raw duration travels further into this file than these two functions.

def _phases_ollama(r: dict) -> dict:
    """Ollama /api/generate -> phases in SECONDS. None where the field is absent."""
    def s(key: str) -> float | None:
        v = r.get(key)
        return None if v is None else v / NS_PER_S
    return {"prefill_tok": r.get("prompt_eval_count"), "prefill_s": s("prompt_eval_duration"),
            "decode_tok": r.get("eval_count"), "decode_s": s("eval_duration"),
            "load_s": s("load_duration"), "server_total_s": s("total_duration"),
            # Ollama exposes no cache-hit field. The first draft wrote 0 here, which is a GUESS
            # wearing a reading's clothes - the exact move SYM-031 forbids. It is None, and it
            # prints UNREAD, because "we cannot see it" and "there were none" are different facts.
            "cached_tok": None}


def _phases_llamacpp(r: dict) -> dict:
    """llama.cpp /v1/chat/completions -> phases in SECONDS. None where the field is absent."""
    t = r.get("timings") or {}
    usage = r.get("usage") or {}
    def s(key: str) -> float | None:
        v = t.get(key)
        return None if v is None else v / MS_PER_S
    return {"prefill_tok": t.get("prompt_n", usage.get("prompt_tokens")), "prefill_s": s("prompt_ms"),
            "decode_tok": t.get("predicted_n", usage.get("completion_tokens")),
            "decode_s": s("predicted_ms"), "load_s": None,  # load is server startup, timed by us
            "server_total_s": None,
            "cached_tok": t.get("cache_n", (usage.get("prompt_tokens_details") or {}).get(
                "cached_tokens", 0))}


def rate(tokens: int | None, seconds: float | None) -> float | None:
    """Tokens per second, or None. A rate needs a duration somebody actually reported."""
    if tokens is None or seconds is None or seconds <= 0:
        return None
    return tokens / seconds


# How much of a prompt may arrive from the KV cache before its prefill rate stops describing
# prefill. The shared part of every request here is the ~90-token readability program, so a few
# percent is structural and harmless; a fifth is not.
CACHE_CONTAMINATION = 0.20
# A prefill rate this far above ITS OWN ARM'S MEDIAN is not a measurement. (S83: the S82
# draft judged against the single warmup, and the warmup was once the anomaly - S82 10.4.)
PREFILL_IMPLAUSIBLE_X = 3.0
# How far the incumbent may move between its first and last measurement before every cross-arm
# ratio in the run is suspect. S82 measured -20.5 % across a 25-minute run, so this is not a
# theoretical bound.
ORDER_DRIFT_LIMIT = 0.05


def prefill_rate(rec: dict) -> float | None:
    """Prefill throughput, or None when the prefill did not actually happen.

    Rule 6 says a rate needs a duration the backend reported. Its twin, learned the hard way in
    S81: a prefill rate needs a PREFILL. `timings.prompt_n` counts only the tokens genuinely
    processed, so a fully cached prompt reports `prompt_n=1` and yields a confident, internally
    consistent 74.6 tok/s that describes a one-token prefill and nothing anyone cares about. The
    second llama arm re-sent the first arm's exact prompts and got 524 and 1,166 tokens free.
    A number that is arithmetically correct and materially meaningless is still a lie told to
    whoever reads it next, so it is withheld rather than footnoted.
    """
    processed, cached = rec.get("prefill_tok"), rec.get("cached_tok")
    if processed is None:
        return None
    if cached:
        total = processed + cached
        if total and cached / total > CACHE_CONTAMINATION:
            return None
    return rate(processed, rec.get("prefill_s"))


def censor_prefill_outliers(rows: list[dict]) -> list[dict]:
    """Withhold prefill rates far above the arm's own MEDIAN. Returns the withheld records.

    The median because the S82 draft judged against the warmup - one measurement, which is
    exactly what docs/21 rule 3 forbids trusting - and on one run the warmup was itself the
    anomaly (823 tok/s, hot card), so two legitimate prefills were withheld (S82 10.4). A
    median is robust to one bad point. Wholesale contamination is prevented STRUCTURALLY by
    the cold start; this does not try to catch it and cannot.
    """
    vals = sorted(r["prefill_tps"] for r in rows if r.get("prefill_tps"))
    if len(vals) < 3:
        return []      # a median of one or two points is not a reference either
    med = statistics.median(vals)
    out = []
    for r in rows:
        tps = r.get("prefill_tps")
        if tps and tps > PREFILL_IMPLAUSIBLE_X * med:
            r["prefill_tps"] = None
            r["prefill_suspect"] = True
            out.append(r)
    return out


def gate_verdict(tot: int, ref: int, bad_stop: int, ref_stop: int,
                 bad_fence: int, ref_fence: int) -> bool:
    """The token gate. The incumbent sets the bar - a candidate must be no WORSE, not perfect
    (S81 10.5: the first draft demanded zero fence failures and thereby failed the production
    backend against its own numbers)."""
    return abs(tot - ref) / ref <= 0.10 and bad_stop <= ref_stop and bad_fence <= ref_fence


def order_drift_verdict(first_mean: float, last_mean: float) -> tuple[float, bool]:
    """A-B-A (SYM-035): (drift fraction, cross-arm ratios admissible)."""
    drift = (last_mean - first_mean) / first_mean
    return drift, abs(drift) <= ORDER_DRIFT_LIMIT


def fmt_rate(v: float | None) -> str:
    return UNREAD if v is None else f"{v:,.1f}"


def summarise(values: list[float | None], unit: str) -> str:
    """docs/34 rule 3: n and a spread, never a bare mean. p95 only once n is big enough to
    mean anything - at n=5 the 95th percentile IS the maximum, and dressing the maximum up in
    a percentile's clothing is a proxy wearing a reputation."""
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return f"{UNREAD} (no arm reported a duration)"
    n = len(vals)
    mean = statistics.fmean(vals)
    p50 = statistics.median(vals)
    if n >= 20:
        p95 = statistics.quantiles(vals, n=20)[18]
        spread = f"p50 {p50:,.1f}, p95 {p95:,.1f}"
    else:
        spread = f"p50 {p50:,.1f}, min {vals[0]:,.1f}, max {vals[-1]:,.1f}"
    return f"{mean:,.1f} {unit}  (n={n}, {spread})"


# ── plumbing ─────────────────────────────────────────────────────────────────────────────────

def vram_mib() -> int:
    """MiB in use. Raises rather than returning a number nobody watched (SYM-031)."""
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                         capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        raise RuntimeError(f"nvidia-smi exited {out.returncode}: {out.stderr.strip()}")
    return int(out.stdout.strip().splitlines()[0])


PIPE_ROOT = fp_paths.pipeline_root()
GPU_LOCK = fp_paths.root("gpu_lock")


def convert_running() -> str | None:
    """The converter's busy SIGNAL, read and never written. Returns the book, or None.

    SYM-032 is precise: `.gpu-lock` is not a lock, because nothing gates on it. It is however a
    truthful signal - watch_and_convert.py:77 writes it before a conversion and :86 deletes it
    after - and reading it is exactly what room-chat does (chat.py, the same two-file contract).
    A measurement that starts while Marker is on the card measures Marker, and two model
    processes on one card is SYM-022's precondition, which cost a reboot in S71.
    """
    try:
        return GPU_LOCK.read_text(encoding="utf-8").strip() or "a conversion"
    except OSError:
        return None


def watcher_running() -> bool:
    """Is an intake watcher alive? Not fatal - it converts only when something is dropped - but
    the operator deserves to be told before a 30-minute measurement that a dropped PDF would
    land a second model on the card partway through."""
    try:
        out = subprocess.run(["tasklist"], capture_output=True, text=True, timeout=30)
        if out.returncode != 0:
            return False          # a failed probe is not a claim that nothing is running;
        return "python.exe" in out.stdout   # the caller prints UNREAD-shaped wording for that
    except Exception:  # noqa: BLE001
        return False


def cool_to(target_c: int, ceiling_s: int = 900, label: str = "") -> int | None:
    """Idle until the card is at or below target_c. Returns the temperature reached, or None.

    S82's finding is that arm order determines the answer: whichever arm runs last is measured on
    a hotter card than the one that ran first. A-B-A MEASURES that; this REMOVES it, by starting
    every arm from the same thermal state instead of from whatever the previous arm left behind.
    The two are complementary - the cool-down makes the comparison fair, the A-B-A proves it was.
    """
    t, _ = gpu_state()
    if t is None:
        print(f"  cool-down {label}: UNREAD - no temperature probe, proceeding uncooled",
              flush=True)
        return None
    if t <= target_c:
        print(f"  cool-down {label}: already {t}C (target {target_c}C)", flush=True)
        return t
    t0 = time.perf_counter()
    print(f"  cool-down {label}: {t}C, waiting for {target_c}C...", flush=True)
    while time.perf_counter() - t0 < ceiling_s:
        time.sleep(10)
        t, _ = gpu_state()
        if t is None or t <= target_c:
            break
    print(f"  cool-down {label}: {t}C after {time.perf_counter() - t0:.0f}s", flush=True)
    return t


def gpu_state() -> tuple[int | None, int | None]:
    """(temperature C, graphics clock MHz), or (None, None) if the probe failed.

    S82: sustained load moves these, and the arms run in a fixed order, so without them a
    position effect is indistinguishable from an engine difference. Never guess a value here -
    a failed probe returns None and prints UNREAD.
    """
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu,clocks.current.graphics",
             "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=15)
        if out.returncode != 0:
            return None, None
        t, c = out.stdout.strip().splitlines()[0].split(",")
        return int(t), int(c)
    except Exception:  # noqa: BLE001
        return None, None


def post(url: str, body: dict, timeout: int = REQUEST_TIMEOUT_S) -> dict:
    raw = json.dumps(body).encode("utf-8")
    proc = subprocess.run(["curl", "-s", "-X", "POST", url,
                           "-H", "Content-Type: application/json", "--data-binary", "@-"],
                          input=raw, capture_output=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"curl exited {proc.returncode}: {proc.stderr.decode('utf-8')[:200]}")
    return json.loads(proc.stdout.decode("utf-8"))


def _row(rec: dict) -> str:
    return (f"  chunk {rec['chunk']:>4}  in {rec['in_chars']:>5}c/{rec['prefill_tok'] or 0:>5}t  "
            f"out {rec['out_chars']:>5}c/{rec['decode_tok'] or 0:>5}t  stop={rec['stop']:<7} "
            f"fence={'ok' if rec['fence'] else 'BAD':<3}  "
            f"prefill {fmt_rate(rec['prefill_tps']):>7}  decode {fmt_rate(rec['decode_tps']):>6} "
            f"tok/s  wall {rec['wall_s']:>5.1f}s")


# ── the arms ─────────────────────────────────────────────────────────────────────────────────

def run_arm(label: str, send, picked: list[tuple[int, str]], warm_chunk: str | None) -> list[dict]:
    """One configuration under test. `send(chunk) -> (raw_response, text, phases, stop)`.

    docs/34 rule 2: cold and warm are never mixed. The warmup request is DISCARDED, not averaged
    in - a first request carries model load and cache population, and folding it into a mean
    produces a figure describing no request that was actually made.

    THE WARMUP CHUNK IS NOT ONE OF THE MEASURED ONES. The first draft warmed on picked[0], so the
    first measured request re-sent a prompt whose KV cache was already populated and its prefill
    was reported at 37,729 tok/s against 4,801 for the next chunk - an eightfold "speedup" that
    was the harness measuring its own warmup. docs/34 §4 documents this trap in the abstract; the
    instrument written to obey that document walked into it on its first run.
    """
    print("=" * 96 + f"\nARM - {label}\n" + "=" * 96, flush=True)
    if warm_chunk is not None:
        print("  warmup on an UNMEASURED chunk (discarded - docs/34 rule 2, and its prefill must "
              "not seed\n  the cache of a chunk we are about to time)...", flush=True)
        _raw, _text, wphases, _stop = send(warm_chunk)
        wtps = rate(wphases.get("prefill_tok"), wphases.get("prefill_s"))
        if wtps:
            # Informational ONLY. The S82 draft used this single point as the outlier REFERENCE,
            # and on one validation run the warmup was itself the anomaly (823 tok/s on a hot
            # card): two legitimate prefills were withheld against it (S82 §10.4). A single
            # measurement is never a reference - docs/21 rule 3 applies to the instrument's own
            # calibration too. The judge is the arm's MEDIAN, at reporting time.
            print(f"  warmup prefill {wtps:,.0f} tok/s  (informational - the outlier judge is "
                  f"the arm's own median)", flush=True)
    arm = []
    for i, chunk in picked:
        t0 = time.perf_counter()
        try:
            raw, text, phases, stop = send(chunk)
        except subprocess.TimeoutExpired:
            # S81: an ollama request stalled indefinitely on chunk 87 - ordinary prose, 3,537
            # chars, no tables - and the SAME chunk completed by hand in 7.5 s immediately after
            # (SYM-034, cause unproven). The first draft let that abort the run, so one transient
            # stall cost eight chunks across three arms. A measurement tool records the hole and
            # keeps measuring; it must never quietly average over it, so the record carries None
            # everywhere and the arm reports its stall count.
            print(f"  chunk {i:>4}  STALLED - no response in {REQUEST_TIMEOUT_S}s (SYM-034). "
                  f"Recorded as a hole, not a zero; continuing.", flush=True)
            arm.append({"chunk": i, "in_chars": len(chunk), "out_chars": 0, "stop": "STALL",
                        "fence": False, "wall_s": round(time.perf_counter() - t0, 2),
                        "stalled": True, "prefill_tok": None, "prefill_s": None,
                        "decode_tok": None, "decode_s": None, "cached_tok": None,
                        "prefill_tps": None, "decode_tps": None, "clock_ok": True})
            continue
        wall = time.perf_counter() - t0
        gt, gc = gpu_state()
        rec = {"chunk": i, "in_chars": len(chunk), "out_chars": len(text), "stop": stop,
               "fence": analyst._tokens_of(text) == analyst._tokens_of(chunk),
               "wall_s": round(wall, 2), "gpu_c": gt, "gpu_mhz": gc, **phases}
        rec["prefill_tps"] = prefill_rate(rec)
        rec["decode_tps"] = rate(rec["decode_tok"], rec["decode_s"])
        # The independent second clock (docs/34 §4). Server-reported phases share every
        # assumption the server makes; wall time is measured here and includes transport, so it
        # cannot be wrong in the same way. Server time must be LESS than wall time.
        srv = sum(x for x in (rec["prefill_s"], rec["decode_s"]) if x is not None)
        rec["clock_ok"] = srv <= rec["wall_s"] + 0.05
        if not rec["clock_ok"]:
            print(f"  !! chunk {i}: server phases {srv:.2f}s EXCEED wall {rec['wall_s']:.2f}s - "
                  f"the unit mapping is wrong, not the model", flush=True)
        arm.append(rec)
        print(_row(rec), flush=True)
    return arm


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", type=Path, default=DEFAULT_BOOK)
    ap.add_argument("-n", "--chunks", type=int, default=5)
    ap.add_argument("--gate-only", action="store_true", help="skip warmups and the throughput table")
    ap.add_argument("--cool-to", type=int, default=None, metavar="C",
                    help="idle until the GPU is at or below this temperature before EACH arm "
                         "(S82: arm order otherwise determines the answer)")
    ap.add_argument("--out", type=Path, default=Path(__file__).with_name("backend_parity.json"))
    args = ap.parse_args()
    warm = not args.gate_only

    # START FROM A PROVEN-COLD CARD. Two things go wrong otherwise, and S81 hit both in one run:
    # the "baseline" gets measured with a model already resident (7,323 MiB), which makes the
    # later unload check pass trivially; and Ollama's prompt cache still holds the previous run's
    # chunks, so the first measured prefills came back at 61,000-65,000 tok/s on a card that does
    # ~4,000-6,000. Ollama exposes NO cache field, so the contamination guard cannot see that -
    # the only real defence is to make the cache empty by construction. Unloading drops it.
    print("cold start: releasing any resident ollama model before the baseline...", flush=True)
    try:
        post(analyst.OLLAMA_URL, {"model": analyst.MODEL, "keep_alive": 0}, timeout=60)
    except Exception:  # noqa: BLE001 - nothing loaded is a perfectly good outcome
        pass
    settle = vram_mib()
    for _ in range(30):
        time.sleep(2)
        now = vram_mib()
        if abs(now - settle) < 60:
            break
        settle = now
    busy = convert_running()
    if busy:
        print(f"REFUSING: a conversion is running ({busy}). Two model processes on one card is "
              f"SYM-022,\n          which cost a reboot in S71. Wait for it to finish.")
        return 1
    if watcher_running():
        print("NOTE: an intake watcher is alive. Nothing is queued, but a PDF dropped during this\n"
              "      run would put Marker on the card beside the measurement. Do not drop while\n"
              "      this is running.\n")
    base = vram_mib()
    ollama_ver = json.loads(subprocess.run(
        ["curl", "-s", "http://localhost:11434/api/version"],
        capture_output=True, timeout=30).stdout.decode("utf-8")).get("version", "?")

    fenced, embeds = analyst.fence(args.book.read_text(encoding="utf-8"))
    chunks = analyst._chunks(fenced)
    program = analyst.load_program(analyst.DEFAULT_PROGRAM)
    step = max(1, len(chunks) // (args.chunks + 1))
    picked = [(i, chunks[i]) for i in range(step, len(chunks), step)][:args.chunks]
    # A warmup chunk that is NOT in the measured set - see run_arm's docstring.
    picked_ix = {i for i, _ in picked}
    warm_chunk = next((c for j, c in enumerate(chunks) if j not in picked_ix), None) if warm else None

    print(f"VRAM baseline {base} MiB - ollama {ollama_ver} - qwen3:8b - flash-attn on - "
          f"-c {analyst.NUM_CTX} - concurrency 1")
    print(f"book: {args.book.name}\n  {len(embeds)} embeds - {len(chunks)} chunks "
          f"@ target {analyst.CHUNK_TARGET}")
    print("  sampled: " + ", ".join(str(i) for i, _ in picked)
          + f"\n  a sample never promotes a claim about all {len(chunks)} chunks\n", flush=True)

    results: dict[str, list[dict]] = {}
    meta: dict[str, str] = {"ollama": ollama_ver}

    def ollama_send(chunk: str):
        r = post(analyst.OLLAMA_URL, {
            "model": analyst.MODEL, "stream": False, "keep_alive": analyst.KEEP_ALIVE_HOLD,
            "prompt": program + chunk, "options": {"num_ctx": analyst.NUM_CTX}, "think": False})
        if r.get("error"):
            raise RuntimeError(f"ollama: {r['error']}")
        return r, r["response"].strip(), _phases_ollama(r), r.get("done_reason")

    if args.cool_to:
        cool_to(args.cool_to, label="before arm 1 (ollama)")
    results["ollama_think_false"] = run_arm(
        "ollama /api/generate think:false (production today)", ollama_send, picked, warm_chunk)

    # SYM-022: one lab process on the card, ever. Prove the release, do not assume it.
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
        load_s = time.perf_counter() - t0
        print(f"llama-server cold load {load_s:.1f}s on :{PORT}  "
              f"(docs/34 cost 1 - reported, never folded into a warm rate)\n", flush=True)
        meta["llamacpp_load_s"] = f"{load_s:.1f}"

        def make_llama_send(extra: dict):
            def send(chunk: str):
                r = post(f"http://127.0.0.1:{PORT}/v1/chat/completions",
                         {"model": "qwen3", "stream": False, "cache_prompt": False,
                          "messages": [{"role": "user", "content": program + chunk}], **extra})
                if "choices" not in r:
                    raise RuntimeError(f"llama.cpp: {json.dumps(r)[:300]}")
                meta.setdefault("llamacpp", r.get("system_fingerprint", "?"))
                msg = r["choices"][0]["message"]
                return (r, (msg.get("content") or "").strip(), _phases_llamacpp(r),
                        r["choices"][0].get("finish_reason"))
            return send

        for label, extra in (
            ("llamacpp_jinja_default", {}),
            ("llamacpp_jinja_nothink", {"chat_template_kwargs": {"enable_thinking": False}}),
        ):
            if args.cool_to:
                cool_to(args.cool_to, label=f"before {label}")
            results[label] = run_arm(f"llama.cpp {label}", make_llama_send(extra), picked, warm_chunk)
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=30)
        except Exception:  # noqa: BLE001
            proc.kill()
        print("\nllama-server terminated.", flush=True)

    # ── A-B-A: measure the incumbent AGAIN, last ────────────────────────────────────────────
    #
    # S82's finding, and the reason this exists. The arms run in a fixed order, so the incumbent
    # was always measured first on a cool idle card and the candidates always after 20+ minutes
    # of sustained load. Within-arm regression on the n=30 run: decode rate correlated with
    # POSITION at r=-0.78 (llama default) and -0.36 (nothink) while correlating with output
    # length at only -0.33 and -0.15 - and the nothink arm's outputs are near-constant, so length
    # cannot explain it. The same config measured 97.7 tok/s in a 7-minute run and 77.7 in a
    # 25-minute one: -20.5 %, from run duration alone.
    #
    # An A/B where A is always first is not an A/B. Re-running the incumbent LAST turns the
    # confound into a measured quantity: whatever the card lost over the session shows up as
    # drift, and if it is large the ratios are withheld rather than published with a caveat
    # nobody will read.
    if not args.gate_only:
        print("\n" + "=" * 96)
        print("A-B-A CONTROL - re-measuring the incumbent LAST, on the card as the candidates "
              "found it")
        print("=" * 96, flush=True)
        if args.cool_to:
            cool_to(args.cool_to, label="before the A-B-A recheck")
        results["ollama_recheck"] = run_arm(
            "ollama /api/generate think:false (RECHECK, end of run)", ollama_send, picked,
            warm_chunk)

    # ── 1. THE TOKEN GATE ────────────────────────────────────────────────────────────────────
    # S83: judge prefill outliers against each arm's own median - see the function.
    for label, rows in results.items():
        for r in censor_prefill_outliers(rows):
            print(f"  {label}  chunk {r['chunk']:>4}: prefill withheld - above "
                  f"{PREFILL_IMPLAUSIBLE_X:g}x the arm median (cache or mismeasure)")

    print("\n" + "=" * 96)
    print("1. TOKEN GATE - does it write the same SIZE of thing, stop by itself, pass the fence?")
    print("=" * 96)
    print(f"{'arm':<26}{'decode tok':>11}{'max':>8}{'not-stop':>10}{'fence bad':>11}{'vs ollama':>12}")
    incumbent = results["ollama_think_false"]
    ref = sum(r["decode_tok"] or 0 for r in incumbent)
    # THE INCUMBENT DEFINES THE BAR, it does not have to be perfect. The first draft required zero
    # fence failures outright, so the moment ollama itself rejected a chunk - which it does; the
    # analyst's own reject counter exists for that - the production backend FAILED its own gate.
    # A candidate has to be no WORSE than what is already shipping, which is the actual question.
    ref_fence = sum(1 for r in incumbent if not r["fence"])
    ref_stop = sum(1 for r in incumbent if r["stop"] != "stop")
    gate = {}
    for label, rows in results.items():
        if label == "ollama_recheck":
            continue
        tot = sum(r["decode_tok"] or 0 for r in rows)
        bad_stop = sum(1 for r in rows if r["stop"] != "stop")
        bad_fence = sum(1 for r in rows if not r["fence"])
        print(f"{label:<26}{tot:>11,}{max(r['decode_tok'] or 0 for r in rows):>8,}{bad_stop:>10}"
              f"{bad_fence:>11}{100.0 * (tot - ref) / ref:>+11.1f}%")
        gate[label] = gate_verdict(tot, ref, bad_stop, ref_stop, bad_fence, ref_fence)
    if ref_fence or ref_stop:
        print(f"  (bar set by the incumbent: {ref_fence} fence failure(s), {ref_stop} non-stop - "
              f"a candidate must be no worse, not perfect)")
    for label, good in gate.items():
        print(f"  {'PASS' if good else 'FAIL'}  {label}")

    if args.gate_only:
        args.out.write_text(json.dumps({"meta": meta, "arms": results}, indent=2), encoding="utf-8")
        print(f"\nraw -> {args.out}")
        return 0

    # ── 2. THROUGHPUT ────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 96)
    print("2. THROUGHPUT - warm, concurrency 1. Prefill and decode NEVER blended (docs/34 §1).")
    print("=" * 96)
    print(f"  builds: ollama {meta.get('ollama')} - llama.cpp {meta.get('llamacpp', '?')}"
          f" - llama.cpp cold load {meta.get('llamacpp_load_s', '?')}s (excluded below)")
    def _cache_total(rows: list[dict]) -> str:
        vals = [r.get("cached_tok") for r in rows]
        return UNREAD if all(v is None for v in vals) else str(sum(v or 0 for v in vals))
    cache = {lb: _cache_total(rows) for lb, rows in results.items()}
    print("  cached prefill tokens: " + ", ".join(f"{lb.split('_')[0]}={v}"
                                                   for lb, v in cache.items())
          + "   (a cached prefill is not a measured prefill - docs/34 §4)\n")
    for label, rows in results.items():
        stalls = sum(1 for r in rows if r.get("stalled"))
        print(f"  {label}" + (f"   [{stalls} STALLED - excluded, SYM-034]" if stalls else ""))
        print(f"      prefill throughput  {summarise([r['prefill_tps'] for r in rows], 'tok/s')}")
        print(f"      decode  throughput  {summarise([r['decode_tps'] for r in rows], 'tok/s')}")
        print(f"      end-to-end latency  {summarise([r['wall_s'] for r in rows], 's')}")
        bad_clock = sum(1 for r in rows if not r["clock_ok"])
        if bad_clock:
            print(f"      !! {bad_clock} request(s): server phases exceeded wall time")
        print()

    # ── 3. THE RATIO - both sides, always (docs/34 rule 4) ───────────────────────────────────
    print("=" * 96)
    print("3. SPEEDUP - only meaningful for an arm that PASSED the token gate")
    print("=" * 96)
    o = results["ollama_think_false"]
    o_dec = statistics.fmean([r["decode_tps"] for r in o if r["decode_tps"] is not None])

    # The confound, measured. If the incumbent is materially slower the second time, the card
    # changed underneath the experiment and every cross-arm ratio inherits that change.
    drift = None
    recheck = results.get("ollama_recheck")
    if recheck:
        r_dec = statistics.fmean([r["decode_tps"] for r in recheck if r["decode_tps"] is not None])
        drift, admissible = order_drift_verdict(o_dec, r_dec)
        c0 = [r["gpu_c"] for r in o if r.get("gpu_c")]
        c1 = [r["gpu_c"] for r in recheck if r.get("gpu_c")]
        temps = (f"  GPU {statistics.fmean(c0):.0f}C -> {statistics.fmean(c1):.0f}C"
                 if c0 and c1 else f"  GPU temp {UNREAD}")
        print(f"  ORDER DRIFT: incumbent decode {o_dec:,.1f} tok/s first, {r_dec:,.1f} last "
              f"= {drift:+.1%}{temps}")
        if not admissible:
            print(f"\n  *** RATIOS WITHHELD. The incumbent moved {drift:+.1%} between its two "
                  f"measurements,\n      which is more than the {ORDER_DRIFT_LIMIT:.0%} limit. The "
                  f"card did not hold still, so a\n      cross-arm ratio would report the run's "
                  f"own drift as an engine difference.\n      Re-measure with a cooled card, or "
                  f"compare each arm against the incumbent\n      measurement nearest it in time.")
            return 0
        print(f"  (within the {ORDER_DRIFT_LIMIT:.0%} limit - ratios below are admissible)\n")

    for label, rows in results.items():
        if label in ("ollama_think_false", "ollama_recheck"):
            continue
        vals = [r["decode_tps"] for r in rows if r["decode_tps"] is not None]
        if not vals:
            print(f"  {label}: {UNREAD}")
            continue
        c_dec = statistics.fmean(vals)
        verdict = "" if gate[label] else "   <- FAILED THE TOKEN GATE, speed is not admissible"
        print(f"  {label}:  decode {c_dec:,.1f} tok/s  vs  ollama {o_dec:,.1f} tok/s  "
              f"= {c_dec / o_dec:.2f}x{verdict}")
    print("\n  A speedup prints both of its sides (docs/34 rule 4). n is small; raise -n before\n"
          "  this is used to justify a migration. Sampling never promotes.")

    args.out.write_text(json.dumps({"meta": meta, "arms": results}, indent=2), encoding="utf-8")
    print(f"\nraw -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
