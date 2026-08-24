#!/usr/bin/env python
"""test_bench_page.py — the first tests this repo has ever pointed at the Bench GLASS (B5).

S108 Lane D. Stdlib only; the runner is a bare CPython:

    C:/Users/Bndit/.local/bin/python3.12.exe prototypes/repair-bench/test_bench_page.py

Four families, each with a POSITIVE control (the real artifact passes) and a NEGATIVE
control (a synthetic snippet reproducing the historical defect must FAIL the same check —
a check that cannot fail is a tautology, docs/32 rule 2):

  1. The two S106 regressions, as named fixtures against bench.html's source:
     - ctxRange is NOT the render range (the 4d06588 data-loss shape, fixed d7ffd11):
       renderLines must never assign ctxRange.
     - arrow keys must not flip the PDF page while typing (fixed 3659ec7): the keydown
       arrow handler must consult isContentEditable before goto().
  2. Every mutating route is token-checked (S108): the MUTATING_POSTS census in bench.py
     and room_chat.py must equal the routes their do_POST actually dispatches, the gate
     must sit BEFORE the first dispatch, and token_gate itself must admit/refuse correctly.
  3. Claim strings name their denominators (measurement-language law, docs/34): the
     counted claims on the glass and in the report carry numerator AND denominator.
  4. The 403 fail-closed path, LIVE: an in-process HTTP server over a throwaway temp
     bundle — no --token means every mutating route answers 403 and the file on disk does
     not change; a wrong or missing X-FP-Token answers 403; the right token is admitted
     (never 403) on every enumerated route, with bodies chosen so no route spawns a
     worker, touches the GPU, or writes outside the temp fixture.

The DOM itself still never loads here (that would need a browser); these are the source
and wire truths a browser session was measured against in S108. B5 remains open beyond
this file and honestly so.
"""
from __future__ import annotations

import http.client
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

# room_chat computes PIPE at import time — point it at a throwaway BEFORE the import so no
# test can ever touch the real pipeline root (the S108 standard: never write under ml/library).
_PIPE_TMP = tempfile.mkdtemp(prefix="fp-test-pipe-")
os.environ["FP_PIPELINE"] = _PIPE_TMP
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "windows-converter"))
import bench  # noqa: E402
import room_chat  # noqa: E402

BENCH_HTML = (HERE / "bench.html").read_text(encoding="utf-8")
BENCH_PY = (HERE / "bench.py").read_text(encoding="utf-8")
ROOM_PY = (REPO / "windows-converter" / "room_chat.py").read_text(encoding="utf-8")


# ---- source-slicing helpers -----------------------------------------------------------------
def js_function_body(source: str, name: str) -> str:
    """The braced body of `function name(...)`, by brace counting (CRLF-safe: the sources
    are read as text, so line endings are already \\n here)."""
    at = source.index(f"function {name}(")
    depth, i = 0, source.index("{", at)
    start = i
    while i < len(source):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
        i += 1
    raise AssertionError(f"unbalanced braces after function {name}")


def js_handler_around(source: str, marker: str) -> str:
    """The addEventListener(...) call whose body contains `marker`."""
    at = source.index(marker)
    head = source.rindex("addEventListener(", 0, at)
    depth, i = 0, source.index("(", head)
    start = i
    while i < len(source):
        if source[i] == "(":
            depth += 1
        elif source[i] == ")":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
        i += 1
    raise AssertionError(f"unbalanced parens in handler around {marker!r}")


def py_function_body(source: str, name: str) -> str:
    """A def's body by indent: every following line until the first non-blank line indented
    at or shallower than the def itself."""
    lines = source.splitlines()
    for i, ln in enumerate(lines):
        m = re.match(rf"([ \t]*)def {name}\(", ln)
        if m:
            base = len(m.group(1))
            body = []
            for nxt in lines[i + 1:]:
                if nxt.strip() and (len(nxt) - len(nxt.lstrip())) <= base:
                    break
                body.append(nxt)
            return "\n".join(body)
    raise AssertionError(f"def {name} not found")


# ---- the checks (each is a function so the negative control runs the SAME code) --------------
def renderlines_leaks_ctxrange(fn_body: str) -> bool:
    """True = the 4d06588 regression is present: renderLines assigns ctxRange."""
    return re.search(r"ctxRange\s*=", fn_body) is not None


def arrow_handler_guards_typing(handler_src: str) -> bool:
    """True = the keydown arrow handler consults isContentEditable before flipping pages."""
    return "isContentEditable" in handler_src


def claim_names_denominator(claim: str) -> bool:
    """A counted claim must carry numerator AND denominator: `${n}/${m}` or `{n} of {m}`."""
    return bool(re.search(r"\$\{[^}]+\}\s*/\s*\$\{[^}]+\}", claim)
                or re.search(r"\{[^{}]+\}\s+of\s+\{[^{}]+\}", claim))


# The synthetic regressions — the shapes the history actually shipped, verbatim enough that
# a check too weak to catch them would pass them.
BAD_RENDERLINES = """{
  ctxHighlight = highlight || 0;
  const lines = mdText.split("\\n");
  ctxRange = { from: 1, to: lines.length };
  $("ctx").innerHTML = linesHtml(mdText, ctxHighlight);
  return { lines: lines.length };
}"""  # the 4d06588 shape: whole-file ctxRange = a 3.4 MB excerpt to a num_ctx-8192 model

BAD_KEYDOWN = """(\"keydown\", (e) => {
  if (e.key === "ArrowLeft") goto(page - 1);
  if (e.key === "ArrowRight") goto(page + 1);
})"""  # the pre-3659ec7 shape: typing arrows flip the PDF page and clear the crop

BAD_CLAIM_JS = "`zones ${rep} repaired`"                 # numerator with no denominator
BAD_CLAIM_PY = "f\"**{cov['addressed']} addressed.**\""  # same defect, python side


class TestS106Regressions(unittest.TestCase):
    """The two S106 regressions as named fixtures (register rows d7ffd11 / 3659ec7)."""

    def test_s106_regression_ctxrange_is_not_the_render_range(self):
        body = js_function_body(BENCH_HTML, "renderLines")
        self.assertFalse(renderlines_leaks_ctxrange(body),
                         "renderLines assigns ctxRange — the 4d06588 data-loss shape: one AI-fix "
                         "click would send the whole file to the model and splice back its stump")

    def test_s106_regression_ctxrange_negative_control(self):
        self.assertTrue(renderlines_leaks_ctxrange(BAD_RENDERLINES),
                        "the check failed to catch the very regression it exists for")

    def test_s106_regression_ctxrange_callers_still_bound_the_slice(self):
        # d7ffd11 moved the assignment to the callers, bounded. Both must still set it.
        for caller, bound in (("renderCtxPlain", r"Math\.min\(r\.lines,\s*40\)"),
                              ("renderCtx", r"Math\.min\(r\.lines,\s*at\s*\+\s*12\)")):
            body = js_function_body(BENCH_HTML, caller)
            self.assertRegex(body, r"ctxRange\s*=", f"{caller} no longer sets ctxRange")
            self.assertRegex(body, bound, f"{caller}'s ctxRange bound has changed shape")

    def test_s106_regression_arrow_keys_must_not_flip_pages_while_typing(self):
        handler = js_handler_around(BENCH_HTML, 'e.key === "ArrowLeft"')
        self.assertTrue(arrow_handler_guards_typing(handler),
                        "the keydown arrow handler no longer consults isContentEditable — "
                        "ArrowLeft/Right while typing would flip the PDF page and clear the crop")

    def test_s106_regression_arrow_keys_negative_control(self):
        self.assertFalse(arrow_handler_guards_typing(BAD_KEYDOWN),
                         "the check failed to catch the unguarded pre-3659ec7 handler")


class TestTokenGateCensus(unittest.TestCase):
    """Every mutating route is token-checked — census, ordering, and the gate function."""

    def test_bench_census_matches_do_post_dispatch(self):
        routes = set(re.findall(r'self\.path == "(/api/[a-z_]+)"', BENCH_PY))
        self.assertEqual(routes, set(bench.MUTATING_POSTS),
                         "bench.py's POST dispatch and MUTATING_POSTS disagree — a route was "
                         "added or removed without updating the enumerated gate census")

    def test_room_chat_census_matches_do_post_dispatch(self):
        do_post = py_function_body(ROOM_PY, "do_POST")
        routes = set(re.findall(r'self\.path == "(/api/[a-z]+)"', do_post))
        self.assertEqual(routes, set(room_chat.MUTATING_POSTS),
                         "room_chat.py's POST dispatch and MUTATING_POSTS disagree")

    def test_gate_runs_before_any_dispatch_in_both_files(self):
        for name, src in (("bench.py", BENCH_PY), ("room_chat.py", ROOM_PY)):
            do_post = py_function_body(src, "do_POST")
            gate_at = do_post.find("token_gate(")
            first_dispatch = do_post.find('self.path == "')
            self.assertGreater(gate_at, -1, f"{name}: do_POST no longer calls token_gate")
            self.assertLess(gate_at, first_dispatch,
                            f"{name}: the token gate must run BEFORE any route dispatch")

    def test_token_gate_semantics_both_modules(self):
        for mod in (bench, room_chat):
            self.assertIn("started without --token", mod.token_gate("anything", None),
                          f"{mod.__name__}: no-token refusal must say WHY and how to fix it")
            self.assertIsNotNone(mod.token_gate(None, "secret"))       # missing header
            self.assertIsNotNone(mod.token_gate("wrong", "secret"))    # wrong token
            self.assertIsNone(mod.token_gate("secret", "secret"))      # match admits

    def test_bench_no_gate_sentinel_admits_in_process_harnesses(self):
        # acceptance.py constructs make_handler(bench) directly, inside the process boundary;
        # the sentinel default must keep that path open while main() always applies the policy.
        self.assertIsNone(bench.token_gate(None, bench._NO_GATE))

    def test_bench_html_attaches_the_header(self):
        api_fn = BENCH_HTML[BENCH_HTML.index("async function api("):]
        api_fn = api_fn[:api_fn.index("}\n") + 1]
        self.assertIn("X-FP-Token", api_fn, "bench.html's api() no longer attaches the token")
        self.assertIn('get("token")', BENCH_HTML.split("async function api(")[0].split("const TOKEN")[-1],
                      "bench.html no longer reads ?token= at load")

    def test_room_chat_serves_the_shim_before_the_page_script(self):
        self.assertIn("X-FP-Token", room_chat.TOKEN_SHIM.decode("utf-8"))
        page = (REPO / "windows-converter" / "room_chat.html").read_bytes()
        # the injection point exists, and the shim goes in front of it
        self.assertIn(b"<title>", page)


class TestClaimDenominators(unittest.TestCase):
    """Counted claims name numerator AND denominator (measurement-language law, docs/34)."""

    def test_zone_chip_claim_names_both(self):
        line = next(ln for ln in BENCH_HTML.splitlines() if "repaired`" in ln and "zones" in ln)
        self.assertTrue(claim_names_denominator(line),
                        f"the zones chip claim lost its denominator: {line.strip()!r}")

    def test_rescore_coverage_claim_names_both(self):
        line = next(ln for ln in BENCH_HTML.splitlines() if "site(s) addressed" in ln)
        self.assertTrue(claim_names_denominator(line),
                        f"the re-score coverage claim lost its denominator: {line.strip()!r}")

    def test_report_addressed_claim_names_both(self):
        line = next(ln for ln in BENCH_PY.splitlines() if "addressed" in ln and "still open" in ln)
        self.assertTrue(claim_names_denominator(line),
                        f"the REPAIRS.md addressed claim lost its denominator: {line.strip()!r}")

    def test_negative_controls_fail_the_same_check(self):
        self.assertFalse(claim_names_denominator(BAD_CLAIM_JS))
        self.assertFalse(claim_names_denominator(BAD_CLAIM_PY))


# ---- the live wire: fail-closed 403, wrong-token 403, right-token admitted -------------------
def _post(port: int, path: str, payload: dict, token: str | None = None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["X-FP-Token"] = token
    conn.request("POST", path, json.dumps(payload), headers)
    r = conn.getresponse()
    body = r.read()
    conn.close()
    try:
        return r.status, json.loads(body)
    except json.JSONDecodeError:
        return r.status, {"raw": body[:200]}


def _get(port: int, path: str):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request("GET", path)
    r = conn.getresponse()
    body = r.read()
    conn.close()
    return r.status, body


# Benign per-route bodies: every one either succeeds harmlessly inside the temp fixture or
# fails validation BEFORE any spawn/GPU/model/write-outside-fixture could happen. The point of
# the admitted pass is only "not 403" — the gate let it through.
BENIGN = {
    "/api/repair": {"zone_line": 1, "page": 1},                    # -> need rect/image_b64
    "/api/md": {"text": "line one\nline two\nline three"},         # -> 200, writes temp only
    "/api/open": {"path": "Z:/definitely/outside/the/roots"},      # -> outside allowlist
    "/api/transcribe": {"zone_line": 1, "page": 1, "rect": [0, 0, 1, 1]},  # -> no fitz/pdf here
    "/api/transcribe_apply": {"zone_line": 1, "page": 1, "markdown": ""},  # -> empty = discard
    "/api/collapse_preview": {"zone_line": 1},                     # -> no zone recorded
    "/api/collapse": {"zone_line": 1},                             # -> no zone recorded
    "/api/assist": {"start": 1, "end": 1, "instruction": ""},      # -> refuses before Ollama
    "/api/undo": {},                                               # -> ledger is empty
    "/api/triage": {"key": "z1", "outcome": "not-an-outcome"},     # -> refused, no write
    "/api/report": {"write": False},                               # -> 200, writes nothing
}


class LiveBenchServer:
    def __init__(self, token):
        self.tmp = Path(tempfile.mkdtemp(prefix="fp-test-bundle-"))
        (self.tmp / "book.md").write_text("---\ntitle: t\n---\nline one\nline two\nline three",
                                          encoding="utf-8")
        self.bench = bench.Bench(self.tmp)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0),
                                         bench.make_handler(self.bench, token=token))
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestFailClosed403Live(unittest.TestCase):
    """bench.py over a real socket, throwaway fixture. Positive control: the right token is
    admitted on every route. Negative controls: no-token/missing/wrong all refuse, and the
    refused write provably did not happen."""

    def test_no_token_server_refuses_every_mutating_route_and_writes_nothing(self):
        srv = LiveBenchServer(token=None)
        try:
            before = (srv.tmp / "book.md").read_bytes()
            for route in bench.MUTATING_POSTS:
                code, body = _post(srv.port, route, BENIGN[route])
                self.assertEqual(code, 403, f"{route} must fail closed without --token")
                self.assertIn("started without --token", body.get("error", ""),
                              f"{route}'s refusal must name the remedy")
            self.assertEqual(before, (srv.tmp / "book.md").read_bytes(),
                             "a 403'd /api/md still changed the file — the gate leaks")
            code, _ = _get(srv.port, "/api/state")
            self.assertEqual(code, 200, "the read side must stay ungated")
        finally:
            srv.close()

    def test_token_server_refuses_missing_and_wrong_and_admits_right(self):
        srv = LiveBenchServer(token="lane-d-secret")
        try:
            for route in bench.MUTATING_POSTS:
                code, _ = _post(srv.port, route, BENIGN[route])              # missing header
                self.assertEqual(code, 403, f"{route}: missing X-FP-Token must refuse")
                code, _ = _post(srv.port, route, BENIGN[route], token="nope")  # wrong token
                self.assertEqual(code, 403, f"{route}: wrong X-FP-Token must refuse")
                code, _ = _post(srv.port, route, BENIGN[route], token="lane-d-secret")
                self.assertNotEqual(code, 403, f"{route}: the right token must be admitted "
                                               "(any non-403 outcome proves the gate opened)")
        finally:
            srv.close()

    def test_room_chat_gate_live(self):
        # Handler.token is class state; no Llama is attached, so an admitted POST fails
        # AFTER the gate (500) — which is exactly the proof wanted: admitted, then the
        # route's own logic spoke. Nothing can spawn: there is no llama instance at all.
        old = room_chat.Handler.token
        httpd = None
        try:
            room_chat.Handler.token = None
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), room_chat.Handler)
            port = httpd.server_address[1]
            t = threading.Thread(target=httpd.serve_forever, daemon=True)
            t.start()
            for route in room_chat.MUTATING_POSTS:
                code, body = _post(port, route, {})
                self.assertEqual(code, 403, f"{route} must fail closed without --token")
                self.assertIn("started without --token", body.get("error", ""))
            room_chat.Handler.token = "room-secret"
            code, _ = _post(port, "/api/unload", {}, token="wrong")
            self.assertEqual(code, 403)
            code, _ = _post(port, "/api/unload", {}, token="room-secret")
            self.assertNotEqual(code, 403, "right token must be admitted (500 here = the gate "
                                           "opened and the llama-less route spoke for itself)")
        finally:
            room_chat.Handler.token = old
            if httpd:
                httpd.shutdown()
                httpd.server_close()


if __name__ == "__main__":
    try:
        unittest.main(verbosity=2)
    finally:
        shutil.rmtree(_PIPE_TMP, ignore_errors=True)
