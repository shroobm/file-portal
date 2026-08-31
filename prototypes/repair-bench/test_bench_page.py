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

import base64
import http.client
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import time
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


def _get(port: int, path: str, token: str | None = None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    headers = {"X-FP-Token": token} if token is not None else {}
    conn.request("GET", path, headers=headers)
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
            code, _ = _get(srv.port, "/api/evidence")
            self.assertEqual(code, 403, "the expensive evidence GET must fail closed")
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
            self.assertEqual(403, _get(srv.port, "/api/evidence")[0])
            self.assertEqual(403, _get(srv.port, "/api/evidence", token="nope")[0])
            self.assertNotEqual(403, _get(srv.port, "/api/evidence",
                                          token="lane-d-secret")[0])
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


# ---- OK-0 / OK-1 / OK-2 / OK-7 (docs/49, signed by Rab 2026-08-30) — the tripwires land in
# the same commit as the guards they watch (docs/32 §6), same idiom as above: every family
# carries a positive control against the real artifact and a negative control that the same
# check REJECTS.
class TestOK0RepairIdentity(unittest.TestCase):
    """OK-0: every NEW repair record carries a UUID identity; old records are never rewritten."""

    ID_RE = re.compile(r"^fpr-[0-9a-f]{32}$")

    def test_new_records_get_unique_ids_and_legacy_records_stay_untouched(self):
        tmp = Path(tempfile.mkdtemp(prefix="fp-test-ok0-"))
        try:
            (tmp / "book.md").write_text("---\nt: 1\n---\nalpha\nbeta\ngamma",
                                         encoding="utf-8")
            legacy = {"ts": "2026-08-01T00:00:00+00:00", "zone_line": 1, "mode": "paste"}
            (tmp / "manifest.json").write_text(json.dumps({"repairs": [legacy]}),
                                               encoding="utf-8")
            b = bench.Bench(tmp)
            png_b64 = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"x" * 24).decode()
            r1 = b.repair(zone_line=1, page=1, image_b64=png_b64)
            r2 = b.repair(zone_line=2, page=1, image_b64=png_b64)
            self.assertRegex(r1["record"]["id"], self.ID_RE)
            self.assertRegex(r2["record"]["id"], self.ID_RE)
            self.assertNotEqual(r1["record"]["id"], r2["record"]["id"],
                                "two repairs share one id — identity is not identity")
            reps = json.loads((tmp / "manifest.json").read_text(encoding="utf-8"))["repairs"]
            self.assertEqual(len(reps), 3)
            self.assertNotIn("id", reps[0],
                             "a legacy record grew an id — append-only means old records "
                             "are never rewritten, not even helpfully")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_negative_control_the_predicate_rejects_non_ids(self):
        for bad in ("", "fpr-nothex", "fpr-" + "a" * 31, "okular-123"):
            self.assertIsNone(self.ID_RE.match(bad),
                              f"the id predicate admitted {bad!r}")


class TestOK5TextLayer(unittest.TestCase):
    """OK-5: the text layer's pure math + its LRU discipline, stdlib-only (the OK-7 pattern —
    the fitz call is one line; everything testable lives outside it)."""

    def test_normalize_clamps_rounds_and_drops_junk(self):
        words = bench.Bench.normalize_words(
            [(10, 20, 110, 40, "alpha", 0, 0, 0),
             (-5, -5, 700, 900, "overflow"),          # clamps to 0..1, never beyond
             (10, 10, 20, 20, "   "),                  # whitespace word dropped
             ("bad",),                                 # malformed tuple dropped, not fatal
             (50, 50, 60, 60, "beta")],
            width=500, height=800)
        self.assertEqual([w[4] for w in words], ["alpha", "overflow", "beta"])
        self.assertEqual(words[0][:4], [0.02, 0.025, 0.22, 0.05])
        self.assertEqual(words[1][:4], [0.0, 0.0, 1.0, 1.0])
        for w in words:
            for v in w[:4]:
                self.assertTrue(0.0 <= v <= 1.0, f"{v} escaped the page")

    def test_degenerate_geometry_is_an_empty_layer_not_a_crash(self):
        self.assertEqual(bench.Bench.normalize_words([(1, 1, 2, 2, "x")], 0, 100), [])
        self.assertEqual(bench.Bench.normalize_words([(1, 1, 2, 2, "x")], 100, -3), [])

    def _bench_with_fake_doc(self, pages=40):
        tmp = Path(tempfile.mkdtemp(prefix="fp-test-ok5-"))
        (tmp / "book.md").write_text("---\nt: 1\n---\nalpha", encoding="utf-8")
        b = bench.Bench(tmp)

        class FakeRect:
            width, height = 500.0, 800.0

        class FakePage:
            rect = FakeRect()

            def __init__(self, n):
                self.n = n

            def get_text(self, kind):
                return [(10, 10, 90, 30, f"word-p{self.n}")]

        class FakeDoc:
            page_count = pages

            def load_page(self, i):
                return FakePage(i + 1)

        b.pdf = tmp / "book.pdf"  # doc()'s no-PDF guard checks presence, not bytes
        b._doc = FakeDoc()
        return b, tmp

    def test_lazy_lru_bounded_and_refreshed(self):
        b, tmp = self._bench_with_fake_doc()
        try:
            first = b.textlayer(1)
            self.assertEqual(first["words"][0][4], "word-p1")
            self.assertTrue(first["searchable"])
            for n in range(2, 2 + bench.Bench.TEXTLAYER_LRU):
                b.textlayer(n)
            b.textlayer(1)  # refresh page 1 — it must now be the NEWEST, not the oldest
            b.textlayer(99)  # one past the cap evicts the true oldest (page 2), never page 1
            self.assertIn(1, b._textlayer, "LRU refresh did not protect the re-read page")
            self.assertNotIn(2, b._textlayer, "the oldest page was not the one evicted")
            self.assertLessEqual(len(b._textlayer), bench.Bench.TEXTLAYER_LRU,
                                 "the layer cache grew past its bound")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_page_number_is_clamped_to_the_book(self):
        b, tmp = self._bench_with_fake_doc(pages=3)
        try:
            self.assertEqual(b.textlayer(0)["page"], 1)
            self.assertEqual(b.textlayer(99)["page"], 3)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_textlayer_route_is_read_only_get_never_a_mutating_post(self):
        src = (Path(__file__).parent / "bench.py").read_text(encoding="utf-8")
        self.assertIn('"/api/textlayer"', src)
        get_part = src[src.index("def do_GET"):src.index("def do_POST")]
        self.assertIn("/api/textlayer", get_part, "textlayer must be a GET route")
        self.assertNotIn("/api/textlayer", src[src.index("MUTATING_POSTS"):src.index("def make_handler")],
                         "textlayer may never join the mutating POST census")

    def test_client_layer_exists_with_eviction_and_alt_gate(self):
        html = (Path(__file__).parent / "bench.html").read_text(encoding="utf-8")
        self.assertIn("/api/textlayer?n=", html, "client never fetches the layer")
        self.assertIn("wordsInRect", html)
        self.assertIn("this.cache.delete(this.cache.keys().next().value)", html,
                      "client cache has no eviction — a long session hoards the book")
        self.assertIn("drag.alt", html, "Alt+drag selection is not gated on the modifier")


class TestOK4SearchSuite(unittest.TestCase):
    """OK-4: the hyphenation-aware matcher (pure) + the client suite's presence census."""

    W = 0.02  # a word box helper: y row r, x slot c

    def _w(self, c, r, text):
        return [c * 0.1, r * 0.1, c * 0.1 + 0.08, r * 0.1 + 0.03, text]

    def test_hyphen_split_across_lines_matches_and_boxes_per_line(self):
        words = [self._w(0, 0, "smart"), self._w(1, 0, "invest-"),
                 self._w(0, 1, "ment"), self._w(1, 1, "works")]
        boxes = bench.Bench.match_in_words(words, "investment")
        self.assertEqual(len(boxes), 2, "a line-crossing match must yield one box PER line")
        self.assertAlmostEqual(boxes[0][1], 0.0, places=5)
        self.assertAlmostEqual(boxes[1][1], 0.1, places=5)

    def test_ligature_query_matches_via_nfkc(self):
        words = [self._w(0, 0, "ﬁnance")]  # PDF's ﬁ ligature
        self.assertEqual(len(bench.Bench.match_in_words(words, "finance")), 1)

    def test_multiword_and_multiple_occurrences(self):
        words = [self._w(0, 0, "cash"), self._w(1, 0, "flow"), self._w(2, 0, "and"),
                 self._w(0, 1, "cash"), self._w(1, 1, "flow")]
        self.assertEqual(len(bench.Bench.match_in_words(words, "cash flow")), 2)

    def test_negative_control_absent_text_is_an_honest_empty(self):
        words = [self._w(0, 0, "alpha"), self._w(1, 0, "beta")]
        self.assertEqual(bench.Bench.match_in_words(words, "gamma"), [])
        self.assertEqual(bench.Bench.match_in_words([], "gamma"), [])
        self.assertEqual(bench.Bench.match_in_words(words, "   "), [])

    def test_hyphen_only_word_is_not_a_glue_trap(self):
        # a bare "-" word must not silently weld its neighbours into one token
        words = [self._w(0, 0, "a"), self._w(1, 0, "-"), self._w(2, 0, "b")]
        self.assertEqual(bench.Bench.match_in_words(words, "ab"), [],
                         "the lone hyphen glued two words that are not one")

    def test_client_suite_census(self):
        html = (Path(__file__).parent / "bench.html").read_text(encoding="utf-8")
        for needle, why in [
            ("SEARCH_DEBOUNCE_MS = 700", "the 700 ms typeahead constant"),
            ("gen !== searchGen", "the request-generation staleness guard"),
            ("mix-blend-mode:multiply", "multiply-blend highlights"),
            ("wrapped to the first hit", "the wrap toast"),
            ("p === page", "the no-jump rule (same page never yanks the view)"),
            ("q-miss", "the zero-hit red field"),
            ("q-busy", "the in-flight spinner state"),
            ("applyRailFilter", "thumbnail-rail hit filtering"),
        ]:
            self.assertIn(needle, html, f"OK-4 client census missing: {why}")

    def test_server_rects_falls_back_to_the_word_stream(self):
        src = (Path(__file__).parent / "bench.py").read_text(encoding="utf-8")
        at = src.index("def rects(")
        self.assertIn("match_in_words", src[at:at + 1400],
                      "rects() no longer consults the hyphenation-aware fallback")


class TestOK6TableTool(unittest.TestCase):
    """OK-6: divider guessing, central-pixel bucketing, the char-split repair for words that
    cross a divider (the audit's words-only failure), and pipe-safety — all pure."""

    def test_divider_guessing_finds_the_valleys_and_ignores_noise(self):
        # two columns of ink: 0.1-0.3 and 0.5-0.8 → one divider at the gap's middle
        divs = bench.Bench.guess_dividers([(0.1, 0.2), (0.15, 0.3), (0.5, 0.7), (0.6, 0.8)],
                                          0.05, 0.9)
        self.assertEqual(divs, [0.4])
        # a sub-threshold gap is texture, not a column boundary
        self.assertEqual(bench.Bench.guess_dividers([(0.1, 0.3), (0.302, 0.5)], 0.0, 0.6), [])

    def test_central_pixel_bucketing_builds_the_grid(self):
        words = [[0.10, 0.10, 0.20, 0.14, "name"], [0.60, 0.10, 0.70, 0.14, "value"],
                 [0.10, 0.30, 0.22, 0.34, "cash"], [0.60, 0.30, 0.72, 0.34, "42"]]
        cells = bench.Bench.bucket_cells(words, [], [0.05, 0.05, 0.95, 0.40],
                                         col_divs=[0.45], row_divs=[0.22])
        self.assertEqual(cells, [["name", "value"], ["cash", "42"]])
        md = bench.Bench.table_markdown(cells)
        self.assertIn("| name | value |", md)
        self.assertIn("| --- | --- |", md.replace("| --- ", "| --- "))
        self.assertIn("| cash | 42 |", md)

    def test_word_crossing_a_divider_is_split_by_its_chars(self):
        # ONE word "AB12" straddles the divider at 0.5 — words-only would dump it whole into
        # the left cell; the chars pull "AB" left and "12" right (the audit's exact case)
        word = [[0.40, 0.10, 0.60, 0.14, "AB12"]]
        chars = [[0.40, 0.10, 0.45, 0.14, "A"], [0.45, 0.10, 0.49, 0.14, "B"],
                 [0.51, 0.10, 0.55, 0.14, "1"], [0.55, 0.10, 0.60, 0.14, "2"]]
        cells = bench.Bench.bucket_cells(word, chars, [0.3, 0.05, 0.9, 0.2],
                                         col_divs=[0.5], row_divs=[])
        self.assertEqual(cells, [["AB", "12"]])

    def test_words_only_fallback_when_no_chars_supplied(self):
        # center 0.48 — clearly left of the 0.5 divider (a dead-center tie is degenerate
        # and may land either side; the contract is center-bucketing, not tie-breaking)
        word = [[0.40, 0.10, 0.56, 0.14, "AB12"]]
        cells = bench.Bench.bucket_cells(word, [], [0.3, 0.05, 0.9, 0.2],
                                         col_divs=[0.5], row_divs=[])
        self.assertEqual(cells, [["AB12", ""]],
                         "without chars the whole word lands by its center — degraded, "
                         "never invented")

    def test_pipes_in_cell_text_are_escaped(self):
        cells = bench.Bench.bucket_cells([[0.1, 0.1, 0.2, 0.14, "a|b"]], [],
                                         [0.0, 0.0, 1.0, 1.0], [], [])
        self.assertEqual(cells[0][0], "a\\|b", "an unescaped pipe eats the table's own syntax")

    def test_review_fixes_2026_08_31(self):
        """The three-lens review's confirmed findings, pinned so they cannot return."""
        # CRITICAL: chars at a 5-decimal-rounded word edge must survive containment
        word = [[round(0.400004, 5), 0.10, round(0.599996, 5), 0.14, "AB12"]]
        chars = [[0.400004, 0.10, 0.45, 0.14, "A"], [0.45, 0.10, 0.499, 0.14, "B"],
                 [0.51, 0.10, 0.55, 0.14, "1"], [0.55, 0.10, 0.599996, 0.14, "2"]]
        cells = bench.Bench.bucket_cells(word, chars, [0.3, 0.05, 0.9, 0.2], [0.5], [])
        self.assertEqual(cells, [["AB", "12"]],
                         "rounding ate a boundary char — the epsilon regressed below 5e-6")
        # overlap advance: a self-overlapping query yields non-overlapping occurrences
        w = [[i * 0.1, 0.1, i * 0.1 + 0.08, 0.14, "no"] for i in range(3)]
        self.assertEqual(len(bench.Bench.match_in_words(w, "no no")), 1,
                         "overlapping matches are back — the scan advances by +1 again")
        # the divider-delete sentinel + rect arity guard live in the route
        src = (Path(__file__).parent / "bench.py").read_text(encoding="utf-8")
        self.assertIn('"none"', src[src.index("/api/table"):src.index("/api/table") + 900],
                      "deleting the LAST divider has no wire format again")
        self.assertIn("rect needs 4 numbers", src, "the rect arity guard is gone")
        html = (Path(__file__).parent / "bench.html").read_text(encoding="utf-8")
        self.assertIn("const tRect = crop;", html,
                      "the null-rect CRITICAL: capture the rect BEFORE clearCrop")
        self.assertIn("textLayer.cache.clear()", html,
                      "book switch no longer drops the page-keyed text layer cache")
        self.assertIn("hlQuery === asked && page === askedPage", html,
                      "the deferred place listener lost its staleness guard")

    def test_client_table_census(self):
        html = (Path(__file__).parent / "bench.html").read_text(encoding="utf-8")
        for needle, why in [
            ('id="tablebtn"', "the arming button"),
            ("3 / (isRow ? r.height : r.width)", "the 3 px snap in page fractions"),
            ("tableCorrect", "click-to-correct wiring"),
            ("tpcopy", "the copy control"),
            ("!tableMode", "the reading-mode gate pass-through"),
        ]:
            self.assertIn(needle, html, f"OK-6 client census missing: {why}")


class TestOK8ZoomAndOK12Grammar(unittest.TestCase):
    """OK-8 + OK-12: presence census over the client surface (the logic is DOM-bound; the
    census pins every named behavior so a refactor cannot silently drop one)."""

    def test_ok8_census(self):
        html = (Path(__file__).parent / "bench.html").read_text(encoding="utf-8")
        for needle, why in [
            ('value="fitpage"', "fit-page spliced into the zoom ladder"),
            ("targetWidth(z) / 7.5", "the computed-dpi one-liner"),
            ("wTarget = targetWidth(z)", "layout and dpi share one width source"),
            ("dpi=300", "the loupe's high-dpi request"),
            ("invert(92%) hue-rotate(180deg)", "night recolor as CSS post-raster"),
            ('id="loupebtn"', "the loupe control"),
        ]:
            self.assertIn(needle, html, f"OK-8 census missing: {why}")
        self.assertNotIn("? 140 : 220", html, "the old two-rung dpi ladder is still wired")

    def test_ok12_census(self):
        html = (Path(__file__).parent / "bench.html").read_text(encoding="utf-8")
        for needle, why in [
            ("2500 + m.length * 35", "length-proportional toast timeouts"),
            ('sev === "error"', "the error rung sticks (modal-fallback)"),
            ("sev-warn", "the warn rung's face"),
            ("function modePin", "pinned mode-instruction toasts"),
            ("const modePins", "per-mode pin registry (one disarm never erases another's pin)"),
            ('modePin("table", null)', "a disarmed mode clears ITS OWN pin"),
        ]:
            self.assertIn(needle, html, f"OK-12 census missing: {why}")
        # legacy contract: status(m, true) must still read as sticky
        self.assertIn("{ sticky: opt }", html, "the legacy boolean-sticky caller broke")


class TestOK7TrimBox(unittest.TestCase):
    """OK-7: the trim measurement, pure and stdlib-only — Okular's 4%-pad and half-page-floor
    constants, exercised both ways."""

    @staticmethod
    def raster(w, h, paper=(250, 250, 248), content_rect=None):
        buf = bytearray()
        for y in range(h):
            for x in range(w):
                inside = content_rect and (content_rect[0] <= x < content_rect[2]
                                           and content_rect[1] <= y < content_rect[3])
                buf.extend((20, 20, 20) if inside else paper)
        return bytes(buf), w * 3

    def test_blank_page_yields_none_not_a_phantom_box(self):
        s, stride = self.raster(60, 90)
        self.assertIsNone(bench.Bench.bbox_from_samples(s, 60, 90, stride))

    def test_content_box_found_then_padded_and_capped(self):
        s, stride = self.raster(100, 100, content_rect=(30, 40, 70, 80))
        tight = bench.Bench.bbox_from_samples(s, 100, 100, stride)
        self.assertAlmostEqual(tight[0], 0.30, places=2)
        self.assertAlmostEqual(tight[2], 0.70, places=2)
        self.assertAlmostEqual(tight[3], 0.80, places=2)
        padded = bench.Bench.pad_and_cap(tight)
        self.assertLess(padded[0], tight[0], "the 4% pad must expand the box, not shrink it")
        self.assertGreater(padded[2], tight[2])
        # the half-page floor: a tiny stamp must not crop the page down to itself
        capped = bench.Bench.pad_and_cap([0.48, 0.48, 0.52, 0.52])
        self.assertGreaterEqual(capped[2] - capped[0], bench.Bench.TRIM_MIN_KEEP - 1e-9)
        self.assertGreaterEqual(capped[3] - capped[1], bench.Bench.TRIM_MIN_KEEP - 1e-9)
        for v in capped:
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)

    def test_negative_control_content_at_the_edge_defeats_the_crop_honestly(self):
        # content touching row 0 (a header bleed, a scanner border): top must be 0 — the
        # measurement reports what is there rather than inventing a margin
        s, stride = self.raster(60, 60, content_rect=(0, 0, 60, 2))
        box = bench.Bench.bbox_from_samples(s, 60, 60, stride)
        self.assertLessEqual(box[1], 0.01)

    def test_paper_estimate_survives_one_dark_corner(self):
        # a photo block covering the top-left corner must not poison the paper estimate
        s, stride = self.raster(80, 80, content_rect=(0, 0, 20, 20))
        box = bench.Bench.bbox_from_samples(s, 80, 80, stride)
        self.assertIsNotNone(box, "one dark corner made the whole page read as paper")
        self.assertLessEqual(box[0], 0.01)
        self.assertLessEqual(box[1], 0.01)

    def test_trimbox_route_is_read_only_get_never_a_mutating_post(self):
        self.assertIn('"/api/trimbox"', BENCH_PY)
        self.assertNotIn("/api/trimbox", bench.MUTATING_POSTS,
                         "trimbox computes and caches — it must never join the mutating census")


class TestOK1ViewportSource(unittest.TestCase):
    """OK-1 source truths in bench.html: stable-id keying, the overwrite-on-same-page history
    rule, and restore winning over the zone-0 auto-jump."""

    def test_view_store_keys_on_the_stable_source_id_first(self):
        body = js_function_body(BENCH_HTML, "viewStoreKey")
        self.assertIn("source_sha16", body,
                      "the view store no longer keys on the stable source id — a pipeline "
                      "rewrite would orphan the reader's position (the audited size-key hazard)")
        # review 2026-08-30: in pdf_only mode s.bundle is the containing FOLDER — the PDF
        # name must outrank it or every bare PDF in done/ shares one store
        self.assertIn("pdf_only", body,
                      "viewStoreKey lost its pdf_only branch — every bare PDF in one folder "
                      "would share a single view store (marks/position/trim cross-pollution)")

    def test_reader_mode_gets_a_real_identity_from_the_pdf_bytes(self):
        tmp = Path(tempfile.mkdtemp(prefix="fp-test-viewid-"))
        try:
            a, b = tmp / "bookA.pdf", tmp / "bookB.pdf"
            a.write_bytes(b"%PDF-1.4 fake A " + b"a" * 100)
            b.write_bytes(b"%PDF-1.4 fake B " + b"b" * 100)
            ida = bench.Bench(a).state()["source_sha16"]
            idb = bench.Bench(b).state()["source_sha16"]
            self.assertRegex(ida, r"^[0-9a-f]{16}$")
            self.assertNotEqual(ida, idb,
                                "two different PDFs share one view identity — the exact "
                                "cross-book pollution the review reproduced")
            self.assertEqual(ida, bench.Bench(a).state()["source_sha16"],
                             "the identity is not stable across re-opens")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_history_overwrites_same_page_and_caps_at_100(self):
        body = js_function_body(BENCH_HTML, "histRecord")
        self.assertIn(".page === vp.page", body, "the same-page overwrite branch is gone — "
                      "plain scrolling would spam the history")
        self.assertIn("100", body, "the in-RAM history cap is gone")
        self.assertIn("splice", body, "a page change no longer erases the forward tail")

    def test_persisted_history_is_the_last_ten(self):
        body = js_function_body(BENCH_HTML, "saveViewStore")
        self.assertIn("slice(-10)", body, "the persisted history is no longer capped at 10")

    def test_load_prefers_the_saved_place_over_the_zone_autojump(self):
        body = js_function_body(BENCH_HTML, "load")
        self.assertIn("restoreView(store)", body)
        self.assertLess(body.index("if (restoreView(store))"),
                        body.index("else if (st.zones.length) selectZone(0);"),
                        "load() auto-jumps to zone 0 before consulting the saved viewport")

    def test_negative_control_a_push_only_history_fails_the_same_checks(self):
        bad = "{ vhist.push(vp); vidx = vhist.length - 1; }"
        self.assertNotIn(".page === vp.page", bad)
        self.assertNotIn("100", bad)


class TestOK2PlaceholderSource(unittest.TestCase):
    """OK-2 source truths: goto routes through setPageImage, and the placeholder is DELAYED
    so fast loads never flash it."""

    def test_goto_routes_through_the_placeholder_path(self):
        body = js_function_body(BENCH_HTML, "goto")
        self.assertIn("setPageImage(", body)
        self.assertNotIn('pageimg").src', body,
                         "goto sets img.src directly — the placeholder path is bypassed")

    def test_placeholder_only_appears_inside_the_delay_callback(self):
        body = js_function_body(BENCH_HTML, "setPageImage")
        self.assertIn("setTimeout", body)
        at_timer = body.index("setTimeout")
        self.assertIn("hidden = false", body[at_timer:],
                      "nothing un-hides the placeholder inside the delay callback")
        self.assertNotIn("hidden = false", body[:at_timer],
                         "the placeholder shows before the delay — fast pages pay the flash")

    def test_negative_control_an_immediate_placeholder_fails_the_same_check(self):
        bad = '{ ph.hidden = false; setTimeout(() => {}, 120); img.src = url; }'
        at_timer = bad.index("setTimeout")
        self.assertIn("hidden = false", bad[:at_timer])

    def test_overlays_ride_the_image_inside_pageinner(self):
        # OK-7's CSS crop shifts #pageinner; highlights must live there or trim would strand them
        self.assertIn('id="pageinner"', BENCH_HTML)
        self.assertIn('$("pageinner").appendChild', BENCH_HTML,
                      "highlight boxes no longer land in #pageinner — a trim crop would "
                      "leave them anchored to the clipped container instead of the image")


def css_hidden_override_present(css: str, ident: str) -> bool:
    """True = the stylesheet carries a `#ident[hidden]` display:none override. Required for
    any id that BOTH declares an author `display` AND is toggled via .hidden from JS — the
    author declaration beats the UA [hidden] rule in the cascade (review CRITICAL 2026-08-30;
    .modal[hidden] at the top of the file is the in-file precedent)."""
    return bool(re.search(rf"#{ident}\[hidden\][^{{]*{{[^}}]*display\s*:\s*none", css))


class TestReviewFixes(unittest.TestCase):
    """The 2026-08-30 three-lens review's confirmed findings, pinned so they cannot return."""

    def test_pagephold_hidden_override_exists(self):
        self.assertTrue(css_hidden_override_present(BENCH_HTML, "pagephold"),
                        "#pagephold[hidden]{display:none} is gone — with an author "
                        "display:block, ph.hidden=true is a NO-OP and the dpi-30 placeholder "
                        "stays painted over every subsequent page (review CRITICAL)")

    def test_pagephold_hidden_override_negative_control(self):
        bad = "#pagephold { position:absolute; display:block; }"
        self.assertFalse(css_hidden_override_present(bad, "pagephold"))

    def test_restored_load_still_binds_the_zone_context(self):
        body = js_function_body(BENCH_HTML, "load")
        self.assertIn("selectZone(0, true)", body,
                      "a restored view no longer binds zone context — zone stays null, "
                      "ctxRange falls to lines 1..40, and the next crop/✦ fix writes to the "
                      "front matter with note 'folder mode' (review CRITICAL)")
        sig = BENCH_HTML.index("function selectZone(")
        self.assertIn("keepView", BENCH_HTML[sig:sig + 60],
                      "selectZone lost its keepView parameter")

    def test_history_walk_never_overwrites_the_destination_entry(self):
        body = js_function_body(BENCH_HTML, "histRecord")
        self.assertRegex(body,
                         r"if \(navFromHist\) \{ navFromHist = false; saveViewStore\(\); "
                         r"histButtons\(\); return; \}",
                         "the navFromHist branch drifted — during a history walk the stored "
                         "entry is the authority; writing viewportNow() there destroys the "
                         "destination's scroll offset")

    def test_marks_key_on_identity_not_render_index(self):
        body = js_function_body(BENCH_HTML, "renderMarks")
        self.assertIn("findIndex", body)
        self.assertIn("dataset.ts", body,
                      "mark rows no longer resolve by ts identity — index-keyed deletion "
                      "made a double-click on ✕ delete TWO marks")
        self.assertNotIn("ondblclick", BENCH_HTML,
                         "dblclick is back — it always fires two clicks first, so rename "
                         "must stay on its own ✎ control")

    def test_trim_select_arms_with_a_clean_crop(self):
        at = BENCH_HTML.index('$("trimbtn").onclick')
        handler = BENCH_HTML[at:at + 700]
        self.assertIn("clearCrop()", handler,
                      "Shift+⛶ no longer clears the stale repair rect — a bare click after "
                      "arming would commit the previous crop as the global trim box")

    def test_alt_history_prevents_browser_back(self):
        handler = js_handler_around(BENCH_HTML, 'e.key === "ArrowLeft"')
        alt_at = handler.index("altKey")
        self.assertIn("preventDefault", handler[alt_at:alt_at + 120],
                      "Alt+←/→ no longer preventDefault — Alt+Left is the browser's Back")
        self.assertIn("beforeunload", BENCH_HTML,
                      "the beforeunload guard is gone — unsaved markdown edits die silently "
                      "on any navigation")

    def test_pad_and_cap_rejects_garbage_boxes(self):
        for bad in ([0.6, 0.6, 0.4, 0.4], [0.5, 0.5, 0.5, 0.5], [-0.1, 0, 0.5, 0.5]):
            with self.assertRaises(ValueError,
                                   msg=f"pad_and_cap answered confidently on garbage {bad}"):
                bench.Bench.pad_and_cap(bad)

    def test_trim_constants_are_live_at_their_call_sites(self):
        self.assertIn("self.pad_and_cap(box, self.TRIM_PAD, self.TRIM_MIN_KEEP)", BENCH_PY,
                      "pad_and_cap is called on frozen defaults — tuning Bench.TRIM_PAD "
                      "or TRIM_MIN_KEEP would silently do nothing")
        self.assertIn("self.TRIM_THRESHOLD)", BENCH_PY,
                      "bbox_from_samples is called on a frozen threshold")


class TestOK15EvidenceWiring(unittest.TestCase):
    """The collector has its own PyMuPDF harness; these pin its read-only Bench projection."""

    def test_evidence_route_is_get_only_and_never_mutating(self):
        self.assertIn('url.path == "/api/evidence"', BENCH_PY)
        self.assertNotIn("/api/evidence", bench.MUTATING_POSTS,
                         "OK-15 quarantine evidence must never become a write route")
        self.assertIn("never written into a bundle or manifest", BENCH_PY)
        branch = BENCH_PY[BENCH_PY.index('url.path == "/api/evidence"'):]
        branch = branch[:branch.index('elif url.path == "/api/toc"')]
        self.assertLess(branch.index("token_gate("), branch.index("ok15_evidence("),
                        "the expensive GET is reachable before its loopback capability gate")
        self.assertIn("_ok15_lock", BENCH_PY,
                      "concurrent evidence GETs can spawn duplicate full-book children")
        self.assertIn('options.headers = { "X-FP-Token": TOKEN }',
                      js_function_body(BENCH_HTML, "api"))

    def test_operator_surface_names_every_probe_and_its_non_gate(self):
        body = js_function_body(BENCH_HTML, "renderEvidence")
        for phrase in ["per-page MuPDF warnings", "logical labels", "order-only differences",
                       "all-OCG-off", "embedded /Thumb"]:
            self.assertIn(phrase, body, f"OK-15 surface stopped rendering {phrase}")
        self.assertIn("audit verdict, and pipeline stay unchanged", body)
        self.assertIn("evidenceUnreadSection(documentUnread, pageUnread)", body,
                      "partial evidence hides its explicit UNREAD reasons")
        unread = js_function_body(BENCH_HTML, "evidenceUnreadSection")
        self.assertIn("pageEntries.map", unread)
        self.assertNotIn("slice(0, 120)", unread,
                         "large damaged books still hide page-level UNREAD reasons")
        self.assertIn("ev-unread-list", unread,
                      "a complete large UNREAD list has no bounded scroll surface")
        self.assertIn("entry.reasons.length", unread,
                      "the UNREAD numerator counts pages instead of individual reasons")
        self.assertIn('id="evidence-retry"', body,
                      "a cached collection failure has no intentional operator retry")
        self.assertIn('?? "—"', body,
                      "an unavailable measurement renders as an invented clean zero")
        self.assertIn("data-page", js_function_body(BENCH_HTML, "evidenceSection"),
                      "suspect evidence pages are no longer navigable")

    def test_collection_failure_is_cached_and_retry_is_explicit(self):
        self.assertEqual(
            "RuntimeError: useful terminal reason",
            bench._last_process_diagnostic(
                "Traceback (most recent call last):\n  noisy stack frame\n"
                "RuntimeError: useful terminal reason\n"
            ),
        )
        tmp = Path(tempfile.mkdtemp(prefix="fp-test-ok15-failure-"))
        try:
            pdf = tmp / "broken.pdf"
            pdf.write_bytes(b"not a real PDF; identity-only state-machine fixture")
            patient = bench.Bench(pdf)
            calls = []

            def fail(actual):
                calls.append(actual)
                raise RuntimeError("synthetic permanent failure")

            patient._collect_ok15_evidence = fail
            first = patient.ok15_evidence()
            second = patient.ok15_evidence()
            self.assertEqual("UNREAD", first["status"])
            self.assertIs(first, second, "the same failure was paid for twice")
            self.assertEqual(1, len(calls))
            self.assertIsNone(first["summary"]["pages_total"])
            self.assertIn("synthetic permanent failure",
                          first["document"]["collection"]["reason"])
            self.assertTrue(first["document"]["collection"]["retryable"])

            patient._collect_ok15_evidence = lambda _actual: {"status": "measured"}
            retried = patient.ok15_evidence(retry=True)
            self.assertEqual("measured", retried["status"])
            self.assertIs(retried, patient.ok15_evidence())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_concurrent_collection_returns_in_progress_without_second_child(self):
        tmp = Path(tempfile.mkdtemp(prefix="fp-test-ok15-concurrent-"))
        try:
            pdf = tmp / "slow.pdf"
            pdf.write_bytes(b"identity-only concurrent state-machine fixture")
            patient = bench.Bench(pdf)
            started, release = threading.Event(), threading.Event()
            calls, result = [], {}

            def slow(actual):
                calls.append(actual)
                started.set()
                if not release.wait(2):
                    raise RuntimeError("test release never arrived")
                return {"status": "measured", "probe": "first child"}

            patient._collect_ok15_evidence = slow
            worker = threading.Thread(
                target=lambda: result.setdefault("report", patient.ok15_evidence()),
                daemon=True,
            )
            worker.start()
            self.assertTrue(started.wait(1), "first collector never entered")
            began = time.monotonic()
            in_progress = patient.ok15_evidence()
            elapsed = time.monotonic() - began
            self.assertEqual("IN-PROGRESS", in_progress["status"])
            self.assertLess(elapsed, 0.25, "concurrent GET silently blocked on the collector")
            self.assertEqual(1, len(calls), "a concurrent GET started a duplicate child")
            release.set()
            worker.join(2)
            self.assertFalse(worker.is_alive())
            self.assertEqual("first child", result["report"]["probe"])
            self.assertIs(result["report"], patient.ok15_evidence())
        finally:
            release.set()
            shutil.rmtree(tmp, ignore_errors=True)

    def test_page_labels_reach_toolbar_and_thumbnail_rail(self):
        goto = js_function_body(BENCH_HTML, "goto")
        thumbs = js_function_body(BENCH_HTML, "buildThumbs")
        self.assertIn("st.page_labels?.[page - 1]", goto)
        self.assertIn("label ${logical}", goto)
        self.assertIn("st.page_labels?.[n - 1]", thumbs)
        self.assertIn("or str(index + 1)", BENCH_PY,
                      "a PDF without label rules renders a blank logical label")
        # Negative control: an ordinal-only rail cannot pass the logical-label check.
        self.assertNotIn("page_labels", 'd.innerHTML = `<span class="tn">${n}</span>`;')


if __name__ == "__main__":
    try:
        unittest.main(verbosity=2)
    finally:
        shutil.rmtree(_PIPE_TMP, ignore_errors=True)
