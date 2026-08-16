#!/usr/bin/env python3
"""Tripwires for the Room's assistant (S79, docs/33).

docs/32 §6 predicts the next proxy substitution appears in whatever is built next to enforce a
rule. What is built here is a MUTEX and a CITATION GUARD — a lock is a proxy for exclusion, and a
citation is a proxy for checkability. So each is stepped on: the property is violated and the
guard is required to fire.

CASE 0 is a positive control. Without it a suite can pass because everything always refuses,
which is the tautology S78 shipped in this exact position.

No GPU, no llama-server, no network — every case here is the logic, so it runs in a second and
there is no excuse for skipping it.

    python acceptance.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent

# Point the module at a scratch pipeline BEFORE importing it — the marker files are module-level
# paths, and a test that wrote to the real C:\Users\Bndit\ml\library would be a test that can
# stop a real convert.
SCRATCH = Path(tempfile.mkdtemp(prefix="room-chat-test-"))
os.environ["FP_PIPELINE"] = str(SCRATCH)

spec = importlib.util.spec_from_file_location("chat", HERE / "room_chat.py")
chat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chat)

passed = failed = 0


def ok(name):
    global passed
    print(f"  ok   {name}")
    passed += 1


def bad(name, why):
    global failed
    print(f"  FAIL {name}\n       {why}")
    failed += 1


def check(name, cond, why=""):
    ok(name) if cond else bad(name, why)


print(f"\nscratch pipeline: {SCRATCH}\n")
print("── the citation guard (docs/33 §2.2) ──")

_, index = chat.load_corpus()
check("the corpus loaded at all", bool(index), "no corpus — every case below is vacuous")

# CASE 0 — POSITIVE CONTROL. A properly cited answer must SURVIVE. Without this the guard could
# refuse everything and every other case would still pass.
a, cites, verdict = chat._enforce_citation(
    "The ⚡ tile is a drag target, not a switch (docs/20 §2).", index)
check("CONTROL: a correctly cited answer survives", verdict == "cited" and "⚡" in a,
      f"verdict={verdict} cites={cites} — the guard is refusing valid answers")
check("...and the citation is reported back to the operator", bool(cites), "no citations surfaced")

# The property: an answer is admissible only if it points somewhere the operator can open.
a, cites, verdict = chat._enforce_citation(
    "The watcher polls every five seconds and restarts itself automatically.", index)
check("an UNCITED answer is withheld", verdict == "withheld-uncited" and "I don't know" in a,
      f"verdict={verdict} — an uncited claim reached the operator")

# The sharpest case: a citation that LOOKS right and names a document we never gave it. A guard
# that accepts this is checking the shape of a citation, not its resolution.
a, cites, verdict = chat._enforce_citation(
    "Force OCR is enabled from the Room's engine menu (docs/99-nonexistent.md §4).", index)
check("a HALLUCINATED citation does not resolve", verdict == "withheld-uncited",
      f"verdict={verdict} cites={cites} — the guard accepted a citation to a doc it never had")

a, cites, verdict = chat._enforce_citation(
    "I don't know — that isn't in the manual I was given.", index)
check("an honest refusal passes through unaltered", verdict == "honest-refusal",
      "the guard mangled a refusal")

print("\n── the mutex (docs/33 §2.3, signed) ──")

lock = SCRATCH / ".gpu-lock"
hold = SCRATCH / "chat-hold.json"
chat.GPU_LOCK, chat.HOLD = lock, hold          # rebind: module-level paths resolved at import

check("CONTROL: with no lock, the card reads free", chat.convert_running() is None,
      "convert_running() sees a convert that is not there")

lock.write_text("Some Book.pdf", encoding="utf-8")
check("a convert in flight is seen", chat.convert_running() == "Some Book.pdf",
      "the converter's own lock file was not read")

# THE TRIPWIRE: violate the property (card busy) and require the guard to fire.
llama = chat.Llama(Path("nonexistent-llama-server.exe"), Path(__file__))
try:
    llama.load()
    bad("load REFUSES while a convert holds the card", "it loaded anyway — the mutex is decorative")
except RuntimeError as e:
    check("load REFUSES while a convert holds the card", "conversion is running" in str(e),
          f"refused for the wrong reason: {e}")
check("...and it left NO orphan hold behind", not hold.exists(),
      "a refused load left chat-hold.json on disk — a convert would defer forever")

lock.unlink()
# Now the reverse: the hold must exist while loaded, so the watcher can see it. The spawn will
# fail (fake exe) — what matters is that the hold was written BEFORE the spawn was attempted and
# cleaned up when the spawn failed.
try:
    llama.load()
except RuntimeError as e:
    check("a missing llama-server refuses by NAME, not silently", "not found" in str(e), str(e))
check("a failed load leaves no orphan hold", not hold.exists(),
      "chat-hold.json survived a failed load — the pipeline would defer forever")

chat._hold_write(7110, "test.gguf")
check("the hold names WHY it exists, for whoever finds it", "_why" in json.loads(hold.read_text()),
      "the marker gives a finder nothing to act on")
llama.unload()
check("unload clears the hold — release is an ACT", not hold.exists(),
      "unload left the hold behind; the card would never come back")

print("\n── the borrowed lifecycle (docs/33 §2.4, §2.5) ──")

check("the load ceiling is not bench.rs's 6 s", chat.LOAD_TIMEOUT_FLOOR_S >= 60,
      f"floor is {chat.LOAD_TIMEOUT_FLOOR_S}s — an 8B model needs ~20 s cold and this would "
      f"report a healthy server dead")
check("the ceiling scales with model size", chat.LOAD_TIMEOUT_PER_GB_S > 0,
      "a fixed ceiling breaks on a larger model")
bench_range = set(range(7077, 7097))
check("the model ports do not collide with the bench", not (set(chat.LLAMA_PORTS) & bench_range),
      f"{sorted(set(chat.LLAMA_PORTS) & bench_range)} overlap the Repair Bench's range")
check("the UI port does not collide with the bench", chat.UI_PORT_DEFAULT not in bench_range,
      "the chat UI would take a port the bench expects")

print("\n── the projection law (docs/33 §2.1, signed) ──")

check("live state is served as DATA, not narrated by the model",
      callable(chat.pipeline_state) and "held" in chat.pipeline_state(),
      "no independent state projection — the model would be the only source of live numbers")
check("the system prompt forbids stating live values", "Never state a live number" in chat.SYSTEM,
      "nothing tells the model to stay out of the projection's lane")

import shutil
shutil.rmtree(SCRATCH, ignore_errors=True)
print(f"\n{'-'*46}")
if failed:
    print(f"TRIPWIRES DISARMED — {failed} failed of {passed+failed}")
    sys.exit(1)
print(f"ALL TRIPWIRES FIRED — {passed}/{passed+failed}")
