#!/usr/bin/env python3
"""The Room's assistant — quarantined prototype (S79, docs/33).

Rab's spec: a button loads the model, a window opens and greets you with a model-loaded
confirmation, a button unloads it, and **a convert cannot happen while the chat is loaded, and
vice versa**.

WHAT THIS IS NOT. It is not an oracle. docs/33 §2.2: verify-before-instruct forbids instructing
from recall, and a model answering from baked context IS recall. So this is a CITATION ENGINE —
every answer either carries a citation that resolves to a real line of a real file, or the answer
is replaced by a refusal. That check is mechanical (`_enforce_citation`), not a request in the
prompt: asking a model to cite and trusting that it did is a proxy for compliance, and docs/32 is
a document about what proxies do.

AND IT MAY NOT SPEAK FOR THE PIPELINE. docs/33 §2.1, signed by Rab 2026-08-15: live values are
rendered through the existing projection path verbatim; the model may point at a surface, never
restate it. So `/api/state` returns pipeline numbers as DATA the page renders, and those numbers
are never put in the model's mouth.

Quarantine (per the prototypes convention): stdlib only, nothing imports this, zero pipeline
coupling except two marker files whose ownership is spelled out in `_hold` below.

    python chat.py --port 7100
    python chat.py --port 7100 --llama "C:\\Users\\Bndit\\ml\\llama\\llama-server.exe"
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parent.parent
PIPE = Path(os.environ.get("FP_PIPELINE", r"C:\Users\Bndit\ml\library"))

# docs/33 §2.5 — the bench owns 7077..7096. Taking one of its ports would make the next Repair
# Bench open land somewhere its window does not expect. A distinct range, and a distinct one for
# the model server so the two cannot collide with each other either.
UI_PORT_DEFAULT = 7100
LLAMA_PORTS = range(7110, 7120)

# docs/33 §2.4 — bench.rs waits 6 s, correct for a stdlib server and WRONG here: an 8B model
# takes ~20 s to load cold (measured 19.54 s first load, ~4.7 s warm). A 6 s ceiling would report
# a healthy server dead on every cold start. The ceiling scales to the model file, and the two
# outcomes are told apart: a process that is ALIVE and not yet answering is LOADING; a process
# that has EXITED is dead and its last words are on disk.
LOAD_TIMEOUT_FLOOR_S = 90
LOAD_TIMEOUT_PER_GB_S = 12

MODEL_GGUF = Path(os.environ.get(
    "FP_CHAT_MODEL",
    r"C:\Users\Bndit\.ollama\models\blobs"
    r"\sha256-a3de86cd1c132c822487ededd47a324c50491393e6565cd14bafa40d0b8e686f"))


# ── the mutex (docs/33 §2.3, signed) ─────────────────────────────────────────────────────────
#
# There is no mutual exclusion in this pipeline today: `.gpu-lock` is written by the watcher at
# watch_and_convert.py:77 and deleted at :86, and read as a gate by NOTHING. A file named lock
# that locks nothing. So the mutex is built here, in the shape the single-writer law allows:
#
#   chat-hold.json   WE write it. The widget/user-intent side, exactly the analyst-mode.txt
#                    pattern — our file, our writes, Python reads it.
#   .gpu-lock        the CONVERTER writes it. We only ever read it. That is the projection law
#                    working normally, not an exception to it.
#
# Load is two-phase: write the hold, THEN read the lock. Recording precedes action (docs/28's
# chokepoint), and the ordering makes the chat yield to the pipeline — a convert is expensive and
# interruption-hostile, a chat session is neither. If the lock turns out to be there, we drop our
# hold and refuse. Worst case both sides yield, which is the safe direction (docs/19: "a lost
# intent is the safe direction").
HOLD = PIPE / "chat-hold.json"
GPU_LOCK = PIPE / ".gpu-lock"


def _hold_write(port: int, model: str) -> None:
    HOLD.write_text(json.dumps({
        "held_by": "room-chat", "pid": os.getpid(), "port": port, "model": model,
        "since": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "_why": "the GPU is held by the Room's assistant; a convert must defer until this is gone",
    }, indent=1), encoding="utf-8")


def _hold_clear() -> None:
    try:
        HOLD.unlink(missing_ok=True)
    except OSError:
        pass


def convert_running() -> str | None:
    """The converter's own file, read never written. Returns the book, or None."""
    try:
        return GPU_LOCK.read_text(encoding="utf-8").strip() or "a conversion"
    except OSError:
        return None


# ── the corpus: curated, and every citation is checked against it ────────────────────────────
#
# docs/20 IS the operator manual — 393 lines, written for exactly this reader. It fits an 8k
# context alongside a question and an answer, which retrieval over 40,000 lines does not. Start
# where the answers already are; add retrieval only if the real questions demand it (docs/33 §3.3
# — that decision waits on Rab's ten questions, and guessing the workload first would be choosing
# a proxy and calling it the property).
CORPUS = [
    ("docs/20-file-portal-manual.md", "the operator manual — surfaces, levers, the life of a book"),
]


def load_corpus() -> tuple[str, dict[str, list[str]]]:
    """Returns (context_text, {path: lines}) — the lines are what citations are checked against."""
    parts, index = [], {}
    for rel, why in CORPUS:
        p = REPO / rel
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        index[rel] = text.splitlines()
        parts.append(f"===== {rel} — {why} =====\n{text}")
    return "\n\n".join(parts), index


SYSTEM = """You answer questions about the File Portal document pipeline for its operator.

RULES, and they are enforced mechanically after you answer — breaking them gets your answer
thrown away and replaced with a refusal:

1. Every factual claim must carry a citation in the form (docs/20 §N) or (path:line).
   Cite ONLY the documents given to you below. Never cite anything you were not given.
2. If the documents below do not answer the question, say exactly:
   I don't know — that isn't in the manual I was given.
   That is a good answer. A guess is not.
3. Never state a live number, status or verdict — not the queue depth, not what is held, not
   whether the watcher is running. The interface shows those directly and is the only thing
   permitted to. Point at the surface instead: "the Room's station rail shows that".
4. Be brief. An operator is mid-task.
"""


CITE_RE = re.compile(r"\((docs/[\w.\-]+(?:\.md)?)\s*§?\s*([\d.]+)?\)|\(([\w./\\-]+):(\d+)\)")


def _enforce_citation(answer: str, index: dict[str, list[str]]) -> tuple[str, list[str], str]:
    """THE GUARD. Returns (answer_or_refusal, resolved_citations, verdict).

    The property: an answer is admissible only if it points at something the operator can open
    and check. The proxy would be "the prompt asked for citations" — and a prompt is a request,
    not a mechanism. So the citations are extracted and RESOLVED here: the cited file must exist
    in the corpus we actually gave the model, or the citation does not count.

    A refusal is a success. docs/33 §2.2: no citation, no answer.
    """
    if "I don't know" in answer:
        return answer, [], "honest-refusal"
    found, resolved = CITE_RE.findall(answer), []
    for doc, sec, path, line in found:
        target = doc or path
        if not target:
            continue
        # Citations name a doc by its STEM ("docs/20"), while the corpus keys it by full filename
        # ("docs/20-file-portal-manual.md"). The first version of this compared with endswith()
        # both ways and resolved NEITHER — every correct answer would have been withheld as
        # uncited, and the guard would have looked like it was working hard. Found by writing the
        # test, not by reading the code.
        tgt = target.replace("\\", "/").strip()
        hit = next((k for k in index
                    if k == tgt or k.startswith(tgt) or tgt.startswith(k)
                    or k.split("/")[-1].startswith(tgt.split("/")[-1])), None)
        if hit:
            resolved.append(f"{target}{'§' + sec if sec else ''}{':' + line if line else ''}")
    if not resolved:
        return ("I don't know — that isn't in the manual I was given.\n\n"
                "(An answer was produced but carried no citation that resolves to a document "
                "I was actually given, so it was withheld. docs/33 §2.2.)"), [], "withheld-uncited"
    return answer, resolved, "cited"


# ── the model server: spawn, readiness, unload ───────────────────────────────────────────────
class Llama:
    def __init__(self, exe: Path, model: Path):
        self.exe, self.model = exe, model
        self.proc: subprocess.Popen | None = None
        self.port: int | None = None
        self.started: float | None = None
        self.ready_s: float | None = None   # load DURATION, measured once at readiness

    @property
    def loaded(self) -> bool:
        return self.proc is not None and self.proc.poll() is None and self.port is not None

    def _free_port(self) -> int:
        for p in LLAMA_PORTS:
            with socket.socket() as s:
                if s.connect_ex(("127.0.0.1", p)) != 0:
                    return p
        raise RuntimeError(f"no free port in {LLAMA_PORTS.start}..{LLAMA_PORTS.stop}")

    def load(self) -> dict:
        if self.loaded:
            return self.status()
        busy = convert_running()
        if busy:
            raise RuntimeError(f"a conversion is running ({busy}) — the card is not free")
        if not self.exe.is_file():
            raise RuntimeError(f"llama-server not found: {self.exe}")
        if not self.model.is_file():
            raise RuntimeError(f"model not found: {self.model}")
        self.port = self._free_port()
        _hold_write(self.port, self.model.name)          # record precedes action
        again = convert_running()                        # ...then re-check, and yield if we lost
        if again:
            _hold_clear()
            raise RuntimeError(f"a conversion started while loading ({again}) — yielding the card")
        errlog = PIPE / "chat-stderr.log"
        self.proc = subprocess.Popen(
            [str(self.exe), "-m", str(self.model), "-ngl", "99", "-c", "8192",
             "--flash-attn", "on", "--jinja", "--host", "127.0.0.1", "--port", str(self.port)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=open(errlog, "wb"),      # last words, the watcher-stderr idiom
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.started = time.perf_counter()
        gb = self.model.stat().st_size / 1e9
        ceiling = LOAD_TIMEOUT_FLOOR_S + LOAD_TIMEOUT_PER_GB_S * gb
        while time.perf_counter() - self.started < ceiling:
            if self.proc.poll() is not None:              # DIED — not "did not come up"
                _hold_clear()
                raise RuntimeError(f"llama-server exited {self.proc.returncode} while loading "
                                   f"— last words in {errlog.name}")
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/health", timeout=2) as r:
                    if json.loads(r.read()).get("status") == "ok":
                        # Captured ONCE, here. The first version reported
                        # `perf_counter() - started` from status(), which is UPTIME, and the
                        # greeting said "came up in 73.7 s" of a model that came up in 33.
                        # A field whose label disagrees with its arithmetic is the same defect
                        # class as a lock that does not lock.
                        self.ready_s = round(time.perf_counter() - self.started, 1)
                        return self.status()
            except Exception:                              # noqa: BLE001 — still LOADING
                time.sleep(0.5)
        self.unload()
        raise RuntimeError(f"llama-server did not answer within {ceiling:.0f}s (it was still "
                           f"alive — this is a timeout, not a crash)")

    def unload(self) -> dict:
        if self.proc is not None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=20)
            except Exception:                              # noqa: BLE001
                try:
                    self.proc.kill()
                except Exception:                          # noqa: BLE001
                    pass
        self.proc, self.port, self.started, self.ready_s = None, None, None, None
        _hold_clear()                                      # release is an ACT
        return self.status()

    def status(self) -> dict:
        return {"loaded": self.loaded, "port": self.port,
                "model": self.model.name if self.model else None,
                "model_gb": round(self.model.stat().st_size / 1e9, 2) if self.model.is_file() else None,
                "load_s": self.ready_s,
                "uptime_s": round(time.perf_counter() - self.started, 1) if (self.loaded and self.started) else None,
                "hold_file": str(HOLD) if HOLD.is_file() else None,
                "convert_running": convert_running()}

    def ask(self, question: str, context: str) -> str:
        body = json.dumps({
            "model": "chat",
            "messages": [{"role": "system", "content": SYSTEM + "\n\n" + context},
                         {"role": "user", "content": question}],
            "max_tokens": 700, "temperature": 0.2,
        }).encode("utf-8")
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/v1/chat/completions",
                                     data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"].strip()


# ── the surface's own state, read from disk, never from the model (docs/33 §2.1) ─────────────
def pipeline_state() -> dict:
    def count(sub, pat="*"):
        try:
            return len([p for p in (PIPE / sub).glob(pat)])
        except OSError:
            return None
    def read(name):
        try:
            return (PIPE / name).read_text(encoding="utf-8").strip()
        except OSError:
            return None
    return {"held": count("held"), "anchor": count("anchor"), "pending": count("pending"),
            "drop_pdfs": count("drop", "*.pdf"), "audit_mode": read("audit-mode.txt"),
            "analyst_mode": read("analyst-mode.txt"), "convert_running": convert_running()}


class Handler(BaseHTTPRequestHandler):
    llama: Llama
    context: str
    index: dict

    def log_message(self, *a):    # quiet; last words go to the stderr file
        pass

    def _send(self, code, payload, ctype="application/json"):
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self._send(200, (HERE / "chat.html").read_bytes(), "text/html; charset=utf-8")
        if self.path == "/api/status":
            return self._send(200, self.llama.status())
        if self.path == "/api/state":
            return self._send(200, pipeline_state())
        self._send(404, {"error": "not found"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        req = json.loads(self.rfile.read(n) or b"{}")
        try:
            if self.path == "/api/load":
                return self._send(200, self.llama.load())
            if self.path == "/api/unload":
                return self._send(200, self.llama.unload())
            if self.path == "/api/ask":
                if not self.llama.loaded:
                    return self._send(409, {"error": "the model is not loaded"})
                raw = self.llama.ask(req.get("q", ""), self.context)
                answer, cites, verdict = _enforce_citation(raw, self.index)
                return self._send(200, {"answer": answer, "citations": cites,
                                        "verdict": verdict, "withheld": raw if verdict == "withheld-uncited" else None})
        except Exception as e:                             # noqa: BLE001
            return self._send(500, {"error": str(e)})
        self._send(404, {"error": "not found"})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=UI_PORT_DEFAULT)
    ap.add_argument("--llama", default=os.environ.get("FP_LLAMA_SERVER", r"C:\Users\Bndit\ml\llama\llama-server.exe"))
    ap.add_argument("--model", default=str(MODEL_GGUF))
    a = ap.parse_args()

    context, index = load_corpus()
    if not index:
        sys.exit(f"no corpus — expected {CORPUS[0][0]} under {REPO}")
    Handler.llama = Llama(Path(a.llama), Path(a.model))
    Handler.context, Handler.index = context, index
    print(f"room-chat on http://127.0.0.1:{a.port}  ·  corpus {list(index)} "
          f"({len(context):,} chars)  ·  llama {a.llama}", flush=True)
    try:
        ThreadingHTTPServer(("127.0.0.1", a.port), Handler).serve_forever()
    except KeyboardInterrupt:
        Handler.llama.unload()          # the card comes back even on Ctrl+C
        print("\nunloaded, hold cleared", flush=True)


if __name__ == "__main__":
    main()
