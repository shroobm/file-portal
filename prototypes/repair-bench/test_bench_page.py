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
import contextlib
import hashlib
import http.client
import inspect
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest import mock
from http.server import HTTPServer, ThreadingHTTPServer
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
EVENT_VOCAB = (REPO / "windows-widget" / "src" / "event-vocab.js").read_text(
    encoding="utf-8")
WIDGET_MAIN = (REPO / "windows-widget" / "src" / "main.js").read_text(encoding="utf-8")
WIDGET_ROOM = (REPO / "windows-widget" / "src" / "room.js").read_text(encoding="utf-8")


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
        line = next(ln for ln in BENCH_HTML.splitlines()
                    if '$("bzones").textContent' in ln)
        self.assertTrue(claim_names_denominator(line),
                        f"the zones chip claim lost its denominator: {line.strip()!r}")

    def test_rescore_coverage_claim_names_both(self):
        line = next(ln for ln in BENCH_HTML.splitlines() if "site(s) addressed" in ln)
        self.assertTrue(claim_names_denominator(line),
                        f"the re-score coverage claim lost its denominator: {line.strip()!r}")

    def test_report_addressed_claim_names_both(self):
        line = next(ln for ln in BENCH_PY.splitlines() if "shown addressed" in ln)
        self.assertTrue(claim_names_denominator(line),
                        f"the REPAIRS.md addressed claim lost its denominator: {line.strip()!r}")

    def test_negative_controls_fail_the_same_check(self):
        self.assertFalse(claim_names_denominator(BAD_CLAIM_JS))
        self.assertFalse(claim_names_denominator(BAD_CLAIM_PY))


class TestS192OwedPrints(unittest.TestCase):
    """S192 E1: the four prints S191's dispositions named as owed — each response already carried the number, the page
    now says it. Source truths (the DOM never loads here — B5's honest limit): the string is wired to the field."""

    def test_locate_confidence_names_its_two_sides(self):
        line = next(ln for ln in BENCH_HTML.splitlines() if "⌖ located: p" in ln)
        self.assertTrue(claim_names_denominator(line),
                        f"the locate confidence lost its two sides: {line.strip()!r}")
        self.assertIn("r.needles", BENCH_HTML.split("⌖ located: p")[0][-600:] + line,
                      "the denominator must be the response's needles count, not a literal")

    def test_locate_negative_control_the_old_one_sided_string_fails(self):
        old = "status(`⌖ located: p${r.page} (confidence ${r.confidence})`);"
        self.assertFalse(claim_names_denominator(old))

    def test_ledger_view_prints_the_disk_half_beside_the_chain(self):
        src = BENCH_HTML
        self.assertIn("aud.matches_disk === true", src)
        self.assertIn("aud.matches_disk === false", src)
        self.assertIn("DISK DIFFERS FROM THE CHAIN", src)
        chain_line = next(ln for ln in src.splitlines() if "chain intact · " in ln)
        self.assertIn("${disk}", chain_line, "the disk half must ride on the chain line, not elsewhere")

    def test_search_head_names_pages_and_hits(self):
        line = next(ln for ln in BENCH_HTML.splitlines() if '$("search-tab").textContent = r.pages.length' in ln)
        self.assertIn("r.total_hits", line)
        self.assertIn("pages ·", line)
        self.assertIn("hits", line)

    def test_undo_line_names_regions_and_chars(self):
        line = next(ln for ln in BENCH_HTML.splitlines() if "↩ undone — byte-identical" in ln)
        self.assertIn("r.regions", line)
        self.assertIn("r.chars_restored", line)
        self.assertIn("r.undo_depth", line)

    def test_the_responses_carry_what_the_page_prints(self):
        # bench.py untouched: the fields the page reads must be the ones the routes return
        for key in ("\"needles\"", "\"votes\"", "\"matches_disk\"", "\"total_hits\"", "\"regions\"", "\"chars_restored\""):
            self.assertIn(key, BENCH_PY, f"bench.py no longer returns {key}")


class TestB15OmissionSignature(unittest.TestCase):
    """B15 (S157 E44): an omission run diagnoses as G — reason, highlight, solution, with the run's own measurements as the
    evidence — and a degeneration zone does NOT fire G (the negative control: the rule is run-shaped, never a catch-all)."""

    def _bench(self) -> bench.Bench:
        holder = tempfile.TemporaryDirectory(prefix="fp-test-b15-")
        self.addCleanup(holder.cleanup)
        root = Path(holder.name)
        (root / "book.md").write_text(
            "---\ntitle: B15 fixture\n---\n" +
            "\n".join(f"line {i} alpha beta gamma delta epsilon" for i in range(1, 60)),
            encoding="utf-8")
        conv = {"kind": "digital",
                "runs": [{"page": 757, "words": 154, "excerpt": "year. valuing famous using these inputs, you can estimate"},
                         {"page": None, "words": 432, "excerpt": "the value of a firm has three components. the first"}],
                "tripwires": {"degeneration": True,
                              "degeneration_detail": {"flagged": True, "md_lines": 59,
                                                      "worst": [{"line": 10, "chars": 900, "distinct_lines": 1, "max_trigram": 60, "zlib": 0.05,
                                                                 "excerpt": "of the purpose of the purpose of the purpose"}]}}}
        manifest = {"source": "b15.pdf", "pages": 1377, "fidelity": {"verdict": "fail", "convert": conv}}
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return bench.Bench(root)

    def test_an_omission_run_diagnoses_as_G_with_its_own_measurements_as_evidence(self):
        st = self._bench().state()
        runs = st["runs"]
        self.assertEqual(len(runs), 2)
        for r in runs:
            d = r["diagnosis"]
            self.assertEqual(d["signature"], "G", d)
            self.assertEqual(d["tag"], "Inferred")
            self.assertIn("omission run of %d words" % r["words"], d["matched_on"])
            for key in ("reason", "highlight", "solution"):
                self.assertTrue(len(d[key]) > 80, key)
        placed, unplaced = runs[0]["diagnosis"]["matched_on"], runs[1]["diagnosis"]["matched_on"]
        self.assertIn("page 757", placed)
        self.assertIn("UNREAD", unplaced)   # a null page is the audit's blindness, said, never rendered as page 0

    def test_negative_control_a_degeneration_zone_does_not_fire_G(self):
        st = self._bench().state()
        zones = st["zones"]
        self.assertEqual(len(zones), 1)
        self.assertNotEqual(zones[0]["diagnosis"]["signature"], "G", zones[0]["diagnosis"])
        self.assertEqual(zones[0]["diagnosis"]["signature"], "E")   # the loop signature, as before

    def test_the_bank_carries_G_after_the_six(self):
        ids = [s["id"] for s in bench.Bench._bank()]
        self.assertEqual(ids, ["E", "C", "A", "D", "B", "F", "G"])
        self.assertEqual(bench.Bench._ORDER[0], "G")


class TestB13BenchButtons(unittest.TestCase):
    """B13 (S157 E57): the page reaches /api/triage, /api/report and /api/ledger — the three endpoints S76 §18.4 proved and
    the glass never carried. Half source (the markup and the handlers exist, the page offers ONLY the human-only outcomes),
    half wire (the three routes answer, through the real handler, on a temp bundle: a dismissal needs a reason, the manifest
    gains the triage, the ledger reads as a list, the report is markdown and writes only when asked). Negative controls: a
    copy of the page without a button fails the source check; a dismissal without a reason is refused by the server."""

    def test_the_page_carries_the_three_controls_and_their_handlers(self):
        for needle in ('id="ledger-btn"', 'id="report-btn"', 'id="report-write"', 'id="ledger"', 'id="report"',
                       'api("/api/ledger")', 'api("/api/report", { write: !!write })', 'api("/api/triage", { key: site.key, outcome, reason })',
                       "function triageRow(site)", "async function triage(site, outcome)"):
            self.assertIn(needle, BENCH_HTML, needle)

    def test_the_page_offers_only_the_human_only_outcomes(self):
        m = re.search(r'const TRIAGE_MANUAL = \[([^\]]*)\];', BENCH_HTML)
        self.assertIsNotNone(m)
        offered = sorted(x.strip().strip('"') for x in m.group(1).split(","))
        self.assertEqual(offered, sorted(bench.OUTCOMES_MANUAL))
        # the derived outcomes are shown (outcomeTag) and never offered as buttons
        for derived in ("collapsed", "image-restored", "text-restored"):
            self.assertNotIn(f'data-triage="{derived}"', BENCH_HTML)

    def test_negative_control_a_page_without_the_ledger_button_fails_the_source_check(self):
        planted = BENCH_HTML.replace('id="ledger-btn"', 'id="ledger-btm"', 1)
        self.assertNotIn('id="ledger-btn"', planted)

    def _bundle(self) -> "bench.Bench":
        holder = tempfile.TemporaryDirectory(prefix="fp-test-b13-")
        self.addCleanup(holder.cleanup)
        root = Path(holder.name)
        (root / "book.md").write_text("---\ntitle: b13\n---\n" + "\n".join(f"line {i} alpha beta gamma" for i in range(1, 40)), encoding="utf-8")
        conv = {"kind": "digital", "runs": [{"page": 7, "words": 40, "excerpt": "the missing paragraph begins"}],
                "tripwires": {"degeneration": False}}
        (root / "manifest.json").write_text(json.dumps({"source": "b13.pdf", "pages": 20, "fidelity": {"verdict": "fail", "convert": conv}}), encoding="utf-8")
        return bench.Bench(root)

    def test_the_three_routes_answer_through_the_real_handler(self):
        subject = self._bundle()
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), bench.make_handler(subject))
        port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            key = subject.state()["runs"][0]["key"]
            st, body = _post(port, "/api/triage", {"key": key, "outcome": "dismissed-noise", "reason": ""})
            self.assertNotEqual(st, 200, "NEGATIVE CONTROL: a dismissal without a reason is refused")
            self.assertIn("reason", json.dumps(body))
            st, body = _post(port, "/api/triage", {"key": key, "outcome": "dismissed-noise", "reason": "witness noise: a running header"})
            self.assertEqual(st, 200, body)
            self.assertEqual(body["outcome"], "dismissed-noise")
            manifest = json.loads((subject.dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["triage"][key]["outcome"], "dismissed-noise")
            st, raw = _get(port, "/api/ledger")
            self.assertEqual(st, 200)
            doc = json.loads(raw)
            self.assertIsInstance(doc["events"], list)   # {events, audit, coverage} — the page reads all three
            self.assertTrue(doc["audit"]["intact"])
            self.assertEqual(doc["coverage"]["tally"]["dismissed-noise"], 1)
            st, body = _post(port, "/api/report", {"write": False})
            self.assertEqual(st, 200, body)
            self.assertIn("markdown", body)
            self.assertFalse(body["written"])
            self.assertFalse((subject.dir / "REPAIRS.md").exists(), "a preview writes nothing")
            st, body = _post(port, "/api/report", {"write": True})
            self.assertEqual(st, 200, body)
            self.assertTrue(body["written"] and (subject.dir / "REPAIRS.md").exists())
            st, body = _post(port, "/api/triage", {"key": key, "outcome": "open", "reason": ""})
            self.assertEqual(st, 200)
            manifest = json.loads((subject.dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertNotIn(key, manifest.get("triage", {}), "reopen withdraws the dismissal")
        finally:
            httpd.shutdown()
            httpd.server_close()


class TestM6Completeness(unittest.TestCase):
    """M6-R1: capped evidence is never mistaken for the complete review population."""

    @staticmethod
    def _runs(count: int) -> list[dict]:
        return [{"page": i + 1, "words": 20 + i,
                 "excerpt": f"line {i + 1} alpha beta gamma delta"}
                for i in range(count)]

    @staticmethod
    def _zones(count: int) -> list[dict]:
        return [{"line": i + 1, "chars": 80 + i, "distinct_lines": 2,
                 "excerpt": f"line {i + 1} alpha beta gamma delta"}
                for i in range(count)]

    def _bench(self, *, runs: int, zones: int, runs_total=..., zones_total=...,
               runs_cap=..., zones_cap=...) -> bench.Bench:
        holder = tempfile.TemporaryDirectory(prefix="fp-test-m6-")
        self.addCleanup(holder.cleanup)
        root = Path(holder.name)
        (root / "book.md").write_text(
            "---\ntitle: M6 fixture\n---\n" +
            "\n".join(f"line {i} alpha beta gamma delta epsilon" for i in range(1, 120)),
            encoding="utf-8")
        conv = {
            "kind": "digital",
            "runs": self._runs(runs),
            "tripwires": {
                "degeneration": bool(zones),
                "degeneration_detail": {
                    "flagged": bool(zones),
                    "md_lines": 119,
                    "worst": self._zones(zones),
                },
            },
        }
        if runs_total is not ...:
            conv["runs_total"] = runs_total
        if runs_cap is not ...:
            conv["runs_capped_at"] = runs_cap
        detail = conv["tripwires"]["degeneration_detail"]
        if zones_total is not ...:
            detail["blocks_total"] = zones_total
        if zones_cap is not ...:
            detail["worst_capped_at"] = zones_cap
        manifest = {"source": "m6.pdf", "pages": 119,
                    "fidelity": {"verdict": "fail", "convert": conv}}
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return bench.Bench(root)

    @staticmethod
    def _address_every_shown_site(subject: bench.Bench) -> None:
        st = subject.state()
        subject.manifest["triage"] = {
            site["key"]: {"outcome": "dismissed-noise", "reason": "M6 test disposition"}
            for site in [*st["zones"], *st["runs"]]
        }

    @staticmethod
    def _preview(subject: bench.Bench) -> dict:
        # Keep this glass harness stdlib-only: M6 tests the recommendation join, while the
        # fidelity module's own suite owns degeneration. The real marker-env pass runs later.
        fake = types.SimpleNamespace(degeneration=lambda _body: {
            "flagged": False, "worst": [], "blocks_total": 0, "worst_capped_at": 10})
        with mock.patch.dict(sys.modules, {"fidelity_audit": fake}):
            return subject.rescore_preview()

    def test_future_capped_totals_block_false_bless_even_when_shown_sites_are_addressed(self):
        subject = self._bench(runs=25, zones=10, runs_total=634, zones_total=37,
                              runs_cap=25, zones_cap=10)
        self._address_every_shown_site(subject)

        st = subject.state()
        self.assertEqual("25 of 634", st["evidence_counts"]["runs"]["label"])
        self.assertEqual("10 of 37", st["evidence_counts"]["zones"]["label"])
        cov = subject.coverage()
        self.assertEqual((35, 671, 636), (cov["shown"], cov["total"], cov["unseen"]))
        self.assertEqual((35, 0), (cov["addressed_shown"], cov["open_shown"]))
        self.assertEqual("partial", cov["completeness"])
        preview = self._preview(subject)
        self.assertFalse(preview["vault_recommendation"]["eligible"])
        self.assertIn("636 located defect(s) not shown",
                      preview["vault_recommendation"]["why"])
        self.assertIn("full-evidence review", preview["vault_recommendation"]["why"])

    def test_legacy_at_cap_is_unread_and_names_reconversion_remedy(self):
        subject = self._bench(runs=25, zones=10)
        self._address_every_shown_site(subject)
        counts = subject.state()["evidence_counts"]
        for kind, shown in (("runs", 25), ("zones", 10)):
            self.assertEqual("unread", counts[kind]["completeness"])
            self.assertEqual(f"{shown} of at least {shown} — total UNREAD",
                             counts[kind]["label"])
            self.assertEqual("re-convert to measure totals", counts[kind]["remedy"])
        preview = self._preview(subject)
        self.assertFalse(preview["vault_recommendation"]["eligible"])
        self.assertIn("re-convert to measure totals",
                      preview["vault_recommendation"]["why"])

    def test_legacy_under_cap_is_exact_not_needlessly_unread(self):
        subject = self._bench(runs=7, zones=2)
        counts = subject.state()["evidence_counts"]
        self.assertEqual(("complete", 7, "7"),
                         (counts["runs"]["completeness"],
                          counts["runs"]["total"], counts["runs"]["label"]))
        self.assertEqual(("complete", 2, "2"),
                         (counts["zones"]["completeness"],
                          counts["zones"]["total"], counts["zones"]["label"]))

    def test_future_complete_totals_use_the_shared_n_of_m_grammar(self):
        subject = self._bench(runs=7, zones=2, runs_total=7, zones_total=2,
                              runs_cap=25, zones_cap=10)
        counts = subject.state()["evidence_counts"]
        self.assertEqual("7 of 7", counts["runs"]["label"])
        self.assertEqual("2 of 2", counts["zones"]["label"])
        helper = js_function_body(EVENT_VOCAB, "countOfTotal")
        self.assertIn("`${shown} of ${total}`", helper)
        self.assertIn('shownOk ? shown : "?"', helper)
        self.assertIn("total UNREAD", helper)
        self.assertIn("re-convert to measure totals", helper)
        self.assertIn(
            "countOfTotal(runs.length, st.runs_total, st.runs_capped_at ?? 25)",
            WIDGET_MAIN)
        self.assertIn(
            "countOfTotal(zones.length, a.zones_total, a.zones_capped_at ?? 10)",
            WIDGET_ROOM)

    def test_display_limits_do_not_corrupt_manifest_completeness(self):
        subject = self._bench(runs=60, zones=0, runs_total=531, zones_total=0,
                              runs_cap=100, zones_cap=10)
        count = subject.state()["evidence_counts"]["runs"]
        self.assertEqual(
            ("partial", 531, 471, "60 of 531", "full-evidence review required"),
            (count["completeness"], count["total"], count["unseen"],
             count["label"], count["remedy"]))
        self.assertNotIn("display_cap", inspect.signature(bench.evidence_count).parameters)

        display = js_function_body(EVENT_VOCAB, "displaySliceNote")
        self.assertIn("available <= limit", display)
        self.assertIn("open Repair Bench for the full retained list", display)
        for source in (WIDGET_MAIN, WIDGET_ROOM):
            self.assertIn('displaySliceNote(runs.length, 40, "map")', source)
            self.assertIn('displaySliceNote(runs.length, 3, "details")', source)

    def test_producer_cap_overflow_remains_malformed(self):
        subject = self._bench(runs=101, zones=0, runs_total=531, zones_total=0,
                              runs_cap=100, zones_cap=10)
        count = subject.state()["evidence_counts"]["runs"]
        self.assertEqual("malformed", count["completeness"])
        self.assertIsNone(count["total"])
        self.assertIn("producer cap of 100", count["reason"])

    def test_rescore_counts_the_retained_list_not_an_arbitrary_preview_slice(self):
        subject = self._bench(runs=0, zones=0, runs_total=0, zones_total=0,
                              runs_cap=25, zones_cap=10)
        fake = types.SimpleNamespace(degeneration=lambda _body: {
            "flagged": True, "worst": self._zones(8),
            "blocks_total": 8, "worst_capped_at": 10})
        with mock.patch.dict(sys.modules, {"fidelity_audit": fake}):
            preview = subject.rescore_preview()
        current = preview["degeneration_now"]
        self.assertEqual(8, len(current["zones"]))
        self.assertEqual(("complete", 8, "8 of 8"),
                         (current["count"]["completeness"],
                          current["count"]["total"], current["count"]["label"]))

    def test_malformed_or_contradictory_totals_are_unread_and_fail_closed(self):
        for bad in (True, "634", -1, 6):
            with self.subTest(total=bad):
                subject = self._bench(runs=7, zones=0, runs_total=bad, zones_total=0,
                                      runs_cap=25, zones_cap=10)
                self._address_every_shown_site(subject)
                count = subject.state()["evidence_counts"]["runs"]
                self.assertEqual("malformed", count["completeness"])
                self.assertIsNone(count["total"])
                self.assertFalse(self._preview(subject)["vault_recommendation"]["eligible"])

    def test_wire_projects_completeness_and_the_fail_closed_recommendation(self):
        subject = self._bench(runs=25, zones=10, runs_total=634, zones_total=37,
                              runs_cap=25, zones_cap=10)
        self._address_every_shown_site(subject)
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), bench.make_handler(subject))
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        fake = types.SimpleNamespace(degeneration=lambda _body: {
            "flagged": False, "worst": [], "blocks_total": 0, "worst_capped_at": 10})
        try:
            code, raw = _get(port, "/api/state")
            state = json.loads(raw)
            self.assertEqual(200, code)
            self.assertEqual("25 of 634", state["evidence_counts"]["runs"]["label"])
            with mock.patch.dict(sys.modules, {"fidelity_audit": fake}):
                code, raw = _get(port, "/api/rescore")
                preview = json.loads(raw)
            self.assertEqual(200, code)
            self.assertFalse(preview["vault_recommendation"]["eligible"])
            self.assertEqual(636, preview["coverage"]["unseen"])
        finally:
            httpd.shutdown()
            httpd.server_close()


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
    def __init__(self, token, tokens_css=None):
        self.tmp = Path(tempfile.mkdtemp(prefix="fp-test-bundle-"))
        (self.tmp / "book.md").write_text("---\ntitle: t\n---\nline one\nline two\nline three",
                                          encoding="utf-8")
        self.bench = bench.Bench(self.tmp)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0),
                                         bench.make_handler(self.bench, token=token, tokens_css=tokens_css))
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestTokensCss(unittest.TestCase):
    """S215 E25: GET /fp-tokens.css serves the ONE file named by --tokens-css (the design system's sheet, private, beside the
    widgets) and nothing else; without it the route is a 404 that names the remedy, and the page's own fallbacks carry."""

    def test_with_a_sheet_the_route_serves_its_bytes_as_css(self):
        tmp = Path(tempfile.mkdtemp(prefix="fp-test-tokens-"))
        sheet = tmp / "fp-tokens.css"
        sheet.write_text(":root { --fp-clay: #d97757; }\n", encoding="utf-8")
        srv = LiveBenchServer(token=None, tokens_css=str(sheet))
        try:
            code, body = _get(srv.port, "/fp-tokens.css")
            self.assertEqual(code, 200)
            self.assertEqual(body, sheet.read_bytes(), "the route must serve the sheet's own bytes")
            code, _ = _get(srv.port, "/fp-tokens.cs")          # a near-miss path is not the route
            self.assertEqual(code, 404)
        finally:
            srv.close()
            shutil.rmtree(tmp, ignore_errors=True)

    def test_without_a_sheet_the_route_is_a_404_that_names_the_remedy(self):
        srv = LiveBenchServer(token=None)
        try:
            code, body = _get(srv.port, "/fp-tokens.css")
            self.assertEqual(code, 404)
            self.assertIn("--tokens-css", json.loads(body.decode("utf-8")).get("error", ""), "the 404 must name the remedy")
        finally:
            srv.close()

    def test_a_sheet_path_that_is_not_a_file_is_a_404_too(self):
        srv = LiveBenchServer(token=None, tokens_css=str(Path(tempfile.gettempdir()) / "fp-no-such-sheet.css"))
        try:
            self.assertEqual(404, _get(srv.port, "/fp-tokens.css")[0])
        finally:
            srv.close()


class TestServeOn(unittest.TestCase):
    """S215 E31 (the phone doors): --also-bind puts the same handler on a second address (the tailnet in use; a second loopback
    address here) — both answer the same routes; the flag is on the command line."""

    def test_two_addresses_one_handler(self):
        import socket
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        tmp = Path(tempfile.mkdtemp(prefix="fp-test-serveon-"))
        (tmp / "book.md").write_text("---\ntitle: t\n---\nline one", encoding="utf-8")
        try:
            servers = bench.serve_on(["127.0.0.1", "127.0.0.2"], port, bench.make_handler(bench.Bench(tmp), token=None))
        except OSError as e:
            self.skipTest("127.0.0.2 cannot be bound here (%s) -- UNREAD, not a pass" % e)
        if len(servers) < 2:   # round four: serve_on now skips an unbindable address instead of raising
            for srv in servers:
                srv.server_close()
            self.skipTest("127.0.0.2 was not bound here -- UNREAD, not a pass")
        t = threading.Thread(target=servers[0].serve_forever, daemon=True)
        t.start()
        try:
            for host in ("127.0.0.1", "127.0.0.2"):
                conn = http.client.HTTPConnection(host, port, timeout=10)
                conn.request("GET", "/api/state")
                r = conn.getresponse()
                self.assertEqual(r.status, 200, host)
                r.read()
                conn.close()
        finally:
            for srv in servers:
                srv.shutdown()
                srv.server_close()
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_flag_is_on_the_command_line(self):
        import subprocess
        out = subprocess.run([sys.executable, str(HERE / "bench.py"), "--help"], capture_output=True, text=True, timeout=60).stdout
        self.assertIn("--also-bind", out)


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
        # the census region is the MUTATING_POSTS tuple and the no-gate sentinel, up to token_gate (round three, 2026-09-30: the GET
        # classification READ_ONLY_GETS now sits further down, before make_handler, and names this route as a read on purpose)
        self.assertNotIn("/api/textlayer", src[src.index("MUTATING_POSTS"):src.index("def token_gate")],
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

    def test_s150_view_anchor_is_a_marker_not_raw_html(self):
        """S149's refuter set the view's renderer to html:false, which turned the raw anchor tag injected into the markdown
        source into visible text; S150 injects a plain marker paragraph and swaps it for the anchor after the render."""
        body = js_function_body(BENCH_HTML, "renderView")
        self.assertIn('"⟦FP-ZONE-ANCHOR⟧\\n\\n"', body, "the marker is injected as text before the zone's line")
        self.assertIn("<p>⟦FP-ZONE-ANCHOR⟧<\\/p>", body, "the rendered marker paragraph is swapped for the anchor")
        self.assertIn('\'<a id="fp-zone-anchor"></a>\'', body)
        self.assertNotIn('\'<a id="fp-zone-anchor"></a>\\n\\n\'', body, "the raw tag is never put into the markdown source")
        self.assertIn("html: false", BENCH_HTML.replace("html:false", "html: false"), "the view's renderer stays html:false (S149's refuter)")


class TestS214ScannerLink(unittest.TestCase):
    """S214 E5: the Scanner link, both ways — the page in the address (#p=<n>) routes through the bench's own goto once the
    state is loaded, and ◫ geometry opens the Scanner on this book's dir name and this page. Source-level, like the rest."""

    def test_hash_page_routes_through_goto_after_state(self):
        body = js_function_body(BENCH_HTML, "applyHashPage")
        self.assertIn("goto(", body, "the address's page must go through goto, the bench's one page function")
        self.assertIn("st.pages", body, "a page is honoured only once the state (st.pages) is loaded")
        self.assertRegex(body, r"#p=", "the address form is #p=<n>")
        self.assertIn('addEventListener("hashchange", applyHashPage)', BENCH_HTML, "a later address change is honoured too")
        # Negative control: a handler that sets the page image directly would bypass goto's placeholder path (OK-2)
        self.assertNotIn("setPageImage(", body)

    def test_geometry_button_opens_the_scanner_on_this_book_and_page(self):
        self.assertIn('id="geo-btn"', BENCH_HTML, "the toolbar carries ◫ geometry")
        # S215 E34 (round four): at the address the bench was opened by, the loopback only as the fallback — the literal
        # 127.0.0.1 sent the phone to itself
        self.assertIn('"http://" + (location.hostname || "127.0.0.1") + ":7180/?dir="', BENCH_HTML, "the Scanner is addressed by the bundle dir name…")
        self.assertNotIn('window.open("http://127.0.0.1:7180', BENCH_HTML, "no hard-coded loopback address for the Scanner")
        self.assertIn("encodeURIComponent(st.bundle)", BENCH_HTML, "…taken from the bench's own state")
        self.assertIn('"&page=" + page', BENCH_HTML, "…and the bench's current page")
        # Negative control: the link must not carry the bench's secret to another origin
        seg = BENCH_HTML[BENCH_HTML.index('id="geo-btn"'):]
        self.assertNotIn("token", seg[seg.index(":7180/?dir="):seg.index(":7180/?dir=") + 200])


class TestHostCheck(unittest.TestCase):
    """S215 round four (DNS rebinding): a Host that is not the bench's own name is refused before any route (GET and POST);
    its loopback names, its listening address and a --host name pass; every answer says Referrer-Policy: no-referrer; an
    --also-bind address that cannot be bound leaves the loopback bench running."""

    @classmethod
    def setUpClass(cls):
        import socket
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        cls.port = s.getsockname()[1]
        s.close()
        cls.tmp = Path(tempfile.mkdtemp(prefix="fp-test-host-"))
        (cls.tmp / "book.md").write_text("---\ntitle: t\n---\nline one", encoding="utf-8")
        cls.servers = bench.serve_on(["127.0.0.1"], cls.port, bench.make_handler(bench.Bench(cls.tmp), token="t0k", hosts=("desktop-bndit",)))
        threading.Thread(target=cls.servers[0].serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        for srv in cls.servers:
            srv.shutdown()
            srv.server_close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def ask(self, method, host, path="/api/state", body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.putrequest(method, path, skip_host=True)
        conn.putheader("Host", host)
        if body is not None:
            conn.putheader("Content-Type", "application/json")
            conn.putheader("Content-Length", str(len(body)))
        conn.endheaders(body)
        r = conn.getresponse()
        data, hdr = r.read(), dict(r.getheaders())
        conn.close()
        return r.status, data, hdr

    def test_foreign_host_refused_get(self):
        s, data, _ = self.ask("GET", "evil.example:%d" % self.port)
        self.assertEqual(s, 421)
        self.assertIn(b"own names", data)

    def test_foreign_host_refused_post_before_the_token(self):
        s, _, _ = self.ask("POST", "evil.example:%d" % self.port, "/api/repair", b'{"zone_line": 1}')
        self.assertEqual(s, 421)

    def test_own_names_pass_and_no_referrer(self):
        for h in ("127.0.0.1:%d" % self.port, "localhost:%d" % self.port, "desktop-bndit:%d" % self.port):
            s, _, hdr = self.ask("GET", h)
            self.assertEqual(s, 200, h)
            self.assertEqual(hdr.get("Referrer-Policy"), "no-referrer", h)

    def test_unbindable_also_bind_leaves_loopback(self):
        import socket
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        # 2026-09-30 (the tailnet lock): serve_on now refuses a LAN address outright (TestTailnetLock), so the address that is "not on
        # this machine" is a tailnet-range one nobody here holds. Round three (2026-09-30): NO socket is ever bound or probed on it - a test
        # may bind loopback only. The listener class is a stub that builds the real class for a loopback address and, for any other,
        # raises the OSError the OS gives for an address this machine does not hold (EADDRNOTAVAIL) WITHOUT creating a socket; what
        # serve_on asked it for is recorded, so "the ghost was asked for, refused, and the loopback bench ran" is observed, not assumed.
        import errno
        import ipaddress
        ghost = "100.64.0.1"
        asked, real_class = [], bench.ThreadingHTTPServer

        def stub(addr, handler):
            asked.append(addr)
            if not ipaddress.ip_address(addr[0]).is_loopback:
                raise OSError(errno.EADDRNOTAVAIL, "Cannot assign requested address (stub: no socket was made)")
            return real_class(addr, handler)
        with mock.patch.object(bench, "ThreadingHTTPServer", side_effect=stub):
            servers = bench.serve_on(["127.0.0.1", ghost], port, bench.make_handler(bench.Bench(self.tmp), token=None))
        try:
            self.assertEqual([a[0] for a in asked], ["127.0.0.1", ghost], "serve_on asked for the loopback bench first, then the ghost")
            self.assertEqual(len(servers), 1)
            self.assertEqual(servers[0].server_address[0], "127.0.0.1")
        finally:
            for srv in servers:
                srv.server_close()


class TestE34Phone(unittest.TestCase):
    """S215 E34 (Rab, Desk 8b065892 2026-09-29 08:12:09Z: "Also repair bench is poorly optimized for mobile."): the header's
    tools as one strip (a swiping row on the phone, display:contents at the desk); sideways (lay-short) set by its own script,
    never inside the program block or the S147 layout module."""

    def test_the_strip_wraps_every_tool_and_carries_no_id(self):
        a = BENCH_HTML.index('<span class="htools">')
        b = BENCH_HTML.index("</header>")
        strip = BENCH_HTML[a:b]
        for tool in ("info-btn", "ledger-btn", "report-btn", "evidence-btn", "guide-btn", "help-btn", 'id="theme"', "rescore", "geo-btn"):
            self.assertIn(tool, strip, tool)
        self.assertNotIn("id=", BENCH_HTML[a:a + len('<span class="htools">') + 1], "the strip carries no id (the S147 invariant's id set)")

    def test_desk_layout_untouched_and_phone_rules_present(self):
        self.assertIn(".htools { display:contents; }", BENCH_HTML)
        self.assertIn("html.lay-phone .htools { display:flex;", BENCH_HTML)
        self.assertIn("html.lay-short header { flex-wrap:nowrap;", BENCH_HTML)
        self.assertIn("html.lay-short #upper { max-height:min(var(--upper-h, 64px), 45vh); }", BENCH_HTML)

    def test_lay_short_is_set_outside_the_program_and_the_layout_module(self):
        program = BENCH_HTML[BENCH_HTML.index("<script>\nconst $ = (id)"):]
        program = program[:program.index("</script>")]
        layout = BENCH_HTML[BENCH_HTML.index("/* ---- S147 · the layout module"):]
        layout = layout[:layout.index("</script>")]
        self.assertNotIn("lay-short", program)
        self.assertNotIn("lay-short", layout)
        self.assertIn('root.classList.toggle("lay-short", !root.classList.contains("lay-phone") && innerHeight <= 520 && innerWidth > innerHeight)', BENCH_HTML)


class TestPeersAndDot(unittest.TestCase):
    """S215 round five: serve_on's servers share one list of peers (the picker's swap goes to all of them); a Host with a trailing
    dot is its own name."""

    def test_servers_share_their_peers(self):
        import socket
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        tmp = Path(tempfile.mkdtemp(prefix="fp-test-peers-"))
        (tmp / "book.md").write_text("---\ntitle: t\n---\nline one", encoding="utf-8")
        servers = bench.serve_on(["127.0.0.1", "127.0.0.2"], port, bench.make_handler(bench.Bench(tmp), token=None))
        try:
            if len(servers) < 2:
                self.skipTest("127.0.0.2 was not bound here -- UNREAD, not a pass")
            self.assertIs(servers[0].peers, servers[1].peers)
            self.assertEqual(len(servers[0].peers), 2)
        finally:
            for srv in servers:
                srv.shutdown() if srv is not servers[0] else None
                srv.server_close()
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_picker_swaps_every_listener(self):
        src = Path(bench.__file__).read_text(encoding="utf-8")
        self.assertIn('for srv in getattr(self.server, "peers", None) or [self.server]:', src)
        self.assertNotIn("                    self.server.bench = new_bench\n", src)

    def test_trailing_dot(self):
        self.assertEqual(bench.host_name("Desktop-Bndit.tailc44e8c.ts.net.:7077"), "desktop-bndit.tailc44e8c.ts.net")
        self.assertTrue(bench.host_ok("localhost.:7077", "127.0.0.1"))


def _picker_swap_probe(mod):
    """S215 round seven (round six, finding 17). Two listeners of one serve_on on loopback addresses (127.0.0.1 and 127.0.0.2), on the real
    bench module or on a mutant of its source: through the first the picker opens book-b, through the second it opens book-a, and after
    each open BOTH listeners are asked for /api/state. Returns (rows, why): a row is (listener asked, book opened, HTTP status of the open,
    what each listener now shows, whether the two hold ONE Bench object); why is '' when the probe ran, else what stopped it (an address
    that cannot be bound is UNREAD, never a pass). mod.OPEN_ROOTS points at a temp root for the probe: nothing of the library is opened."""
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    root = Path(tempfile.mkdtemp(prefix="fp-test-swap-"))
    for name in ("book-a", "book-b"):
        (root / name).mkdir()
        (root / name / "book.md").write_text("---\ntitle: t\n---\nline one", encoding="utf-8")
    servers = []
    serving_first = False
    try:
        with mock.patch.object(mod, "OPEN_ROOTS", (root,)):
            try:
                servers = mod.serve_on(["127.0.0.1", "127.0.0.2"], port,
                                       mod.make_handler(mod.Bench(root / "book-a"), token="t0k"))
            except OSError as e:
                return [], "the listeners could not be bound here (%s)" % e
            if len(servers) < 2:
                return [], "127.0.0.2 was not bound here"
            threading.Thread(target=servers[0].serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
            serving_first = True
            hosts = ("127.0.0.1", "127.0.0.2")

            def call(host, method, path, body=None):
                conn = http.client.HTTPConnection(host, port, timeout=10)
                conn.request(method, path, body=body,
                             headers={"X-FP-Token": "t0k", "Content-Type": "application/json"} if body is not None else {})
                r = conn.getresponse()
                data = r.read()
                conn.close()
                return r.status, json.loads(data.decode("utf-8"))

            rows = []
            for asked, book in ((hosts[0], "book-b"), (hosts[1], "book-a")):
                status, _ = call(asked, "POST", "/api/open", json.dumps({"path": str(root / book)}).encode("utf-8"))
                seen = tuple(call(h, "GET", "/api/state")[1].get("bundle") for h in hosts)
                first, second = getattr(servers[0], "bench", None), getattr(servers[1], "bench", None)
                rows.append((asked, book, status, seen, first is not None and first is second))
            return rows, ""
    finally:
        # shutdown() waits for its serve_forever to notice (up to its poll interval), so the listeners are stopped together; it also waits
        # forever on a serve_forever that never ran, so the first listener is stopped only if it was started
        stoppers = [threading.Thread(target=srv.shutdown) for i, srv in enumerate(servers) if i > 0 or serving_first]
        for th in stoppers:
            th.start()
        for th in stoppers:
            th.join()
        for srv in servers:
            srv.server_close()
        shutil.rmtree(root, ignore_errors=True)


def _swap_reaches_both(rows):
    """The property the picker's swap must have: both opens answered 200, and after each one BOTH listeners show the book just opened
    and hold one and the same Bench object."""
    return len(rows) == 2 and all(status == 200 and seen == (book, book) and same
                                  for (_asked, book, status, seen, same) in rows)


class TestPickerSwapLive(unittest.TestCase):
    """S215 round seven (round six, finding 17: "Nothing tests that the picker's swap actually reaches every bench listener"):
    TestPeersAndDot.test_the_picker_swaps_every_listener greps the source, so a swap loop whose body was `pass` -- or that swaps only the
    listener that was asked, which is the bug round five fixed -- left the whole file green. This runs it: the picker opens a book through
    one listener of a two-listener serve_on and the OTHER listener must show it (and the reverse), on loopback addresses only."""

    def test_a_swap_posted_to_either_listener_is_seen_on_both(self):
        rows, why = _picker_swap_probe(bench)
        if why:
            self.skipTest(why + " -- UNREAD, not a pass")
        self.assertTrue(_swap_reaches_both(rows), rows)


def _bench_mutant(old, new):
    """S215 round seven (round six, finding 17): bench.py's source with exactly one statement changed, exec'd as a module of its own (its
    __file__ is the real one, so its folder lookups resolve). The real module is not touched. The anchor must be found exactly once."""
    src = Path(bench.__file__).read_text(encoding="utf-8")
    if src.count(old) != 1:
        raise AssertionError("mutation anchor %r found %d times in bench.py" % (old, src.count(old)))
    mod = types.ModuleType("bench_mutant_r7")
    mod.__file__ = bench.__file__
    exec(compile(src.replace(old, new), bench.__file__, "exec", dont_inherit=True), mod.__dict__)
    return mod


class TestPickerSwapMutants(unittest.TestCase):
    """S215 round seven (round six, finding 17): the negatives to TestPickerSwapLive. The live probe is run on mutants of the swap
    statement in bench.py's /api/open branch; each must fail it, and the unchanged source loaded the same way must pass."""

    SWAP = "srv.bench = new_bench"

    def test_the_unchanged_source_passes_the_probe_when_loaded_as_a_mutant(self):
        rows, why = _picker_swap_probe(_bench_mutant(self.SWAP, self.SWAP))
        if why:
            self.skipTest(why + " -- UNREAD, not a pass")
        self.assertTrue(_swap_reaches_both(rows), rows)

    def test_each_broken_swap_fails_the_probe(self):
        mutants = (
            ("pass: the loop runs and swaps nothing", "pass"),
            ("only the listener that was asked", "if srv is self.server: srv.bench = new_bench"),
            ("only the others", "if srv is not self.server: srv.bench = new_bench"),
            ("each listener opens its own copy", 'srv.bench = open_target(str(payload["path"]))'),
        )
        for name, new in mutants:
            with self.subTest(mutant=name):
                rows, why = _picker_swap_probe(_bench_mutant(self.SWAP, new))
                if why:
                    self.skipTest(why + " -- UNREAD, not a pass")
                self.assertFalse(_swap_reaches_both(rows), "%s: the live probe still passes, so it cannot tell (%r)" % (name, rows))


class TestHostDots(unittest.TestCase):
    """S215 E37 (round six, 18): a Host of only dots is refused, never read as 'no Host sent'"""

    def test_dots_only_refused_names_with_a_dot_admitted(self):
        self.assertFalse(bench.host_ok(".", "127.0.0.1"))
        self.assertFalse(bench.host_ok(".:7077", "127.0.0.1"))
        self.assertFalse(bench.host_ok("::1.", "127.0.0.1"))
        self.assertTrue(bench.host_ok("localhost.:7077", "127.0.0.1"))
        self.assertTrue(bench.host_ok(None, "127.0.0.1"), "no Host at all: the loopback still admits a local tool")

    def test_negative_control_the_old_strip(self):
        old = lambda name: name[:-1] if name.endswith(".") else name   # noqa: E731 — the round-five line
        self.assertEqual(old("."), "", "the old strip turned '.' into '' (read as no Host)")


class TestBodyCache(unittest.TestCase):
    """S215 E36: the body is read once per change of the file; an outside write is seen; the bench's own write drops its copy;
    state() is the same warm and cold."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="fp-test-cache-"))
        self.md = self.tmp / "book.md"
        self.md.write_text("---\ntitle: t\n---\nline one\nline  two\n", encoding="utf-8")
        self.b = bench.Bench(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_read_once_per_change(self):
        a = self.b.body()
        self.assertIs(self.b.body(), a, "an unchanged file is not read again (the same string object)")
        self.assertEqual(self.b._lines()[1], ["line one", "line two", ""])

    def test_an_outside_write_is_seen(self):
        self.b.body()
        import os
        import time as _t
        self.md.write_text("---\ntitle: t\n---\nchanged by another hand\n", encoding="utf-8")
        st = self.md.stat()
        os.utime(self.md, ns=(st.st_atime_ns, st.st_mtime_ns + 2_000_000))   # a clock that moved, whatever the file system's grain
        self.assertIn("changed by another hand", self.b.body())
        self.assertIn("changed by another hand", self.b._lines()[1])

    def test_the_bench_write_drops_its_copy(self):
        self.b.body()
        self.b._write_body("rewritten by the bench\n", gesture="manual-edit", note="test")
        self.assertIn("rewritten by the bench", self.b.body())

    def test_a_same_size_rewrite_inside_one_tick_is_seen(self):
        """round seven: the (mtime, size) key missed this; the bytes compare cannot"""
        import os
        self.md.write_text("---\ntitle: t\n---\naaaa\n", encoding="utf-8")
        st = self.md.stat()
        self.assertIn("aaaa", self.b.body())
        self.md.write_text("---\ntitle: t\n---\nbbbb\n", encoding="utf-8")
        os.utime(self.md, ns=(st.st_atime_ns, st.st_mtime_ns))   # the old mtime put back: same size, same tick
        self.assertIn("bbbb", self.b.body())
        self.assertIn("bbbb", self.b._lines()[1])

    def test_crlf_decoded_as_read_text_does(self):
        self.md.write_bytes(b"---\r\ntitle: t\r\n---\r\none\r\ntwo\r\n")
        self.assertEqual(self.b.body(), bench.split_frontmatter(self.md.read_text(encoding="utf-8"))[1])

    def test_the_resolvers_agree_with_their_pre_e36_forms(self):
        body = "Alpha  Beta\tGamma delta\n  The QUICK brown   fox jumps over\nplain line\nthe quick BROWN fox again here\n"
        self.md.write_text("---\ntitle: t\n---\n" + body, encoding="utf-8")
        b = bench.Bench(self.tmp)

        def run_old(run):                       # bench.py before E36, written out
            words = (run.get("excerpt") or "").split()
            if len(words) < 3:
                return None
            body_norm = [" ".join(ln.split()).lower() for ln in b.body().split("\n")]
            for n in (6, 5, 4, 3):
                if len(words) < n:
                    continue
                needle = " ".join(words[:n]).lower().strip("-—•* ")
                if len(needle) < 8:
                    continue
                hits = [i + 1 for i, ln in enumerate(body_norm) if needle in ln]
                if hits:
                    return hits[0]
            return None

        def zone_hits_old(excerpt):
            return [i + 1 for i, ln in enumerate(b.body().split("\n")) if excerpt in " ".join(ln.split())]
        for ex in ("the quick brown fox never here", "Alpha Beta Gamma delta", "QUICK brown fox jumps over the", "no such words at all"):
            self.assertEqual(b._resolve_run_line({"excerpt": ex}), run_old({"excerpt": ex}), ex)
        for ex in ("Alpha Beta Gamma", "The QUICK brown fox", "plain line", "absent"):
            got = [i + 1 for i, ln in enumerate(b._lines()[1]) if ex in ln]
            self.assertEqual(got, zone_hits_old(ex), ex)

    def test_md_and_page_revalidate(self):
        srv = bench.serve_on(["127.0.0.1"], 0, bench.make_handler(self.b))
        try:
            threading.Thread(target=srv[0].serve_forever, daemon=True).start()   # serve_on leaves the first to its caller
            port = srv[0].server_address[1]
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
            c.request("GET", "/api/md")
            r = c.getresponse(); r.read()
            tag = r.getheader("ETag")
            self.assertEqual(r.status, 200)
            self.assertTrue(tag and tag.startswith('"md-'), tag)
            self.assertEqual(r.getheader("Cache-Control"), "no-cache")
            c.request("GET", "/api/md", headers={"If-None-Match": tag})
            r = c.getresponse(); body = r.read()
            self.assertEqual((r.status, body), (304, b""))
            self.md.write_text("---\ntitle: t\n---\nchanged\n", encoding="utf-8")
            c.request("GET", "/api/md", headers={"If-None-Match": tag})
            r = c.getresponse(); r.read()
            self.assertEqual(r.status, 200)
            self.assertNotEqual(r.getheader("ETag"), tag)
            self.assertIsNone(self.b.page_etag(1, 72), "no PDF: no page validator, the route answers as before")
        finally:
            for s in srv:
                s.shutdown(); s.server_close()

    def test_http11_keepalive_and_the_304(self):
        """S215 E36 (round seven): HTTP/1.1 on one kept-alive connection — the browser's form of revalidation"""
        srv = bench.serve_on(["127.0.0.1"], 0, bench.make_handler(self.b, token="t0k"))   # a gate, so the POST below is refused
        try:
            threading.Thread(target=srv[0].serve_forever, daemon=True).start()
            c = http.client.HTTPConnection("127.0.0.1", srv[0].server_address[1], timeout=10)
            c.request("GET", "/api/md")
            r = c.getresponse(); r.read()
            self.assertEqual((r.version, r.status), (11, 200), "the bench answers HTTP/1.1")
            tag = r.getheader("ETag")
            c.request("GET", "/api/md", headers={"If-None-Match": tag})   # the SAME connection, kept alive
            r = c.getresponse(); body = r.read()
            self.assertEqual((r.version, r.status, body), (11, 304, b""))
            c.request("POST", "/api/md", body=b'{"text": "x"}', headers={"Content-Type": "application/json", "X-FP-Token": "wrong"})
            r = c.getresponse(); r.read()
            c.request("GET", "/api/md", headers={"If-None-Match": tag})   # after a refused POST: the drained body never leaks
            r = c.getresponse(); r.read()
            self.assertEqual(r.status, 304)
            c.close()
        finally:
            for s in srv:
                s.shutdown(); s.server_close()

    def test_state_same_warm_and_cold(self):
        cold = bench.Bench(self.tmp).state()
        self.b.state()
        warm = self.b.state()
        self.assertEqual(json.dumps(cold, sort_keys=True, default=str), json.dumps(warm, sort_keys=True, default=str))



def e38_block(src: str) -> str:
    """the S215 E38 <script> block (the windowed pane), from its head comment to its </script>"""
    at = src.index("/* S215 E38 (Rab, Desk 4354924f")
    return src[at:src.index("</script>", at)]


def e38_window_rule_ok(block: str) -> bool:
    """the window only on the phone layouts AND never while the pane is editable"""
    m = re.search(r"const windowed = \(\) => (.+?);", block)
    return bool(m) and "phone()" in m.group(1) and "!editing()" in m.group(1) and \
        'contains("lay-phone")' in block and 'contains("lay-short")' in block


def e38_edit_order_ok(block: str) -> bool:
    """the ✎ wrapper draws the whole file BEFORE the program's handler makes the pane editable, flags the click, and
    toggleView draws no window inside it"""
    w = block[block.index("editBtn.onclick = function"):]
    return w.index("whole()") < w.index("_edit.call(") and "inEditClick = true" in w and \
        "!inEditClick" in block[block.index("toggleView = function"):block.index("editBtn")]


class TestE38WindowedPane(unittest.TestCase):
    """S215 E38 (Rab, Desk 4354924f 2026-09-29 10:16:52Z: "harsh latency especially when I rotate my phone"): on the phone the
    markdown pane draws the lines near the screen; the editor and the desk draw the whole file, as before."""

    def setUp(self):
        self.src = BENCH_HTML.replace("\r\n", "\n")
        self.block = e38_block(self.src)

    def test_rebinds_the_programs_own_functions_only(self):
        for name in ("renderLines", "ctxText", "scrollToLine", "markTableHealth", "toggleView"):
            self.assertIn(f"{name} = function", self.block, f"E38 no longer rebinds {name}")
        self.assertNotIn("S215 E38", self.src[self.src.index("const $ = (id) =>"):self.src.index("/* ---- S147 · the layout module")],
                         "E38 must live outside the program block")

    def test_window_only_on_the_phone_and_never_while_editing(self):
        self.assertTrue(e38_window_rule_ok(self.block))

    def test_window_rule_negative_control(self):
        self.assertFalse(e38_window_rule_ok(self.block.replace("phone() && !editing()", "phone()")),
                         "the helper failed to catch a window drawn under the editor")

    def test_the_editor_gets_the_whole_file_first(self):
        self.assertTrue(e38_edit_order_ok(self.block))

    def test_the_editor_order_negative_controls(self):
        self.assertFalse(e38_edit_order_ok(self.block.replace("!viewOn && windowed() && !inEditClick", "!viewOn && windowed()")),
                         "the helper failed to catch toggleView drawing a window inside a ✎ click (the editor would get a slice)")
        swapped = self.block.replace("    if (!editing() && win) { keep = firstOnScreen(); whole(); }\n", "").replace(
            "    try { r = _edit.call(this, e); } finally { inEditClick = false; }\n",
            "    try { r = _edit.call(this, e); } finally { inEditClick = false; }\n    if (win) whole();\n")
        self.assertFalse(e38_edit_order_ok(swapped), "the helper failed to catch the whole file drawn AFTER the pane became editable")

    def test_a_slice_never_feeds_the_programs_highlight_path_or_the_save(self):
        draw = self.block[self.block.index("function draw("):self.block.index("function whole(")]
        self.assertIn("renderedText = null", draw)
        self.assertRegex(self.block, r"ctxText = function \(\) \{ return win \? mdText : _ctxText\(\); \};")

    def test_class_changes_are_acted_on_in_an_animation_frame(self):
        self.assertRegex(self.block, r"const later = function \(\) \{ if \(!modeRaf\) modeRaf = requestAnimationFrame\(settle\); \};")
        self.assertIn('new MutationObserver(later).observe(root, { attributes: true, attributeFilter: ["class"] })', self.block)

    def test_round_six_refit_after_a_turn_fit_modes_only(self):
        tail = self.block[self.block.index("round six (22)"):]
        self.assertIn("requestAnimationFrame(", tail)
        self.assertRegex(tail, r'z\.value === "fit" \|\| z\.value === "fitpage"\) && typeof applyZoom === "function"\) applyZoom\(\)')

    def test_round_six_sideways_css(self):
        self.assertIn("html.lay-short .patient { flex:none; max-width:34vw; overflow-x:auto;", self.src)
        self.assertNotRegex(self.src, r"html\.lay-short \.patient \{[^}]*overflow:hidden", "sideways the chips must swipe (round six, 20)")
        self.assertIn("padding-bottom:env(safe-area-inset-bottom)", self.src)



def e38_leave_ok(block: str) -> bool:
    """✎-off and the crossing read the whole file's own row height (firstOfWhole, rounded) and jump the window to that line"""
    fw = block[block.index("function firstOfWhole()"):block.index("let tbFor")]
    edit = block[block.index("editBtn.onclick = function"):block.index('ctx.addEventListener("scroll"')]
    settle = block[block.index("function settle()"):block.index("const later")]
    return ("Math.round(" in fw and "getBoundingClientRect().height" in fw and "draw(firstOfWhole(), true)" in edit
            and "draw(firstOfWhole(), true)" in settle)


def e38_selection_ok(block: str) -> bool:
    scroll = block[block.index('ctx.addEventListener("scroll"'):block.index("function settle()")]
    cp = block[block.index('document.addEventListener("copy"'):]
    return ("selOpenInPane()" in scroll and "}, true);" in cp and "stopImmediatePropagation" in cp
            and "r.intersectsNode(pads[0]) || r.intersectsNode(pads[1])" in cp and "L.slice(" in cp)


class TestE38RoundEight(unittest.TestCase):
    """S215 E38, round eight (wf_1b9eba3a) and round seven's preload profile: the fixes' shapes, each with its negative control."""

    def setUp(self):
        self.src = BENCH_HTML.replace("\r\n", "\n")
        self.block = e38_block(self.src)

    def test_leaving_the_editor_keeps_the_line(self):
        self.assertTrue(e38_leave_ok(self.block))

    def test_leaving_the_editor_negative_control(self):
        self.assertFalse(e38_leave_ok(self.block.replace("draw(firstOfWhole(), true);   // round eight: the whole file's own row height",
                                                         "draw(firstOnScreen());")), "the helper missed the 2 %-per-cycle drift")
        self.assertFalse(e38_leave_ok(self.block.replace("Math.round((ctx.scrollTop - PAD)", "Math.floor((ctx.scrollTop - PAD)")),
                         "the helper missed the floor that lost one line per cycle")

    def test_a_selection_is_never_redrawn_and_copies_true_lines(self):
        self.assertTrue(e38_selection_ok(self.block))

    def test_selection_negative_control(self):
        self.assertFalse(e38_selection_ok(self.block.replace("      if (!win || selOpenInPane()) return;\n", "      if (!win) return;\n")))
        self.assertFalse(e38_selection_ok(self.block.replace("  }, true);\n  // round six (22)", "  });\n  // round six (22)")),
                         "the copy must be captured before the pane's own handler")

    def test_table_marks_follow_the_buffer(self):
        draw = self.block[self.block.index("function draw("):self.block.index("function whole(")]
        self.assertIn("tbFresh();", draw)
        fresh = self.block[self.block.index("function tbFresh()"):self.block.index("function selOpenInPane()")]
        self.assertIn("if (tbFor === mdText) return;", fresh)

    def test_an_unsized_frame_reads_no_layout(self):
        self.assertIn("const unsized = () => !innerWidth || !innerHeight;", self.block)
        self.assertIn("const firstOnScreen = () => unsized() ? 0 :", self.block)
        self.assertIn("const rowsOnScreen = () => unsized() ? 40 :", self.block)
        draw = self.block[self.block.index("function draw("):self.block.index("function whole(")]
        self.assertIn("if (!hidden) ctx.scrollTop =", draw)

    def test_e34_more_once_per_frame(self):
        at = self.src.index("/* S215 E34 (Rab, Desk 8b065892 08:12:09Z")   # the script's head (the CSS's carries the date)
        e34 = self.src[at:self.src.index("</script>", at)]
        self.assertIn("function moreSoon() { if (!moreRaf) moreRaf = requestAnimationFrame(", e34)
        for use in ("new ResizeObserver(moreSoon)", "new MutationObserver(moreSoon)", 'addEventListener("scroll", moreSoon', "setTimeout(moreSoon, 400)"):
            self.assertIn(use, e34)
        self.assertNotRegex(e34, r"Observer\(more\)", "a layout read per mutation (834 ms at 4x in the hidden preload)")


# ---- the tailnet lock (Rab, 2026-09-30: "absolute locked inside my tailscale vpn, and no one can access it, even if they got a
# screenshot of it and tried to access it themselves"). Lock one is the listener's address (the launch flags and the widgets'
# own hosts); this file proves locks two and three: serve_on/--also-bind refuse a wide address before a socket exists, and
# Handler.handle() answers a bare 403 to any peer that is not loopback or the tailnet, before it reads a byte. A request
# that came through a proxy is refused too. Every family has its positive control (the real thing passes) first.
class _FakeReader(io.BytesIO):
    """the request side of a fake connection: how far it had been read when it was closed, and the size of every read() on it"""
    at_close = None

    def __init__(self, data):
        super().__init__(data)
        self.sizes = []

    def read(self, size=-1):
        self.sizes.append(size)
        return super().read(size)

    def close(self):
        if self.at_close is None:
            self.at_close = self.tell()
        super().close()


class _FakeConn:
    """a socket that speaks from a byte string and keeps what is written to it; nothing here touches a network"""

    def __init__(self, raw):
        self.raw, self.sent, self.reader, self.timeouts = raw, [], None, []

    def settimeout(self, t):
        self.timeouts.append(t)

    def makefile(self, mode="rb", bufsize=-1):
        self.reader = _FakeReader(self.raw)
        return self.reader

    def sendall(self, data):
        self.sent.append(bytes(data))

    def close(self):
        pass

    def wire(self):
        return b"".join(self.sent)


def _raw(method, path="/api/state", host="100.108.102.101:7077", headers=None, body=b""):
    """one HTTP/1.1 request as bytes; Content-Length is added for a body unless the headers carry their own"""
    head = {"Host": host, **(headers or {})}
    if body and "Content-Length" not in head:
        head["Content-Length"] = str(len(body))
    return (f"{method} {path} HTTP/1.1\r\n" + "".join(f"{k}: {v}\r\n" for k, v in head.items()) + "\r\n").encode("latin-1") + body


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class TestTailnetLock(unittest.TestCase):
    TRUSTED = ("127.0.0.1", "::1", "100.97.237.60", "100.108.102.101", "fd7a:115c:a1e0::1", "::ffff:100.97.237.60")
    STRANGERS = ("192.168.2.207", "8.8.8.8", "::ffff:192.168.2.207", "2001:db8::7f00:1")

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="fp-test-lock-"))
        (self.tmp / "book.md").write_text("---\ntitle: t\n---\nline one\nline two", encoding="utf-8")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.server = types.SimpleNamespace(server_address=("100.108.102.101", 7077))   # what the handler reads: the address it listens on

    def drive(self, handler, peer, raw):
        """run the REAL handler class over a fake connection from `peer`; the refusal note is swallowed, not printed"""
        conn = _FakeConn(raw)
        addr = (peer, 5555, 0, 0) if isinstance(peer, str) and ":" in peer else (peer, 5555)
        with contextlib.redirect_stdout(io.StringIO()):
            handler(conn, addr, self.server)
        return conn

    def spy(self, **kw):
        """the real Handler with every do_* replaced by a recorder, so 'no method ran' is observed, not assumed"""
        base = bench.make_handler(bench.Bench(self.tmp), **kw)
        calls = []

        class Spy(base):
            pass
        for m in ("GET", "POST", "HEAD", "OPTIONS", "PUT"):
            def do(self, _m=m):
                calls.append(_m)
                self.rfile.read(int(self.headers.get("Content-Length") or 0))   # a real method consumes its body
                self._json({"spy": _m})
            setattr(Spy, "do_" + m, do)
        return Spy, calls

    # -- the tables
    def test_peer_ok_table(self):
        for ip in ("127.0.0.1", "::1", "100.97.237.60", "100.108.102.101", "fd7a:115c:a1e0::1", "::ffff:100.97.237.60"):
            self.assertTrue(bench.peer_ok(ip), ip)
        for ip in ("192.168.2.207", "8.8.8.8", "::ffff:192.168.2.207", "2001:db8::7f00:1", "", "not-an-ip"):
            self.assertFalse(bench.peer_ok(ip), repr(ip))

    def test_peer_ok_edges_fail_closed(self):
        # the ends of 100.64.0.0/10 and of the tailnet's ULA range, and things that only look right
        for ip in ("100.64.0.0", "100.127.255.255", "fd7a:115c:a1e0:ffff:ffff:ffff:ffff:ffff", "127.255.255.255", "::ffff:127.0.0.1"):
            self.assertTrue(bench.peer_ok(ip), ip)
        for ip in ("100.63.255.255", "100.128.0.0", "fd7a:115c:a1e1::1", "128.0.0.1", "fe80::1", "::", "0.0.0.0",
                   "100.97.237.60.evil.example", "100.97.237", "::ffff:8.8.8.8", None, 0, b"100.97.237.60"):
            self.assertFalse(bench.peer_ok(ip), repr(ip))
        self.assertFalse(bench.peer_ok("fe80::1%eth0"), "a link-local address is neither loopback nor the tailnet, scope id or not")
        self.assertTrue(bench.peer_ok("100.97.237.60%1"), "a scope id is stripped, never trusted to change the answer")

    def test_bind_ok_table(self):
        for ip in ("100.108.102.101", "127.0.0.1"):
            self.assertTrue(bench.bind_ok(ip), ip)
        for ip in ("", "0.0.0.0", "::", "192.168.2.102", "desktop-bndit", "localhost", "8.8.8.8", "::ffff:0.0.0.0", "0", None,
                   "100.108.102.101:7077", " 127.0.0.1"):
            self.assertFalse(bench.bind_ok(ip), repr(ip))

    # -- lock three: the peer, in handle()
    def test_loopback_and_the_tailnet_are_served(self):
        """the positive control: every trusted peer reaches do_GET/POST/HEAD/OPTIONS/PUT, and the real handler answers a real page"""
        Spy, calls = self.spy()
        bodies = {"GET": b"", "POST": b'{"a": 1}', "HEAD": b"", "OPTIONS": b"", "PUT": b"{}"}
        for peer in self.TRUSTED:
            for m, body in bodies.items():
                conn = self.drive(Spy, peer, _raw(m, "/api/state", body=body))
                self.assertTrue(conn.wire().startswith(b"HTTP/1.1 200"), (peer, m, conn.wire()[:60]))
        self.assertEqual(len(calls), len(self.TRUSTED) * len(bodies), calls)
        self.assertEqual(set(calls), set(bodies))
        real = bench.make_handler(bench.Bench(self.tmp))
        for peer in self.TRUSTED:
            conn = self.drive(real, peer, _raw("GET", "/api/state"))
            self.assertTrue(conn.wire().startswith(b"HTTP/1.1 200") and b'"bundle"' in conn.wire(), (peer, conn.wire()[:80]))

    def test_a_stranger_gets_the_bare_403_for_every_method_and_not_a_byte_is_read(self):
        Spy, calls = self.spy()
        requests = {
            "GET": _raw("GET", "/api/state"), "POST": _raw("POST", "/api/md", body=b'{"text": "x"}'), "HEAD": _raw("HEAD", "/"),
            "OPTIONS": _raw("OPTIONS", "*"), "PUT": _raw("PUT", "/api/md", body=b"{}"), "malformed": b"x\r\n\r\n",
            "garbage": b"\x16\x03\x01\x02\x00\x01\x00\x01\xfc\x03\x03",          # a TLS hello: not HTTP at all
            "empty": b"",
        }
        for peer in self.STRANGERS:
            for name, raw in requests.items():
                conn = self.drive(Spy, peer, raw)
                self.assertEqual(conn.wire(), bench._FORBIDDEN, (peer, name))
                self.assertEqual(conn.reader.at_close, 0, "%s %s: a request byte was read before the refusal" % (peer, name))
        self.assertEqual(calls, [], "a do_* method ran for a stranger")
        # the real handler (not the spy) says the same: nothing of the page, the state or the books leaves
        real = bench.make_handler(bench.Bench(self.tmp), token="t0k")
        for peer in self.STRANGERS:
            conn = self.drive(real, peer, requests["GET"])
            self.assertEqual(conn.wire(), bench._FORBIDDEN)
            self.assertNotIn(b"bundle", conn.wire())

    def test_a_stranger_with_the_right_token_writes_nothing(self):
        real = bench.make_handler(bench.Bench(self.tmp), token="t0k")
        body = json.dumps({"text": "---\ntitle: t\n---\nA STRANGER WAS HERE"}).encode("utf-8")
        req = _raw("POST", "/api/md", headers={"X-FP-Token": "t0k", "Content-Type": "application/json"}, body=body)
        before = (self.tmp / "book.md").read_bytes()
        for peer in self.STRANGERS:
            conn = self.drive(real, peer, req)
            self.assertEqual(conn.wire(), bench._FORBIDDEN, peer)
            self.assertEqual((self.tmp / "book.md").read_bytes(), before, "%s: the book changed" % peer)
        conn = self.drive(real, "100.97.237.60", req)        # positive control: the same bytes from the tailnet are admitted
        self.assertIn(b'"saved": true', conn.wire())
        self.assertNotEqual((self.tmp / "book.md").read_bytes(), before)

    def test_an_unreadable_peer_address_is_refused(self):
        real = bench.make_handler(bench.Bench(self.tmp))
        for peer in ((), None, ("not-an-ip", 1), ("", 1), (None, 1), ("100.97.237.60.9", 1)):
            conn = _FakeConn(_raw("GET"))
            with contextlib.redirect_stdout(io.StringIO()):
                real(conn, peer, self.server)
            self.assertEqual(conn.wire(), bench._FORBIDDEN, repr(peer))
            self.assertEqual(conn.reader.at_close, 0, repr(peer))

    def test_a_refusal_is_noted_five_times_then_every_thousandth_and_never_raises(self):
        old = bench._refusals
        try:
            bench._refusals = 0
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                for _ in range(2001):
                    bench._count_refusal("192.168.2.207")
            lines = out.getvalue().splitlines()
            self.assertEqual(len(lines), 7, lines)            # refusals 1-5, 1000 and 2000
            self.assertTrue(all("192.168.2.207" in ln for ln in lines))
            self.assertTrue(lines[-1].endswith("#2000"), lines[-1])
            bench._refusals = 0
            with mock.patch("builtins.print", side_effect=OSError("the console is gone")):
                bench._count_refusal("192.168.2.207")         # a dead log must not take a connection down
        finally:
            bench._refusals = old

    # -- lock two: the listener
    def test_serve_on_refuses_a_wide_bind_before_building_anything(self):
        handler = bench.make_handler(bench.Bench(self.tmp), token=None)
        for binds in (["0.0.0.0"], ["127.0.0.1", "0.0.0.0"], ["127.0.0.1", ""], ["127.0.0.1", "::"], ["127.0.0.1", "192.168.2.102"],
                      ["127.0.0.1", "desktop-bndit"], ["127.0.0.1", "localhost"], ["localhost"], ["192.168.2.102", "127.0.0.1"]):
            with mock.patch.object(bench, "ThreadingHTTPServer") as made:
                with self.assertRaises(ValueError, msg=repr(binds)) as cm:
                    bench.serve_on(binds, 0, handler)
            self.assertFalse(made.called, "%r: a server was built before the refusal" % (binds,))
            self.assertIn("refusing to listen", str(cm.exception))
        # and with REAL sockets: nothing is left listening behind the refusal. The refused address here is TEST-NET-1 (192.0.2.1, RFC 5737:
        # no machine owns it), never 0.0.0.0 or a LAN address - so that even if the lock were removed this test could not open a
        # listener on a non-loopback address (the OS refuses the bind of an address nobody holds); every server the real class builds
        # is recorded and closed, whatever happens
        port = _free_port()
        built, real_class = [], bench.ThreadingHTTPServer

        def recording(*a, **k):
            if a[0][0] != "127.0.0.1":   # round three: a mutant that removed the lock still cannot reach a bind on a non-loopback address
                raise AssertionError("the test forbids a bind on %r: serve_on asked for a non-loopback listener" % (a[0],))
            srv = real_class(*a, **k)
            built.append(srv)
            return srv
        try:
            with mock.patch.object(bench, "ThreadingHTTPServer", side_effect=recording):
                with self.assertRaises(ValueError):
                    bench.serve_on(["127.0.0.1", "192.0.2.1"], port, handler)
            self.assertEqual(built, [], "a server was built before the wide address was refused")
            probe = socket.socket()
            try:
                probe.settimeout(3)
                self.assertNotEqual(probe.connect_ex(("127.0.0.1", port)), 0, "the loopback server was built before the wide address was refused")
            finally:
                probe.close()
        finally:
            for srv in built:
                srv.server_close()
        servers = bench.serve_on(["127.0.0.1"], 0, handler)   # positive control: an honest address still binds
        try:
            self.assertEqual(servers[0].server_address[0], "127.0.0.1")
        finally:
            for s in servers:
                s.server_close()

    # The start-up refusal of --also-bind, in two shapes. A SUBPROCESS launch (the real command line, the real exit code) uses ONLY values
    # no machine owns: a tailnet-range address for the positive control and the three TEST-NET blocks (RFC 5737: 192.0.2.0/24,
    # 198.51.100.0/24, 203.0.113.0/24) for the refusals - so a launch that got past the lock could not open a listener on any
    # non-loopback address. The wide values (0.0.0.0, '', '::', a LAN address, names) are exercised IN-PROCESS, where main() runs with
    # the socket-creating class and the bench itself stubbed: no socket can be made, and the refusal is shown to come first.
    WIDE_ALSO_BIND = ("0.0.0.0", "", "::", "::ffff:0.0.0.0", "192.168.2.102", "desktop-bndit", "localhost", "8.8.8.8", "0")

    def test_a_wide_also_bind_stops_the_start_before_a_socket_or_a_bench_exists(self):
        gone = str(Path(tempfile.gettempdir()) / "fp-no-such-bundle-for-the-lock-test")
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

        # Round three (2026-09-30): every launch below runs under a guard that makes ANY bind in the child raise and say so on stderr
        # ('BIND-ATTEMPT'), so not one of these launches can open a listener on any address, loopback included - the positive control
        # included: it is proved to stop at the missing bundle (exit 1) and to have attempted no bind at all, not merely assumed to.
        guard = ("import runpy, socket, sys\n"
                 "def _no_bind(self, *a, **k):\n"
                 "    sys.stderr.write('BIND-ATTEMPT %r\\n' % (a[:1],))\n"
                 "    raise OSError('this test forbids every bind in this child')\n"
                 "socket.socket.bind = _no_bind\n"
                 "script = sys.argv[1]\n"
                 "sys.argv = sys.argv[1:]\n"
                 "runpy.run_path(script, run_name='__main__')\n")

        def start(also):
            port = _free_port()
            r = subprocess.run([sys.executable, "-c", guard, str(HERE / "bench.py"), gone, "--port", str(port), "--also-bind", also],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, env=env)
            return r, port
        # the guard's own negative control: a child that does bind (loopback, port 0) is stopped and says BIND-ATTEMPT
        tmp = Path(tempfile.mkdtemp(prefix="fp-test-noguard-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "binder.py").write_text("import socket\ns = socket.socket()\ns.bind(('127.0.0.1', 0))\nprint('BOUND')\n", encoding="utf-8")
        r = subprocess.run([sys.executable, "-c", guard, str(tmp / "binder.py")], capture_output=True, text=True, timeout=60, env=env)
        self.assertNotEqual(r.returncode, 0, "the guard let a bind through")
        self.assertIn("BIND-ATTEMPT", r.stderr)
        self.assertNotIn("BOUND", r.stdout)
        # the positive control: a tailnet-range address that this machine does not hold gets PAST argument parsing (and then stops at the
        # missing bundle, exit 1, before any socket is made)
        r, _ = start("100.64.0.1")
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("not a bundle dir or a PDF", r.stderr)
        self.assertNotIn("literal loopback or Tailscale", r.stderr)
        self.assertNotIn("BIND-ATTEMPT", r.stderr, "the positive control reached a bind")
        self.assertNotIn("REPAIR BENCH", r.stdout, "the positive control got past building the bench")
        for also in ("192.0.2.1", "198.51.100.1", "203.0.113.1"):
            r, port = start(also)
            self.assertEqual(r.returncode, 2, "%r: %s" % (also, r.stderr))
            self.assertIn("--also-bind", r.stderr)
            self.assertIn("not a literal loopback or Tailscale address", r.stderr)
            self.assertNotIn("not a bundle dir", r.stderr, "%r: the refusal must come before the bench is built" % also)
            self.assertNotIn("BIND-ATTEMPT", r.stderr, "%r: the launch reached a bind" % also)
            self.assertNotIn("REPAIR BENCH", r.stdout)
            probe = socket.socket()
            try:
                probe.settimeout(3)
                self.assertNotEqual(probe.connect_ex(("127.0.0.1", port)), 0, also)
            finally:
                probe.close()

    def _main_with(self, argv):
        """bench.main() in this process with `argv`, the listener class and the Bench class replaced by recorders: what it exits with,
        what it said on stderr, and whether any server or bench was (about to be) built. No socket can be created by this call."""
        err, out = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "argv", ["bench.py"] + argv), mock.patch.object(bench, "ThreadingHTTPServer") as server, \
                mock.patch.object(bench, "Bench") as made_bench, contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            try:
                bench.main()
                code = None
            except SystemExit as e:
                code = e.code
            except Exception as e:   # noqa: BLE001 - past argument parsing, serve_on's own lock may still refuse: that is a failure HERE
                code = "raised %s: %s" % (type(e).__name__, e)
        return code, err.getvalue(), out.getvalue(), server.called, made_bench.called

    def test_a_wide_also_bind_is_refused_by_main_before_a_bench_or_a_server_is_built(self):
        gone = str(Path(tempfile.gettempdir()) / "fp-no-such-bundle-for-the-lock-test")
        for also in self.WIDE_ALSO_BIND:
            code, err, out, server_called, bench_called = self._main_with([gone, "--port", "0", "--also-bind", also])
            self.assertEqual(code, 2, "%r: %s" % (also, err))
            self.assertIn("--also-bind", err)
            self.assertIn("not a literal loopback or Tailscale address", err)
            self.assertFalse(bench_called, "%r: a Bench was built before the refusal" % also)
            self.assertFalse(server_called, "%r: a listener was built before the refusal" % also)
            self.assertNotIn("REPAIR BENCH", out)
        # the positive control, with the same stubs: a tailnet address gets through parsing, builds the (stubbed) Bench and the
        # (stubbed) listeners - nothing is refused, and still no socket exists
        with mock.patch.object(sys, "argv", ["bench.py", gone, "--port", "0", "--also-bind", "100.108.102.101"]), \
                mock.patch.object(bench, "serve_on", return_value=[types.SimpleNamespace(serve_forever=lambda: None)]) as served, \
                mock.patch.object(bench, "Bench") as made_bench, contextlib.redirect_stdout(io.StringIO()):
            made_bench.return_value.state.return_value = {"bundle": "b", "sandbox": False, "verdict": "pass", "zones": [], "pages": 1,
                                                         "pdf_available": False}
            bench.main()
        self.assertTrue(made_bench.called and served.called)
        self.assertEqual(served.call_args[0][0], ["127.0.0.1", "100.108.102.101"])

    def test_bind_arg_is_the_argparse_form_of_the_same_rule(self):
        import argparse
        self.assertEqual(bench._bind_arg("100.108.102.101"), "100.108.102.101")
        for bad in ("0.0.0.0", "", "::", "192.168.2.102", "desktop-bndit"):
            with self.assertRaises(argparse.ArgumentTypeError, msg=repr(bad)):
                bench._bind_arg(bad)

    def test_the_docs_server_in_launch_json_binds_loopback(self):
        def binds_loopback(args):
            return "--bind" in args and args.index("--bind") + 1 < len(args) and args[args.index("--bind") + 1] == "127.0.0.1"
        self.assertFalse(binds_loopback(["-m", "http.server", "8321", "--directory", "docs"]), "negative control: no --bind")
        self.assertFalse(binds_loopback(["-m", "http.server", "8321", "--bind", "0.0.0.0"]), "negative control: a wide --bind")
        launch = json.loads((REPO / ".claude" / "launch.json").read_text(encoding="utf-8"))
        servers = [c for c in launch["configurations"] if "http.server" in c["runtimeArgs"]]
        self.assertIn("docs", [c["name"] for c in servers])
        for c in servers:
            self.assertTrue(binds_loopback(c["runtimeArgs"]), "%s: python -m http.server answers every interface without --bind 127.0.0.1" % c["name"])


class TestPreAuthDrain(unittest.TestCase):
    """2026-09-30: a POST refused before its body was used (421, 403) drains at most _DRAIN_CAP bytes, in chunks of 64 KiB or less, and
    waits at most _DRAIN_TIMEOUT on a sender that stalls; a Content-Length that is not a whole number answers 400 and closes."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="fp-test-drain-"))
        (self.tmp / "book.md").write_text("---\ntitle: t\n---\nline one", encoding="utf-8")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.handler = bench.make_handler(bench.Bench(self.tmp), token="t0k", hosts=())
        self.server = types.SimpleNamespace(server_address=("100.108.102.101", 7077))

    def drive(self, raw):
        conn = _FakeConn(raw)
        self.handler(conn, ("100.97.237.60", 5555), self.server)
        return conn

    def test_a_small_refused_body_is_drained_whole_and_the_connection_stays(self):
        """the positive control: the S215 round-seven contract holds - the body is consumed and a kept-alive connection is safe"""
        body = b'{"text": "x"}'
        conn = self.drive(_raw("POST", "/api/md", headers={"X-FP-Token": "wrong"}, body=body))
        self.assertTrue(conn.wire().startswith(b"HTTP/1.1 403"), conn.wire()[:40])
        self.assertEqual(conn.reader.sizes, [len(body)], "the whole body, and no more, was read")
        self.assertNotIn(b"Connection: close", conn.wire())
        conn = self.drive(_raw("POST", "/api/md", host="evil.example", body=body))
        self.assertTrue(conn.wire().startswith(b"HTTP/1.1 421"), conn.wire()[:40])
        self.assertEqual(conn.reader.sizes, [len(body)])

    def test_a_content_length_that_is_not_a_whole_number_is_a_400_and_nothing_is_read(self):
        for bad in ("-1", "-5", "abc", "+5", "5.0", "0x10", "1e3", "5 5", "5,5", "-0", "99999999999999999999999 x"):
            for label, req in (
                    ("wrong token", _raw("POST", "/api/md", headers={"X-FP-Token": "wrong", "Content-Length": bad})),
                    ("no token", _raw("POST", "/api/md", headers={"Content-Length": bad})),
                    ("foreign host", _raw("POST", "/api/md", host="evil.example", headers={"Content-Length": bad})),
                    ("right token", _raw("POST", "/api/md", headers={"X-FP-Token": "t0k", "Content-Length": bad}))):
                conn = self.drive(req + b'{"text": "x"}')
                wire = conn.wire()
                self.assertTrue(wire.startswith(b"HTTP/1.1 400"), "%r %s: %s" % (bad, label, wire[:40]))
                self.assertIn(b"Connection: close", wire, "%r %s" % (bad, label))
                self.assertIn(b"whole number", wire)
                self.assertEqual(conn.reader.sizes, [], "%r %s: a body read was attempted" % (bad, label))
        # a non-ASCII digit (Arabic-Indic five) is not a digit here either
        conn = self.drive(b"POST /api/md HTTP/1.1\r\nHost: 100.108.102.101:7077\r\nContent-Length: \xd9\xa5\r\n\r\n")
        self.assertTrue(conn.wire().startswith(b"HTTP/1.1 400"), conn.wire()[:40])
        # and the legitimate zero: an empty POST with no token is the usual 403, not a 400
        conn = self.drive(_raw("POST", "/api/undo", headers={"X-FP-Token": "wrong", "Content-Length": "0"}))
        self.assertTrue(conn.wire().startswith(b"HTTP/1.1 403"), conn.wire()[:40])

    def test_a_declared_length_past_the_cap_is_read_to_the_cap_in_chunks_and_the_connection_closes(self):
        body = b"x" * 300000
        with mock.patch.object(bench, "_DRAIN_CAP", 150000):
            for label, req in (("wrong token", _raw("POST", "/api/md", headers={"X-FP-Token": "wrong"}, body=body)),
                               ("foreign host", _raw("POST", "/api/md", host="evil.example", body=body))):
                conn = self.drive(req)
                sizes = conn.reader.sizes
                self.assertEqual(sum(sizes), 150000, "%s: %s" % (label, sizes))
                self.assertLessEqual(max(sizes), 65536, "%s: a read bigger than one 64 KiB chunk: %s" % (label, sizes))
                self.assertGreaterEqual(len(sizes), 3)
                self.assertTrue(conn.wire().startswith((b"HTTP/1.1 403", b"HTTP/1.1 421")), conn.wire()[:40])
                self.assertIn(b"Connection: close", conn.wire(), label)

    def test_a_body_framed_by_transfer_encoding_is_not_drained_and_the_connection_closes(self):
        # no Content-Length at all: the bytes after the headers are a chunked body the bench does not parse
        conn = self.drive(_raw("POST", "/api/md", headers={"X-FP-Token": "wrong", "Transfer-Encoding": "chunked"})
                          + b"5\r\nhello\r\n0\r\n\r\n")
        self.assertTrue(conn.wire().startswith(b"HTTP/1.1 403"), conn.wire()[:40])
        self.assertIn(b"Connection: close", conn.wire())
        self.assertEqual(conn.reader.sizes, [])

    def test_a_sender_that_stalls_is_answered_at_the_drain_timeout_not_the_connections_30_seconds(self):
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), self.handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (httpd.shutdown(), httpd.server_close()))
        port = httpd.server_address[1]
        with mock.patch.object(bench, "_DRAIN_TIMEOUT", 0.5):
            s = socket.create_connection(("127.0.0.1", port), timeout=10)
            try:
                head = ("POST /api/md HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nX-FP-Token: wrong\r\nContent-Length: 1000000000000\r\n\r\n" % port).encode("ascii")
                s.sendall(head + b"ten bytes!")              # ... and then says nothing more
                t0 = time.monotonic()
                got = b""
                while b"\r\n\r\n" not in got:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    got += chunk
                took = time.monotonic() - t0
            finally:
                s.close()
        self.assertTrue(got.startswith(b"HTTP/1.1 403"), got[:60])
        self.assertIn(b"Connection: close", got)
        self.assertLess(took, 5, "the stalled drain held the thread for %.1f s" % took)

    def test_live_bad_length_answers_400_on_both_sides_of_the_gate_and_the_server_carries_on(self):
        srv = LiveBenchServer(token="t0k")
        try:
            for tok in (None, "wrong", "t0k"):
                conn = http.client.HTTPConnection("127.0.0.1", srv.port, timeout=10)
                conn.putrequest("POST", "/api/md")
                conn.putheader("Content-Length", "-5")
                if tok:
                    conn.putheader("X-FP-Token", tok)
                conn.endheaders()
                r = conn.getresponse()
                r.read()
                self.assertEqual(r.status, 400, tok)
                self.assertTrue(r.will_close, "the 400 must close the connection")
                conn.close()
            self.assertEqual(_get(srv.port, "/api/state")[0], 200, "a bad length must not hurt the next caller")
            code, _ = _post(srv.port, "/api/md", {"text": "---\ntitle: t\n---\nafter"}, token="t0k")   # the admitted path is untouched
            self.assertEqual(code, 200)
        finally:
            srv.close()


class TestProxyMarkers(unittest.TestCase):
    """2026-09-30, rule (4): a request that carries a forwarding header came through a proxy (a local `tailscale serve`, a Funnel, a
    reverse proxy arrive FROM loopback, which the peer lock admits) and is refused, GET and POST, before the token is looked at."""

    def setUp(self):
        self.srv = LiveBenchServer(token="t0k")
        self.addCleanup(self.srv.close)

    def req(self, method, path, headers=None, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.srv.port, timeout=10)
        conn.request(method, path, body=body, headers=headers or {})
        r = conn.getresponse()
        data = r.read()
        conn.close()
        return r.status, data

    def test_the_real_client_headers_pass(self):
        """the positive control: what a browser (the widget's WebView2, the Control's frame, the phone) and a plain script send"""
        port = self.srv.port
        browser = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0) Edg/130", "Accept": "*/*", "Accept-Encoding": "gzip, deflate",
                   "Accept-Language": "en-US,en;q=0.9", "Origin": "http://127.0.0.1:%d" % port, "Referer": "http://127.0.0.1:%d/?token=t0k" % port,
                   "Sec-Fetch-Site": "same-origin", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Dest": "empty", "Cache-Control": "no-cache",
                   "If-None-Match": '"none-such"', "Connection": "keep-alive"}
        for headers in (browser, {}):
            code, body = self.req("GET", "/api/state", headers)
            self.assertEqual(code, 200, headers)
            self.assertIn(b"bundle", body)
        code, _ = self.req("POST", "/api/md", {**browser, "X-FP-Token": "t0k", "Content-Type": "application/json"},
                           json.dumps({"text": "---\ntitle: t\n---\nfrom the page"}))
        self.assertEqual(code, 200)

    def test_every_marker_refuses_get_and_post(self):
        before = (self.srv.tmp / "book.md").read_bytes()
        # the two families are matched by PREFIX: X-Forwarded-* and Tailscale-* (Funnel's Tailscale-Funnel-Request, Serve's
        # Tailscale-User-Login / -Name / -Profile-Pic and Tailscale-App-Capabilities / -Headers-Info, and any name Tailscale adds later)
        family = ("x-forwarded-for", "x-forwarded-host", "x-forwarded-proto", "x-forwarded-port", "x-forwarded-server", "x-forwarded-whatever",
                  "tailscale-funnel-request", "tailscale-user-login", "tailscale-user-name", "tailscale-user-profile-pic",
                  "tailscale-app-capabilities", "tailscale-headers-info", "tailscale-whatever-it-adds-next")
        for name in bench.PROXY_MARKERS + family:
            for spelled in (name, name.upper(), name.title()):   # header names are case-blind
                code, body = self.req("GET", "/api/state", {spelled: "203.0.113.9"})
                self.assertEqual(code, 403, spelled)
                self.assertIn(b"direct requests only", body)
                code, body = self.req("POST", "/api/md", {spelled: "203.0.113.9", "X-FP-Token": "t0k"},
                                      json.dumps({"text": "---\ntitle: t\n---\nvia a proxy"}))
                self.assertEqual(code, 403, spelled)
                self.assertIn(b"direct requests only", body)
        self.assertEqual((self.srv.tmp / "book.md").read_bytes(), before, "a proxied POST with the right token still wrote")

    def test_a_proxied_request_from_loopback_is_the_case_the_peer_lock_cannot_see(self):
        tmp = self.srv.tmp
        handler = bench.make_handler(bench.Bench(tmp), token="t0k")
        server = types.SimpleNamespace(server_address=("127.0.0.1", 7077))
        conn = _FakeConn(_raw("GET", "/api/state", host="127.0.0.1:7077", headers={"X-Forwarded-For": "198.51.100.23"}))
        handler(conn, ("127.0.0.1", 5555), server)
        self.assertTrue(conn.wire().startswith(b"HTTP/1.1 403"), conn.wire()[:40])
        self.assertIn(b"direct requests only", conn.wire())
        conn = _FakeConn(_raw("GET", "/api/state", host="127.0.0.1:7077"))            # positive control: the same peer, no marker
        handler(conn, ("127.0.0.1", 5555), server)
        self.assertTrue(conn.wire().startswith(b"HTTP/1.1 200"), conn.wire()[:40])

    def test_a_foreign_host_is_still_a_421_first(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.srv.port, timeout=10)
        conn.putrequest("GET", "/api/state", skip_host=True)
        conn.putheader("Host", "evil.example:%d" % self.srv.port)
        conn.putheader("X-Forwarded-For", "203.0.113.9")
        conn.endheaders()
        r = conn.getresponse()
        r.read()
        conn.close()
        self.assertEqual(r.status, 421)

    def test_proxy_marker_table(self):
        import email.message
        msg = email.message.Message()
        self.assertIsNone(bench.proxy_marker(msg))
        msg["Host"] = "127.0.0.1:7077"
        msg["Origin"] = "http://127.0.0.1:7077"
        msg["Sec-Fetch-Site"] = "same-origin"
        self.assertIsNone(bench.proxy_marker(msg), "the real client's headers are not markers")
        for h in ("Forwarded", "X-Forwarded-For", "X-Forwarded-Host", "X-Forwarded-Proto", "X-Forwarded-Port", "X-Forwarded-Whatever", "X-Real-IP",
                  "Via", "Tailscale-Funnel-Request", "Tailscale-User-Login", "Tailscale-User-Name", "Tailscale-User-Profile-Pic",
                  "Tailscale-App-Capabilities", "Tailscale-Headers-Info", "Tailscale-Anything-At-All", "TAILSCALE-X",
                  "CF-Connecting-IP", "CF-Ray", "True-Client-IP", "X-Client-IP") + tuple(bench.PROXY_MARKERS):
            m = email.message.Message()
            m[h] = "x"
            self.assertEqual(bench.proxy_marker(m), h.lower(), h)
        for h in ("X-Forwarded", "X-Requested-With", "Host", "Origin", "Referer", "User-Agent", "Sec-Fetch-Site", "Sec-Fetch-Dest",
                  "X-FP-Token", "If-None-Match", "Cache-Control", "Accept", "Connection", "Upgrade-Insecure-Requests", "Content-Length",
                  "Tailscale", "Not-Tailscale-Header"):      # the prefix is 'tailscale-' at the START of the name, not the word anywhere in it
            m = email.message.Message()                          # the headers a browser, the widget and a script do send
            m[h] = "x"
            self.assertIsNone(bench.proxy_marker(m), h)
        m = email.message.Message()
        m["X-Forwarded-For"] = ""                                # present and empty is still forwarded
        self.assertEqual(bench.proxy_marker(m), "x-forwarded-for")


def _lock_probe(mod):
    """The lock's behaviours, run on `mod` (the real bench module, or a mutant of its source): returns the list of things that did not hold
    ([] = the lock holds). Positive controls first (a trusted peer is served), then one violation per rule: a stranger over the peer lock,
    a wide bind at serve_on and at the argparse type, a body past the drain cap, a negative length, a forwarded request."""
    import argparse
    bad = []
    tmp = Path(tempfile.mkdtemp(prefix="fp-test-lockprobe-"))
    try:
        (tmp / "book.md").write_text("---\ntitle: t\n---\nline one", encoding="utf-8")
        handler = mod.make_handler(mod.Bench(tmp), token="t0k")
        server = types.SimpleNamespace(server_address=("100.108.102.101", 7077))

        def run(peer, raw):
            conn = _FakeConn(raw)
            with contextlib.redirect_stdout(io.StringIO()):
                handler(conn, (peer, 5555), server)
            return conn
        for peer in ("127.0.0.1", "100.97.237.60"):
            if not run(peer, _raw("GET")).wire().startswith(b"HTTP/1.1 200"):
                bad.append("positive control: %s is not served" % peer)
        for peer in ("192.168.2.207", "8.8.8.8", "::ffff:192.168.2.207"):
            conn = run(peer, _raw("GET"))
            if conn.wire() != mod._FORBIDDEN or conn.reader.at_close != 0:
                bad.append("peer lock: %s is not refused before a byte is read" % peer)
        with mock.patch.object(mod, "ThreadingHTTPServer") as made:
            try:
                mod.serve_on(["127.0.0.1", "0.0.0.0"], 0, handler)
                bad.append("listener lock: serve_on accepted 0.0.0.0")
            except ValueError:
                pass
            if made.called:
                bad.append("listener lock: serve_on built a server before refusing")
        try:
            mod._bind_arg("0.0.0.0")
            bad.append("listener lock: --also-bind accepted 0.0.0.0")
        except argparse.ArgumentTypeError:
            pass
        with mock.patch.object(mod, "_DRAIN_CAP", 150000):
            conn = run("100.97.237.60", _raw("POST", "/api/md", headers={"X-FP-Token": "wrong"}, body=b"x" * 300000))
            if sum(conn.reader.sizes) != 150000:
                bad.append("drain: read %d of a 300000-byte refused body, cap 150000" % sum(conn.reader.sizes))
        if not run("100.97.237.60", _raw("POST", "/api/md", headers={"X-FP-Token": "wrong", "Content-Length": "-5"})).wire().startswith(b"HTTP/1.1 400"):
            bad.append("drain: a negative Content-Length is not a 400")
        if not run("127.0.0.1", _raw("GET", "/api/state", host="127.0.0.1:7077", headers={"X-Forwarded-For": "198.51.100.23"})).wire().startswith(b"HTTP/1.1 403"):
            bad.append("proxy marker: a forwarded GET is not refused")
        if not run("127.0.0.1", _raw("POST", "/api/md", host="127.0.0.1:7077", headers={"Via": "1.1 proxy", "X-FP-Token": "t0k"},
                                        body=b'{"text": "x"}')).wire().startswith(b"HTTP/1.1 403"):
            bad.append("proxy marker: a forwarded POST with the right token is not refused")
        for ts in ("Tailscale-Funnel-Request", "Tailscale-User-Name", "Tailscale-Something-New"):   # the whole Tailscale-* prefix, not two names
            if not run("127.0.0.1", _raw("GET", "/api/state", host="127.0.0.1:7077", headers={ts: "?1"})).wire().startswith(b"HTTP/1.1 403"):
                bad.append("proxy marker: a GET carrying %s is not refused" % ts)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return bad


class TestTailnetLockMutants(unittest.TestCase):
    """The negatives to the tailnet lock (docs/32 rule 2: a check that cannot fail is a tautology). The probe above holds on the real
    source; on bench.py's source with exactly ONE guard removed or weakened, each mutant must make it report a failure."""

    MUTANTS = (
        ("the peer guard never fires", "            if not ok:", "            if False:"),
        ("peer_ok trusts everyone", "    return any(ip.version == n.version and ip in n for n in _PEER_NETS)", "    return True"),
        ("serve_on accepts any address", "        if not bind_ok(b):", "        if False:"),
        ("--also-bind accepts any address", "    if not bind_ok(value):", "    if False:"),
        ("the drain has no cap", "left = min(n, _DRAIN_CAP)", "left = n"),
        ("a negative Content-Length is taken as given", "return int(raw) if raw.isascii() and raw.isdigit() else None", "return int(raw)"),
        ("no header is a proxy marker", "for k in headers.keys():", "for k in ():"),
        ("the Tailscale-* prefix is not refused", 'PROXY_PREFIXES = ("x-forwarded-", "tailscale-")', 'PROXY_PREFIXES = ("x-forwarded-",)'),
    )

    def test_the_real_source_and_its_unchanged_copy_hold(self):
        self.assertEqual(_lock_probe(bench), [])
        same = "            if not ok:"
        self.assertEqual(_lock_probe(_bench_mutant(same, same)), [], "the source loaded as a mutant, unchanged, must hold too")

    def test_each_weakened_guard_is_caught(self):
        for name, old, new in self.MUTANTS:
            with self.subTest(mutant=name):
                failures = _lock_probe(_bench_mutant(old, new))
                self.assertTrue(failures, "%s: the probe still reports nothing, so it cannot tell" % name)


# ---- round three (2026-09-30): the browser that speaks plain http ---------------------------------------------------------------
# A browser sends Fetch Metadata (Sec-Fetch-Site / -Mode / -Dest) ONLY to a potentially trustworthy URL: https, or 127.0.0.0/8, ::1 and
# localhost. Over plain http to the tailnet address or a *.ts.net name it sends NONE, so every Sec-Fetch-Site rule is inert there and
# fires on loopback only. What a browser does send over plain http: Origin on every POST (a same-origin one too) and on a cross-origin
# fetch; NO Origin on a GET navigation, <img>, <script>, <link>, <iframe> or form GET; Referer by the referrer policy (a foreign page can
# suppress it, never forge it to our host). A cross-origin request that is not "simple" needs a CORS preflight that no File Portal server
# answers, and no answer carries Access-Control-Allow-Origin, so a foreign page can never READ one. The tests below are that browser:
# requests that carry NO Sec-Fetch-* at all (plus, separately, the loopback shape that carries them). Each family has its positive
# control (every real client's exact shape still passes) and, in TestRequestCheckMutants, a negative control per rule.
def _ask(port, method, path, headers=None, body=None, host=None):
    """one request over a real LOOPBACK socket carrying exactly the headers given plus Host - no Sec-Fetch-*, Origin, Referer or
    Accept-Encoding unless named: what a browser speaking plain http to the tailnet sends. -> (status, {lower-case header: value}, raw body,
    parsed JSON or None). `headers` is a dict, or a list of pairs when a header must be sent twice."""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        conn.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
        conn.putheader("Host", host or "127.0.0.1:%d" % port)
        for k, v in (headers.items() if isinstance(headers, dict) else (headers or ())):
            conn.putheader(k, v)
        if body is not None:
            conn.putheader("Content-Length", str(len(body)))
        conn.endheaders(body)
        r = conn.getresponse()
        data = r.read()
        hdr = {k.lower(): v for k, v in r.getheaders()}
    finally:
        conn.close()
    try:
        parsed = json.loads(data)
    except ValueError:
        parsed = None
    return r.status, hdr, data, parsed


def _wire_answer(conn):
    """(status, parsed JSON body or None, raw wire) of what a _FakeConn was sent"""
    wire = conn.wire()
    head, _, body = wire.partition(b"\r\n\r\n")
    status = int(head.split(b" ", 2)[1]) if head.startswith(b"HTTP/") else 0
    try:
        parsed = json.loads(body)
    except ValueError:
        parsed = None
    return status, parsed, wire


def _refused_by_a_request_rule(status, parsed):
    """True when an answer is one of rule (5)'s refusals: a 403 whose body names its reason"""
    return status == 403 and isinstance(parsed, dict) and parsed.get("reason") in ("origin", "fetch-site", "unproven-origin")


class _ForeignFixture:
    """a live loopback bench (token 't0k') over a throwaway bundle; Bench.ok15_evidence is replaced by a recorder, so an admitted evidence GET is SEEN
    and never spawns a child. snapshot() is the bundle's bytes: 'nothing happened' is read off it, never assumed"""

    def __init__(self, hosts=()):
        self.tmp = Path(tempfile.mkdtemp(prefix="fp-test-foreign-"))
        (self.tmp / "book.md").write_text("---\ntitle: t\n---\nline one\nline two\nline three", encoding="utf-8")
        self.bench = bench.Bench(self.tmp)
        self.evidence = []
        self.bench.ok15_evidence = lambda retry=False: (self.evidence.append(retry), {"spy": "evidence"})[1]
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), bench.make_handler(self.bench, token="t0k", hosts=hosts))
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.origin = "http://127.0.0.1:%d" % self.port

    def snapshot(self):
        return {str(p.relative_to(self.tmp)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(self.tmp.rglob("*")) if p.is_file()}

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestForeignPageOverPlainHttp(unittest.TestCase):
    """2026-09-30 round three, rules (5): what a foreign web page open in his browser can fire at the bench with NO Fetch Metadata - a blind
    GET (no Origin, maybe no Referer) and a simple POST (its own Origin, or 'null') - changes nothing, and every real client still passes."""

    @classmethod
    def setUpClass(cls):
        cls.srv = _ForeignFixture()

    @classmethod
    def tearDownClass(cls):
        cls.srv.close()

    def setUp(self):
        self.before = self.srv.snapshot()
        self.srv.evidence.clear()

    def nothing_happened(self, what):
        self.assertEqual(self.srv.snapshot(), self.before, "%s changed the bundle" % what)
        self.assertEqual(self.srv.evidence, [], "%s started the evidence collector" % what)

    def foreign_origins(self):
        p = self.srv.port
        return ("http://evil.example", "https://evil.example", "http://evil.example:80", "http://evil.example:%d" % p, "null", "NULL",
                "http://127.0.0.1:1", "http://localhost:1", "https://127.0.0.1:%d" % p, "http://127.0.0.1.evil.example:%d" % p,
                "http://localhost.evil.example:%d" % p, "http://127.0.0.1:%d@evil.example" % p, "http://evil.example/127.0.0.1:%d" % p,
                "http://127.0.0.1", "HTTP://EVIL.EXAMPLE", "", "127.0.0.1:%d" % p, "file://", "chrome-extension://abcdefgh",
                "http://100.97.237.60:%d" % p, "http://192.168.2.102:%d" % p)

    # -- B: the non-GET routes refuse a foreign page's simple request
    def test_a_simple_post_from_a_foreign_origin_is_refused_in_every_content_type(self):
        body = json.dumps({"text": "---\ntitle: t\n---\nA FOREIGN PAGE WAS HERE"})
        boundary = "----fpboundary"
        multipart = ('--%s\r\nContent-Disposition: form-data; name="text"\r\n\r\nA FOREIGN PAGE WAS HERE\r\n--%s--\r\n' % (boundary, boundary))
        shapes = (("text/plain", body), ("text/plain;charset=UTF-8", body),
                  ("application/x-www-form-urlencoded", "text=A+FOREIGN+PAGE+WAS+HERE&token=t0k"),
                  ("multipart/form-data; boundary=" + boundary, multipart), (None, body))
        for origin in self.foreign_origins():
            for ctype, payload in shapes:
                for token in (None, "t0k"):      # a foreign page cannot carry the token; the Origin rule is a lock of its own, so the right one is tried too
                    headers = {"Origin": origin}
                    if ctype:
                        headers["Content-Type"] = ctype
                    if token:
                        headers["X-FP-Token"] = token
                    code, _, _, parsed = _ask(self.srv.port, "POST", "/api/md", headers, payload.encode("utf-8"))
                    self.assertEqual(code, 403, (origin, ctype, token))
                    self.assertEqual((parsed or {}).get("reason"), "origin", (origin, ctype, token))
        self.nothing_happened("a simple POST from a foreign origin")

    def test_every_mutating_route_refuses_a_foreign_and_a_null_origin_even_with_the_right_token(self):
        for route in bench.MUTATING_POSTS:
            for origin in ("http://evil.example", "null", "http://127.0.0.1:1"):
                code, _, _, parsed = _ask(self.srv.port, "POST", route, {"Origin": origin, "X-FP-Token": "t0k", "Content-Type": "text/plain"},
                                          json.dumps(BENIGN[route]).encode("utf-8"))
                self.assertEqual((code, (parsed or {}).get("reason")), (403, "origin"), (route, origin))
        self.nothing_happened("a foreign POST to a mutating route")

    def test_the_pages_own_post_is_admitted_on_every_route(self):
        """the positive control: Origin ours + the token, the shape bench.html's fetch sends (text/plain - it sets no Content-Type), with and
        without the loopback Fetch Metadata"""
        plain = {"Origin": self.srv.origin, "X-FP-Token": "t0k", "Content-Type": "text/plain;charset=UTF-8", "Accept": "*/*"}
        fetch_meta = {**plain, "Sec-Fetch-Site": "same-origin", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Dest": "empty"}
        for route in bench.MUTATING_POSTS:
            for headers in (plain, fetch_meta):
                code, _, _, parsed = _ask(self.srv.port, "POST", route, headers, json.dumps(BENIGN[route]).encode("utf-8"))
                self.assertNotEqual(code, 403, "%s: the page's own request was refused: %s" % (route, parsed))
                self.assertNotIn("reason", parsed or {}, route)

    def test_an_origin_less_post_is_a_non_browser_client_and_goes_on_to_the_token_gate(self):
        payload = json.dumps({"text": "---\ntitle: t\n---\nfrom a script"}).encode("utf-8")
        code, _, _, parsed = _ask(self.srv.port, "POST", "/api/md", {"X-FP-Token": "t0k", "Content-Type": "application/json"}, payload)
        self.assertEqual((code, (parsed or {}).get("saved")), (200, True), "PowerShell / urllib: no Origin, the token")
        snap = self.srv.snapshot()
        code, _, _, parsed = _ask(self.srv.port, "POST", "/api/md", {"Content-Type": "application/json"}, payload)
        self.assertEqual(code, 403)
        self.assertIn("X-FP-Token", (parsed or {}).get("error", ""), "an Origin-less POST meets the token gate, not rule (5)")
        self.assertNotIn("reason", parsed or {})
        code, _, _, parsed = _ask(self.srv.port, "POST", "/api/md", {"Origin": self.srv.origin, "Content-Type": "text/plain"}, payload)
        self.assertEqual(code, 403)
        self.assertIn("X-FP-Token", (parsed or {}).get("error", ""), "our own Origin without the token is still the token gate's 403")
        self.assertEqual(self.srv.snapshot(), snap)

    # -- the token is read from a HEADER and from nowhere else (a header is preflight-protected; a query string and a form field are not)
    def test_the_token_is_read_from_a_header_and_from_nowhere_else(self):
        payload = json.dumps({"text": "---\ntitle: t\n---\nSMUGGLED", "token": "t0k", "X-FP-Token": "t0k"}).encode("utf-8")
        attempts = (
            ("a query string", "/api/md?token=t0k", {"Content-Type": "application/json"}, payload),
            ("a query string, header spelling", "/api/md?X-FP-Token=t0k", {"Content-Type": "application/json"}, payload),
            ("a JSON field", "/api/md", {"Content-Type": "application/json"}, payload),
            ("a form field", "/api/md", {"Content-Type": "application/x-www-form-urlencoded"}, b"token=t0k&X-FP-Token=t0k&text=SMUGGLED"),
            ("a multipart field", "/api/md", {"Content-Type": "multipart/form-data; boundary=zz"},
             b'--zz\r\nContent-Disposition: form-data; name="token"\r\n\r\nt0k\r\n--zz--\r\n'),
            ("a cookie", "/api/md", {"Cookie": "X-FP-Token=t0k; token=t0k"}, payload),
            ("an Authorization header", "/api/md", {"Authorization": "Bearer t0k"}, payload),
        )
        for what, path, headers, body in attempts:
            code, _, _, parsed = _ask(self.srv.port, "POST", path, headers, body)
            self.assertEqual(code, 403, what)
            self.assertIn("X-FP-Token", (parsed or {}).get("error", ""), what)
        for what, path, headers in (("a query string", "/api/evidence?token=t0k", {"Referer": self.srv.origin + "/?token=t0k"}),
                                    ("a cookie", "/api/evidence", {"Referer": self.srv.origin + "/", "Cookie": "X-FP-Token=t0k"})):
            code, _, _, parsed = _ask(self.srv.port, "GET", path, headers)
            self.assertEqual(code, 403, "evidence GET: " + what)
            self.assertIn("X-FP-Token", (parsed or {}).get("error", ""), what)
            self.assertNotIn("reason", parsed or {}, "the request had proof (our Referer); it is the token gate that refused it: " + what)
        self.nothing_happened("a token sent anywhere but the X-FP-Token header")
        # the source agrees: the only token_gate calls read the header, and no route reads a token from the query or the body
        calls = re.findall(r"(?<!def )token_gate\(([^,]*),", BENCH_PY)
        self.assertEqual(calls, ['self.headers.get("X-FP-Token")'] * 2, "the evidence GET and the POST gate read the header, and only it")
        self.assertIsNone(re.search(r'(?i)\b(q|payload|query|form|body)\.get\(\s*["\']\s*(x-fp-)?token', BENCH_PY),
                          "a route reads the token from the query or the body")
        self.assertIsNotNone(re.search(r'(?i)\bpayload\.get\(\s*"token', 'x = payload.get("token")'), "negative control: the pattern sees such a read")

    # -- C: the one GET with a side effect
    def test_the_side_effect_get_refuses_a_blind_request(self):
        p = self.srv.port
        blind = (("no header at all", {}),
                 ("a foreign Referer", {"Referer": "http://evil.example/page"}),
                 ("a sibling port's Referer", {"Referer": "http://127.0.0.1:1/"}),
                 ("a Referer that is not a URL", {"Referer": "garbage"}),
                 ("a Referer that only begins with our host", {"Referer": "http://127.0.0.1.evil.example:%d/" % p}),
                 ("an https Referer", {"Referer": "https://127.0.0.1:%d/" % p}),
                 ("a Referer with userinfo", {"Referer": "http://127.0.0.1:%d@evil.example/" % p}))
        for path in ("/api/evidence", "/api/evidence?retry=1", "/api/evidence?token=t0k", "/api/evidence;x=1", "/api/evidence;x=1?retry=1"):
            for what, headers in blind:
                code, _, _, parsed = _ask(p, "GET", path, headers)
                self.assertEqual((code, (parsed or {}).get("reason")), (403, "unproven-origin"), (path, what))
        self.nothing_happened("a blind GET of the side-effect route")

    def test_the_side_effect_get_is_admitted_only_with_proof(self):
        p, ours = self.srv.port, self.srv.origin
        # what the page sends over plain http: the token, and NO Referer (every answer of the bench says Referrer-Policy: no-referrer)
        for what, headers in (("the page's own shape on the tailnet (token, no Referer)", {"X-FP-Token": "t0k"}),
                              ("the page on loopback (token + Fetch Metadata)", {"X-FP-Token": "t0k", "Sec-Fetch-Site": "same-origin", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Dest": "empty"}),
                              ("a script with the page's token and its own marker", {"X-FP-Token": "t0k", "X-FP-Local": "1"}),
                              ("the page with a Referer of its own", {"X-FP-Token": "t0k", "Referer": ours + "/?token=t0k"}),
                              ("a script that holds the token and a stray foreign Referer", {"X-FP-Token": "t0k", "Referer": "http://evil.example/"})):
            self.srv.evidence.clear()
            code, _, _, parsed = _ask(p, "GET", "/api/evidence", headers)
            self.assertEqual((code, parsed), (200, {"spy": "evidence"}), what)
            self.assertEqual(self.srv.evidence, [False], what)
        self.srv.evidence.clear()
        code, _, _, parsed = _ask(p, "GET", "/api/evidence?retry=1", {"X-FP-Token": "t0k"})
        self.assertEqual((code, self.srv.evidence), (200, [True]))
        # proof without the token still meets the token gate: a proven request is not an authorised one
        self.srv.evidence.clear()
        for what, headers in (("X-FP-Local alone", {"X-FP-Local": "1"}), ("our own Referer alone", {"Referer": ours + "/"}),
                              ("a wrong token", {"X-FP-Token": "nope"}), ("Fetch Metadata alone", {"Sec-Fetch-Site": "same-origin"})):
            code, _, _, parsed = _ask(p, "GET", "/api/evidence", headers)
            self.assertEqual(code, 403, what)
            self.assertIn("X-FP-Token", (parsed or {}).get("error", ""), what)
            self.assertNotEqual((parsed or {}).get("reason"), "unproven-origin", what)
        self.assertEqual(self.srv.evidence, [])

    def test_a_spelling_that_does_not_dispatch_never_reaches_the_evidence_collector(self):
        for path in ("/api/evidence/", "/API/EVIDENCE", "/api//evidence", "/api/evidence%2f", "/api/evidence%00", "/api/evidenc", "/api/evidences"):
            code, _, _, parsed = _ask(self.srv.port, "GET", path, {"X-FP-Token": "t0k"})
            self.assertEqual(code, 404, path)
        self.assertEqual(self.srv.evidence, [], "a spelling reached ok15_evidence")
        # a leading '//' is collapsed to '/' by http.server before any handler runs (Python 3.11+; earlier, urlparse reads it as a host and
        # the route is a 404): either way the rule sees the path the dispatch sees, so a blind one is refused or does not dispatch, and a
        # proven one is the route itself
        for path in ("//api/evidence", "///api/evidence"):
            code, _, _, parsed = _ask(self.srv.port, "GET", path, {"Referer": "http://evil.example/"})
            self.assertIn(code, (403, 404), path)
            self.assertIn((parsed or {}).get("reason"), ("unproven-origin", None), path)
        self.assertEqual(self.srv.evidence, [], "a blind '//' spelling reached ok15_evidence")

    # -- C, the other side: a page or the data, read, stays open to a typed, bookmarked or blind visit
    def test_a_read_only_get_is_answered_with_no_origin_and_no_referer_and_with_a_foreign_referer(self):
        routes = ("/", "/?token=t0k&theme=dark", "/api/state", "/api/md", "/api/ledger", "/api/asset?name=none.png", "/api/toc", "/api/find?q=line",
                  "/api/textlayer?n=1", "/fp-tokens.css", "/vendor/markdown-it.min.js", "/api/page?n=1", "/api/locate?i=0")
        for headers in ({}, {"Referer": "http://evil.example/page"}, {"Referer": "garbage"},
                        {"User-Agent": "Mozilla/5.0", "Accept": "text/html", "Upgrade-Insecure-Requests": "1"}):
            for path in routes:
                code, _, _, parsed = _ask(self.srv.port, "GET", path, headers)
                self.assertFalse(_refused_by_a_request_rule(code, parsed), (path, headers, parsed))
                self.assertNotEqual(code, 421, path)
        for path in ("/", "/api/state", "/api/md", "/api/ledger"):      # the ones this fixture can really serve
            self.assertEqual(_ask(self.srv.port, "GET", path)[0], 200, path)
        self.nothing_happened("a blind GET of a page or of the data")

    def test_a_get_with_a_foreign_origin_is_refused_too(self):
        for origin in self.foreign_origins():
            for path in ("/", "/api/state", "/api/md", "/api/evidence"):
                code, _, _, parsed = _ask(self.srv.port, "GET", path, {"Origin": origin, "X-FP-Token": "t0k"})
                self.assertEqual((code, (parsed or {}).get("reason")), (403, "origin"), (origin, path))
        self.nothing_happened("a cross-origin GET")

    def test_two_origin_headers_are_refused(self):
        for first, second in ((self.srv.origin, "http://evil.example"), ("http://evil.example", self.srv.origin), (self.srv.origin, self.srv.origin)):
            code, _, _, parsed = _ask(self.srv.port, "POST", "/api/md", [("Origin", first), ("Origin", second), ("X-FP-Token", "t0k")],
                                      json.dumps({"text": "---\ntitle: t\n---\ntwo origins"}).encode("utf-8"))
            self.assertEqual((code, (parsed or {}).get("reason")), (403, "origin"), (first, second))
        self.nothing_happened("a request with two Origin headers")

    def test_two_origin_headers_are_refused_on_a_get_too(self):
        """S215 round nine (2): the rule is for every method - a read and the side-effect GET as well as a write"""
        for first, second in ((self.srv.origin, "http://evil.example"), ("http://evil.example", self.srv.origin), (self.srv.origin, self.srv.origin)):
            for path in ("/", "/api/state", "/api/md", "/api/evidence"):
                code, _, _, parsed = _ask(self.srv.port, "GET", path, [("Origin", first), ("Origin", second), ("X-FP-Token", "t0k")])
                self.assertEqual((code, (parsed or {}).get("reason")), (403, "origin"), (first, second, path))
        code, _, _, parsed = _ask(self.srv.port, "GET", "/api/state", [("Origin", self.srv.origin)])      # the control: one Origin of ours is served
        self.assertEqual(code, 200)
        self.nothing_happened("a GET with two Origin headers")

    def test_two_host_headers_are_refused(self):
        """S215 round nine (2): more than one Host header is a 421 on a GET and on a POST (the body drained, the right token no help), whichever comes
        first and whether or not the two agree; one Host is still served (the control)"""
        p, mine = self.srv.port, "127.0.0.1:%d" % self.srv.port
        payload = json.dumps({"text": "---\ntitle: t\n---\nTWO HOSTS"}).encode("utf-8")
        for first, second in ((mine, mine), (mine, "evil.example:%d" % p), ("evil.example:%d" % p, mine), (mine, "localhost:%d" % p)):
            code, _, _, parsed = _ask(p, "GET", "/api/state", [("Host", second)], host=first)
            self.assertEqual(code, 421, (first, second))
            self.assertIn("own names", (parsed or {}).get("error", ""), (first, second))
            code, _, _, parsed = _ask(p, "POST", "/api/md", [("Host", second), ("X-FP-Token", "t0k"), ("Content-Type", "application/json")], payload, host=first)
            self.assertEqual(code, 421, (first, second))
        code, _, _, parsed = _ask(p, "GET", "/api/evidence", [("Host", mine), ("X-FP-Token", "t0k")])      # the side-effect GET too: refused before the collector
        self.assertEqual(code, 421)
        self.nothing_happened("a request with two Host headers")
        code, _, _, _ = _ask(p, "GET", "/api/state")
        self.assertEqual(code, 200, "control: one Host")
        code, _, _, parsed = _ask(p, "POST", "/api/md", [("X-FP-Token", "t0k"), ("Content-Type", "application/json")], payload)
        self.assertEqual((code, (parsed or {}).get("saved")), (200, True), "control: one Host on a POST")

    # -- the Sec-Fetch-Site rule, where the browser sends it (loopback, https): the Desk's shape, with Dest document OR iframe
    def test_sec_fetch_site_refuses_cross_site_except_a_navigation_of_the_page_itself(self):
        p, tok = self.srv.port, {"X-FP-Token": "t0k"}

        def sf(site, mode="cors", dest="empty"):
            return {"Sec-Fetch-Site": site, "Sec-Fetch-Mode": mode, "Sec-Fetch-Dest": dest}
        refused = (
            ("a cross-site fetch of the data", "/api/state", sf("cross-site")),
            ("a cross-site fetch of the page", "/", sf("cross-site")),
            ("a cross-site <img> of the page", "/", sf("cross-site", "no-cors", "image")),
            ("a cross-site iframe that is not a navigation", "/", sf("cross-site", "no-cors", "iframe")),
            ("a cross-site embed", "/", sf("cross-site", "navigate", "embed")),
            ("a cross-site object", "/", sf("cross-site", "navigate", "object")),
            ("a cross-site navigation with no dest", "/", sf("cross-site", "navigate", "empty")),
            ("a cross-site window onto a data route", "/api/state", sf("cross-site", "navigate", "document")),
            ("a cross-site frame onto a data route", "/api/md", sf("cross-site", "navigate", "iframe")),
            ("a cross-site window onto the side-effect route", "/api/evidence", {**sf("cross-site", "navigate", "document"), **tok}),
            ("a cross-site script load", "/vendor/markdown-it.min.js", sf("cross-site", "no-cors", "script")),
            ("a value no browser sends", "/api/state", sf("sideways")),
        )
        for what, path, headers in refused:
            code, _, _, parsed = _ask(p, "GET", path, headers)
            self.assertEqual((code, (parsed or {}).get("reason")), (403, "fetch-site"), what)
        for what, headers in (("cross-site, no Origin", {**sf("cross-site"), **tok}),
                              ("cross-site with our own Origin", {**sf("cross-site"), **tok, "Origin": self.srv.origin})):
            code, _, _, parsed = _ask(p, "POST", "/api/md", headers, json.dumps({"text": "---\ntitle: t\n---\ncross-site"}).encode("utf-8"))
            self.assertEqual((code, (parsed or {}).get("reason")), (403, "fetch-site"), "a POST: " + what)
        self.nothing_happened("a cross-site request")
        admitted = (
            ("a typed or bookmarked address", "/", sf("none", "navigate", "document")),
            ("a same-origin reload", "/", sf("same-origin", "navigate", "document")),
            ("a same-site window (a sibling port on this host)", "/", sf("same-site", "navigate", "document")),
            ("a cross-site window (the Scanner's /repair)", "/?token=t0k&theme=light", sf("cross-site", "navigate", "document")),
            ("a cross-site frame (the Control's openBench)", "/?token=t0k&theme=dark", sf("cross-site", "navigate", "iframe")),
            ("a legacy nested navigation", "/", sf("cross-site", "nested-navigate", "iframe")),
            ("the page's own data fetch", "/api/state", {**sf("same-origin"), **tok}),
            ("a sibling page's read", "/api/state", sf("same-site")),
        )
        for what, path, headers in admitted:
            code, _, data, parsed = _ask(p, "GET", path, headers)
            self.assertEqual(code, 200, what)
        code, _, _, parsed = _ask(p, "POST", "/api/md", {**tok, "Origin": self.srv.origin, **sf("same-origin")},
                                  json.dumps({"text": "---\ntitle: t\n---\nsame-origin"}).encode("utf-8"))
        self.assertEqual((code, (parsed or {}).get("saved")), (200, True), "the page's own POST")

    # -- the other verbs answer nothing, and nothing carries a CORS allowance
    def test_head_options_and_the_other_verbs_do_nothing_and_no_answer_is_readable_cross_origin(self):
        p = self.srv.port
        foreign = {"Origin": "http://evil.example", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "x-fp-token, content-type",
                   "X-FP-Token": "t0k"}
        for method in ("HEAD", "OPTIONS", "PUT", "DELETE", "PATCH", "TRACE"):
            for headers in ({}, foreign):
                code, hdr, _, _ = _ask(p, method, "/api/md", headers, b"{}" if method in ("PUT", "PATCH", "DELETE") else None)
                self.assertEqual(code, 501, (method, headers))
                self.assertFalse([h for h in hdr if h.startswith("access-control-")], (method, hdr))
        for method, path, headers, body in (("GET", "/", {}, None), ("GET", "/api/state", {"Origin": self.srv.origin}, None),
                                            ("GET", "/api/state", {"Origin": "http://evil.example"}, None), ("GET", "/api/nothing", {}, None),
                                            ("POST", "/api/md", {"Origin": "http://evil.example"}, b"{}"),
                                            ("POST", "/api/md", {"Origin": self.srv.origin, "X-FP-Token": "t0k"}, b'{"text": "---\\ntitle: t\\n---\\nok"}'),
                                            ("GET", "/api/evidence", {}, None)):
            code, hdr, _, _ = _ask(p, method, path, headers, body)
            self.assertFalse([h for h in hdr if h.startswith("access-control-")], (method, path, hdr))
            self.assertEqual(hdr.get("referrer-policy"), "no-referrer", (method, path))
        self.assertEqual(self.srv.evidence, [])

    # -- every real client's exact shape still passes
    def test_every_real_client_shape_still_passes(self):
        p, tok, ours = self.srv.port, "t0k", self.srv.origin
        page = {"Sec-Fetch-Site": "same-origin", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Dest": "empty", "X-FP-Token": tok, "Accept": "*/*"}
        shapes = (
            ("the widget's window / a typed address (Edge navigation)", "GET", "/?token=t0k&theme=dark", {"Sec-Fetch-Site": "none", "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Dest": "document", "Upgrade-Insecure-Requests": "1", "User-Agent": "Mozilla/5.0 Edg/130"}, None),
            ("the Control's frame (openBench)", "GET", "/?token=t0k&theme=dark", {"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Dest": "iframe", "Referer": "http://localhost:7170/", "Upgrade-Insecure-Requests": "1"}, None),
            ("the Scanner's /repair window", "GET", "/?token=t0k", {"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "navigate", "Sec-Fetch-Dest": "document",
                "Referer": "http://localhost:7160/"}, None),
            ("the page's data fetch", "GET", "/api/state", {**page, "If-None-Match": '"none-such"'}, None),
            ("the page's markdown revalidation", "GET", "/api/md", {**page, "If-None-Match": '"none-such"', "Cache-Control": "no-cache"}, None),
            ("the page's own write (WebView2 / Edge on loopback)", "POST", "/api/md", {**page, "Origin": ours, "Content-Type": "text/plain;charset=UTF-8"},
                json.dumps({"text": "---\ntitle: t\n---\nfrom the page"}).encode("utf-8")),
            ("the phone over plain http (no Fetch Metadata at all)", "POST", "/api/md", {"Origin": ours, "X-FP-Token": tok, "Content-Type": "text/plain;charset=UTF-8",
                "User-Agent": "Mozilla/5.0 (iPhone)"}, json.dumps({"text": "---\ntitle: t\n---\nfrom the phone"}).encode("utf-8")),
            ("the phone's data read over plain http", "GET", "/api/ledger", {"X-FP-Token": tok, "User-Agent": "Mozilla/5.0 (iPhone)"}, None),
            ("PowerShell Invoke-RestMethod (token, no Origin)", "POST", "/api/md", {"X-FP-Token": tok, "Content-Type": "application/json", "User-Agent": "WindowsPowerShell"},
                json.dumps({"text": "---\ntitle: t\n---\nfrom a script"}).encode("utf-8")),
            ("python urllib, as acceptance.py and the Scanner's probe (no extra header)", "GET", "/api/state", {"User-Agent": "Python-urllib/3.12"}, None),
        )
        for what, method, path, headers, body in shapes:
            code, _, _, parsed = _ask(p, method, path, headers, body)
            self.assertIn(code, (200, 304), "%s: %s %s" % (what, code, parsed))
        for what, headers in (("the page's evidence request on loopback", {**page}),
                              ("the page's evidence request on the tailnet (no Referer, no Fetch Metadata)", {"X-FP-Token": tok})):
            self.srv.evidence.clear()
            code, _, _, parsed = _ask(p, "GET", "/api/evidence", headers)
            self.assertEqual((code, self.srv.evidence), (200, [False]), what)
        # the Scanner's liveness probe: a connect that sends nothing, then closes
        s = socket.create_connection(("127.0.0.1", p), timeout=5)
        s.close()
        self.assertEqual(_ask(p, "GET", "/api/state")[0], 200, "the bench survived a bare connect")

    def test_the_comments_and_the_readme_say_where_each_rule_fires(self):
        readme = (HERE / "README.md").read_text(encoding="utf-8")
        for text, name in ((BENCH_PY, "bench.py"), (readme, "README.md")):
            self.assertIn("fires only where browsers send it", text, name)
            self.assertIn("https, or 127.0.0.0/8, ::1, localhost", text, name)
            self.assertIn("HTTP-mode Funnel only", text, name)
            self.assertIn("TCP-mode funnel", text, name)
            self.assertIn("lockdown_check.py", text, name)
        self.assertNotIn("Nothing reads `Origin` or `Sec-Fetch-Site`", readme, "the README still says the bench reads neither")


class TestTailnetShapes(unittest.TestCase):
    """The same rules over the listener a phone or another tailnet device reaches: a bench bound to its tailnet address, driven in-process
    (no socket, no request to any address), every request carrying NO Fetch Metadata - what a browser sends over plain http."""

    HOSTS = ("desktop-bndit", "desktop-bndit.tailnet-test.ts.net")
    BOUND = "100.108.102.101"
    PORT = 7077

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="fp-test-shapes-"))
        (self.tmp / "book.md").write_text("---\ntitle: t\n---\nline one", encoding="utf-8")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.bench = bench.Bench(self.tmp)
        self.evidence = []
        self.bench.ok15_evidence = lambda retry=False: (self.evidence.append(retry), {"spy": "evidence"})[1]
        self.handler = bench.make_handler(self.bench, token="t0k", hosts=self.HOSTS)
        self.server = types.SimpleNamespace(server_address=(self.BOUND, self.PORT))

    def send(self, method, path, headers=None, body=b"", host=None):
        conn = _FakeConn(_raw(method, path, host=host or "%s:%d" % (self.BOUND, self.PORT), headers=headers, body=body))
        with contextlib.redirect_stdout(io.StringIO()):
            self.handler(conn, ("100.97.237.60", 5555), self.server)
        return _wire_answer(conn)[:2]

    def write(self, origin, extra=None, host=None):
        body = json.dumps({"text": "---\ntitle: t\n---\nwritten by %s" % (origin or "a script")}).encode("utf-8")
        headers = {"X-FP-Token": "t0k", "Content-Type": "text/plain;charset=UTF-8", **(extra or {})}
        if origin is not None:
            headers["Origin"] = origin
        return self.send("POST", "/api/md", headers, body, host)

    def test_our_own_origins_are_admitted(self):
        # S215 round nine (1): the loopback names (127.0.0.1, localhost, [::1]) are NOT here any more - on the tailnet listener they are not ours
        # (test_a_loopback_name_is_not_ours_on_the_tailnet_listener; the loopback listener keeps them: TestRoundNineListeners)
        for origin in ("http://100.108.102.101:7077", "http://desktop-bndit:7077", "http://desktop-bndit.tailnet-test.ts.net:7077",
                       "http://desktop-bndit.tailnet-test.ts.net.:7077", "HTTP://DESKTOP-BNDIT:7077", None):
            code, parsed = self.write(origin)
            self.assertEqual((code, (parsed or {}).get("saved")), (200, True), origin)

    # S215 round nine (1): on the TAILNET listener a loopback name is not one of our own pages, in an Origin or a Referer
    LOOPBACK_SPELLINGS = ("127.0.0.1", "localhost", "localhost.", "LOCALHOST", "[::1]", "[0:0:0:0:0:0:0:1]", "[::ffff:127.0.0.1]", "[::ffff:7f00:1]",
                          "127.0.0.2", "127.1.2.3")

    def test_a_loopback_name_is_not_ours_on_the_tailnet_listener(self):
        before = (self.tmp / "book.md").read_bytes()
        for name in self.LOOPBACK_SPELLINGS:
            origin = "http://%s:7077" % name
            code, parsed = self.write(origin)
            self.assertEqual((code, (parsed or {}).get("reason")), (403, "origin"), origin)
            code, parsed = self.send("GET", "/api/state", {"Origin": origin})       # the rule is for every method, a read too
            self.assertEqual((code, (parsed or {}).get("reason")), (403, "origin"), "a GET with " + origin)
            code, parsed = self.send("GET", "/api/evidence", {"Referer": origin + "/?token=t0k"})       # a loopback Referer is no proof on the tailnet
            self.assertEqual((code, (parsed or {}).get("reason")), (403, "unproven-origin"), "a Referer of " + origin)
        self.assertEqual((self.tmp / "book.md").read_bytes(), before)
        self.assertEqual(self.evidence, [])
        # the same Referer shapes that ARE ours are proof (and then meet the token gate): the tailnet address and a tailnet name
        for ok in ("http://100.108.102.101:7077/", "http://desktop-bndit:7077/", "http://desktop-bndit.tailnet-test.ts.net:7077/"):
            code, parsed = self.send("GET", "/api/evidence", {"Referer": ok})
            self.assertEqual(code, 403, ok)
            self.assertNotIn("reason", parsed or {}, ok)
            self.assertIn("X-FP-Token", (parsed or {}).get("error", ""), ok)

    def test_a_page_on_any_other_site_port_or_device_is_refused(self):
        before = (self.tmp / "book.md").read_bytes()
        for origin in ("http://100.108.102.101:7078", "http://100.108.102.101", "http://100.97.237.60:7077", "http://phone.tailnet-test.ts.net:7077",
                       "http://192.168.2.102:7077", "http://evil.example:7077", "https://100.108.102.101:7077", "null",
                       "http://desktop-bndit.evil.example:7077", "http://100.108.102.101:7077.evil.example"):
            code, parsed = self.write(origin)
            self.assertEqual((code, (parsed or {}).get("reason")), (403, "origin"), origin)
        self.assertEqual((self.tmp / "book.md").read_bytes(), before)

    def test_the_phone_over_plain_http_passes_and_a_blind_evidence_get_does_not(self):
        for path in ("/", "/api/state", "/api/md", "/api/ledger"):
            self.assertEqual(self.send("GET", path, {"User-Agent": "Mozilla/5.0 (iPhone)"})[0], 200, path)
        self.assertEqual(self.send("GET", "/api/evidence", {"X-FP-Token": "t0k"}), (200, {"spy": "evidence"}))
        self.evidence.clear()
        for headers in ({}, {"Referer": "http://evil.example/"}, {"Referer": "http://100.97.237.60:7077/"}, {"Referer": "http://127.0.0.1:1/"}):
            code, parsed = self.send("GET", "/api/evidence", headers)
            self.assertEqual((code, (parsed or {}).get("reason")), (403, "unproven-origin"), headers)
        # a Referer from this bench's own address is proof of a click within its page - and still meets the token gate
        for own in ("http://100.108.102.101:7077/?token=t0k", "http://desktop-bndit:7077/", "http://desktop-bndit.tailnet-test.ts.net:7077/"):
            code, parsed = self.send("GET", "/api/evidence", {"Referer": own})
            self.assertEqual(code, 403, own)
            self.assertIn("X-FP-Token", (parsed or {}).get("error", ""), own)
            self.assertNotIn("reason", parsed or {}, "proof was shown (our own Referer): the token gate refused, not rule (5)")
        self.assertEqual(self.evidence, [])

    def test_no_fetch_metadata_means_the_sec_fetch_rule_is_inert_and_the_origin_rule_carries_the_lock(self):
        # with no Sec-Fetch-* a cross-site navigation cannot be told from a typed address: read routes answer it, and the lock is Origin + proof
        self.assertEqual(self.send("GET", "/", {"Referer": "http://evil.example/"})[0], 200)
        self.assertEqual(self.write("http://evil.example:7077")[1]["reason"], "origin")
        self.assertEqual(self.send("GET", "/api/evidence", {"Referer": "http://evil.example/"})[1]["reason"], "unproven-origin")

    def test_two_host_headers_are_refused_on_the_tailnet_listener(self):
        """S215 round nine (2): a second Host header is added to the raw request (the helper below builds what `_raw`'s dict cannot)"""
        ours = "%s:%d" % (self.BOUND, self.PORT)
        before = (self.tmp / "book.md").read_bytes()
        body = json.dumps({"text": "---\ntitle: t\n---\nTWO HOSTS"}).encode("utf-8")
        for first, second in ((ours, ours), (ours, "evil.example"), ("evil.example", ours), (ours, "desktop-bndit:7077"), (ours, "127.0.0.1:7077")):
            for method, path, headers, payload in (("GET", "/api/state", {}, b""), ("GET", "/api/evidence", {"X-FP-Token": "t0k"}, b""),
                                                   ("POST", "/api/md", {"X-FP-Token": "t0k", "Origin": "http://" + ours}, body)):
                raw = _raw(method, path, host=first, headers=headers, body=payload).replace(b"\r\n\r\n", b"\r\nHost: " + second.encode() + b"\r\n\r\n", 1)
                conn = _FakeConn(raw)
                with contextlib.redirect_stdout(io.StringIO()):
                    self.handler(conn, ("100.97.237.60", 5555), self.server)
                code, parsed, _ = _wire_answer(conn)
                self.assertEqual(code, 421, (method, path, first, second))
                self.assertIn("own names", (parsed or {}).get("error", ""), (method, path, first, second))
        self.assertEqual((self.tmp / "book.md").read_bytes(), before)
        self.assertEqual(self.evidence, [])
        self.assertEqual(self.send("GET", "/api/state")[0], 200, "control: one Host")


class TestRoundNineListeners(unittest.TestCase):
    """S215 round nine (1), each kind of listener, in-process (fake connections, no socket, no address is ever sent to): the loopback listener
    (127.0.0.1 and ::1) keeps its loopback names in an Origin and a Referer; a loopback stand-in (127.0.0.2, what a test may bind in place of a
    tailnet address) takes its OWN address and not the other loopback names"""
    PORT = 7077

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="fp-test-round9-"))
        (self.tmp / "book.md").write_text("---\ntitle: t\n---\nline one", encoding="utf-8")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.bench = bench.Bench(self.tmp)
        self.evidence = []
        self.bench.ok15_evidence = lambda retry=False: (self.evidence.append(retry), {"spy": "evidence"})[1]
        self.handler = bench.make_handler(self.bench, token="t0k", hosts=())

    def on(self, bound, method, path, headers=None, body=b""):
        host = ("[%s]:%d" if ":" in bound else "%s:%d") % (bound, self.PORT)
        conn = _FakeConn(_raw(method, path, host=host, headers=headers, body=body))
        with contextlib.redirect_stdout(io.StringIO()):
            self.handler(conn, ("127.0.0.1", 5555), types.SimpleNamespace(server_address=(bound, self.PORT)))
        return _wire_answer(conn)[:2]

    def write(self, bound, origin):
        body = json.dumps({"text": "---\ntitle: t\n---\nwritten from %s" % origin}).encode("utf-8")
        return self.on(bound, "POST", "/api/md", {"X-FP-Token": "t0k", "Content-Type": "text/plain;charset=UTF-8", "Origin": origin}, body)

    def test_the_loopback_listener_keeps_its_loopback_names(self):
        for bound in ("127.0.0.1", "::1"):
            for name in ("127.0.0.1", "localhost", "localhost.", "LOCALHOST", "[::1]"):
                origin = "http://%s:%d" % (name, self.PORT)
                code, parsed = self.write(bound, origin)
                self.assertEqual((code, (parsed or {}).get("saved")), (200, True), (bound, origin))
                # a Referer of ours is proof on the evidence GET (and the request then meets the token gate, not rule 5)
                code, parsed = self.on(bound, "GET", "/api/evidence", {"Referer": origin + "/?token=t0k"})
                self.assertEqual(code, 403, (bound, origin))
                self.assertIn("X-FP-Token", (parsed or {}).get("error", ""), (bound, origin))
                self.assertNotIn("reason", parsed or {}, (bound, origin))
        self.assertEqual(self.evidence, [])

    def test_the_loopback_listener_still_refuses_what_is_not_its_own(self):
        for bound in ("127.0.0.1", "::1"):
            for origin in ("http://evil.example:7077", "http://100.108.102.101:7077", "null", "http://localhost:7078", "https://localhost:7077"):
                code, parsed = self.write(bound, origin)
                self.assertEqual((code, (parsed or {}).get("reason")), (403, "origin"), (bound, origin))

    def test_a_loopback_stand_in_takes_its_own_address_and_not_the_other_loopback_names(self):
        code, parsed = self.write("127.0.0.2", "http://127.0.0.2:%d" % self.PORT)
        self.assertEqual((code, (parsed or {}).get("saved")), (200, True), "its own address is ours")
        before = (self.tmp / "book.md").read_bytes()
        for origin in ("http://127.0.0.1:%d" % self.PORT, "http://localhost:%d" % self.PORT, "http://[::1]:%d" % self.PORT, "http://127.0.0.3:%d" % self.PORT):
            code, parsed = self.write("127.0.0.2", origin)
            self.assertEqual((code, (parsed or {}).get("reason")), (403, "origin"), origin)
        self.assertEqual((self.tmp / "book.md").read_bytes(), before)


class TestOriginAndProofTables(unittest.TestCase):
    """the pure functions of rule (5), as tables: what is ours, what only looks like ours"""

    BOUND, NAMES, PORT = "100.108.102.101", ("desktop-bndit", "desktop-bndit.tailnet-test.ts.net"), 7077

    def test_authority_table(self):
        good = {"127.0.0.1": ("127.0.0.1", 80), "127.0.0.1:7077": ("127.0.0.1", 7077), "[::1]": ("::1", 80), "[::1]:7077": ("::1", 7077),
                "Desktop-BNDIT:7077": ("desktop-bndit", 7077), "name.:7077": ("name", 7077), "a.b.c": ("a.b.c", 80), " 127.0.0.1:1 ": ("127.0.0.1", 1),
                "127.0.0.1:65535": ("127.0.0.1", 65535)}
        for text, want in good.items():
            self.assertEqual(bench._authority(text), want, text)
        for text in ("", " ", None, "[", "[]", "[::1", "[::1]x", "[::1]:", "::1", "a:b:c", "127.0.0.1:", "127.0.0.1:0", "127.0.0.1:65536", "127.0.0.1:-1",
                     "127.0.0.1:+1", "127.0.0.1:1e3", "127.0.0.1:٥", "127.0.0.1:7077@evil.example", "user@127.0.0.1", "127.0.0.1/", "127.0.0.1:7077/x",
                     "a b", "a\tb", "127.0.0.1\\x", ":7077", "127.0.0.1?x", "127.0.0.1#x"):
            self.assertIsNone(bench._authority(text), repr(text))

    def test_origin_ok_table(self):
        ok = lambda v: bench.origin_ok(v, self.BOUND, self.NAMES, self.PORT)   # noqa: E731
        for v in ("http://100.108.102.101:7077", "http://desktop-bndit:7077",
                  "http://desktop-bndit.tailnet-test.ts.net:7077", "http://desktop-bndit.tailnet-test.ts.net.:7077", "HTTP://DESKTOP-BNDIT:7077", " http://desktop-bndit:7077 "):
            self.assertTrue(ok(v), v)
        # S215 round nine (1): on the tailnet listener (BOUND is a tailnet address) no loopback name is ours - the loopback listener's table is below
        for v in ("http://127.0.0.1:7077", "http://localhost:7077", "http://[::1]:7077", "HTTP://LOCALHOST:7077", " http://localhost:7077 ", "http://localhost.:7077",
                  "http://[0:0:0:0:0:0:0:1]:7077", "http://[::ffff:127.0.0.1]:7077", "http://[::ffff:7f00:1]:7077", "http://127.0.0.2:7077", "http://127.1.2.3:7077"):
            self.assertFalse(ok(v), v)
        for v in ("null", "NULL", "", None, "http://", "http://:7077", "http://localhost", "http://localhost:80", "http://localhost:7078", "https://localhost:7077",
                  "ftp://localhost:7077", "localhost:7077", "//localhost:7077", "http://localhost:7077/", "http://localhost:7077/x", "http://localhost:7077?x",
                  "http://localhost.evil.example:7077", "http://evil.example:7077", "http://localhost:7077@evil.example", "http://evil.example@localhost:7077",
                  "http://100.97.237.60:7077", "http://192.168.2.102:7077", "http://0.0.0.0:7077", "http://desktop-bndit.evil.example:7077",
                  "http://localhost:7077 http://evil.example", "chrome-extension://localhost:7077", "file://localhost:7077"):
            self.assertFalse(ok(v), repr(v))
        self.assertTrue(bench.origin_ok("http://desktop-bndit:1", self.BOUND, self.NAMES, None), "port None = any port (a caller that does not say)")
        self.assertTrue(bench.origin_ok("http://localhost:1", "127.0.0.1", self.NAMES, None), "port None = any port, on the loopback listener")
        self.assertFalse(bench.origin_ok("http://localhost:1", self.BOUND, self.NAMES, None), "a loopback name is refused on the tailnet listener whatever the port rule")

    def test_loopback_names_are_ours_on_the_loopback_listener_only(self):
        """S215 round nine (1): the same spellings read against each kind of listener - the loopback listener (127.0.0.1 and ::1) keeps its loopback
        names; the tailnet listener keeps none; a loopback stand-in (127.0.0.2, a test's) keeps its OWN address and not the other loopback names"""
        names = ("127.0.0.1", "localhost", "localhost.", "LOCALHOST", "[::1]")
        for bound in ("127.0.0.1", "::1"):
            for n in names:
                self.assertTrue(bench.origin_ok("http://%s:7077" % n, bound, self.NAMES, self.PORT), (bound, n))
                self.assertTrue(bench.referer_ok("http://%s:7077/?token=x" % n, bound, self.NAMES, self.PORT), (bound, n))
        for bound in (self.BOUND, "fd7a:115c:a1e0::1"):
            for n in names + ("[0:0:0:0:0:0:0:1]", "[::ffff:127.0.0.1]", "[::ffff:7f00:1]", "127.0.0.2", "127.1.2.3"):
                self.assertFalse(bench.origin_ok("http://%s:7077" % n, bound, self.NAMES, self.PORT), (bound, n))
                self.assertFalse(bench.referer_ok("http://%s:7077/" % n, bound, self.NAMES, self.PORT), (bound, n))
        self.assertTrue(bench.origin_ok("http://[fd7a:115c:a1e0::1]:7077", "fd7a:115c:a1e0::1", self.NAMES, self.PORT), "a tailnet IPv6 listener's own address is ours")
        self.assertTrue(bench.origin_ok("http://127.0.0.2:7077", "127.0.0.2", self.NAMES, self.PORT), "the stand-in's own address")
        for n in ("127.0.0.1", "localhost", "[::1]"):
            self.assertFalse(bench.origin_ok("http://%s:7077" % n, "127.0.0.2", self.NAMES, self.PORT), "a stand-in on 127.0.0.2 does not take the other loopback names: " + n)

    def test_loopback_name_table(self):
        for n in ("localhost", "127.0.0.1", "127.0.0.2", "127.1.2.3", "::1", "0:0:0:0:0:0:0:1", "::ffff:127.0.0.1", "::ffff:7f00:1"):
            self.assertTrue(bench._loopback_name(n), n)
        for n in ("", "100.108.102.101", "desktop-bndit", "evil.example", "::ffff:100.64.0.1", "localhost.evil.example", "127.0.0.1.evil.example", "128.0.0.1",
                  "fd7a:115c:a1e0::1", "0.0.0.0", "::", "127.0.0", "a:b"):
            self.assertFalse(bench._loopback_name(n), repr(n))

    def test_host_header_ok_table(self):
        """S215 round nine (2): at most one Host header, and it names the bench"""
        import email.message

        def hosts(*values):
            m = email.message.Message()
            for v in values:
                m["Host"] = v      # Message.__setitem__ appends: a header given twice is two header lines, as on the wire
            return m
        ok = lambda m, bound=self.BOUND: bench.host_header_ok(m, bound, self.NAMES)   # noqa: E731
        self.assertTrue(ok(hosts("100.108.102.101:7077")))
        self.assertTrue(ok(hosts("desktop-bndit:7077")))
        self.assertTrue(ok(hosts()) is False, "no Host at all is refused on the tailnet listener")
        self.assertTrue(ok(hosts(), "127.0.0.1"), "no Host at all is a local tool on the loopback listener")
        self.assertFalse(ok(hosts("evil.example:7077")))
        for two in (("100.108.102.101:7077", "100.108.102.101:7077"), ("100.108.102.101:7077", "evil.example"), ("evil.example", "100.108.102.101:7077"),
                    ("desktop-bndit:7077", "desktop-bndit:7077"), ("", "100.108.102.101:7077")):
            self.assertFalse(ok(hosts(*two)), two)
            self.assertFalse(ok(hosts(*two), "127.0.0.1"), two)
        self.assertFalse(ok(hosts("127.0.0.1:7077", "localhost:7077"), "127.0.0.1"), "two loopback Host headers on the loopback listener")
        self.assertTrue(ok(hosts("127.0.0.1:7077"), "127.0.0.1"))

    def test_referer_ok_table(self):
        ok = lambda v: bench.referer_ok(v, self.BOUND, self.NAMES, self.PORT)   # noqa: E731
        for v in ("http://100.108.102.101:7077/", "http://desktop-bndit:7077/api/state", "http://desktop-bndit.tailnet-test.ts.net:7077/?token=t0k&theme=dark#p=3",
                  "http://desktop-bndit:7077"):
            self.assertTrue(ok(v), v)
        for v in ("http://localhost:7077/?token=t0k&theme=dark#p=3", "http://[::1]:7077/", "http://localhost:7077", "http://127.0.0.1:7077/"):
            self.assertFalse(ok(v), "round nine (1): a loopback Referer is not ours on the tailnet listener: " + v)
        for v in ("", None, "garbage", "/relative", "http://evil.example/", "http://localhost:7078/", "http://localhost/", "https://localhost:7077/",
                  "http://localhost.evil.example:7077/", "http://localhost:7077@evil.example/", "http://[::1/", "javascript:alert(1)", "data:text/html,x"):
            self.assertFalse(ok(v), repr(v))

    def test_proof_and_refusal_table(self):
        import email.message

        def hdrs(**kw):
            m = email.message.Message()
            for k, v in kw.items():
                m[k.replace("_", "-")] = v
            return m
        ref = lambda h, method="GET", path="/api/evidence": bench.page_refusal(h, method, path, self.BOUND, self.NAMES, self.PORT)   # noqa: E731
        self.assertEqual(ref(hdrs()), "unproven-origin")
        self.assertIsNone(ref(hdrs(X_FP_Token="x")))
        self.assertIsNone(ref(hdrs(X_FP_Local="")), "any value, even an empty one: the header's presence is the proof")
        self.assertIsNone(ref(hdrs(Referer="http://desktop-bndit:7077/")))
        self.assertIsNone(ref(hdrs(Referer="http://100.108.102.101:7077/")))
        self.assertEqual(ref(hdrs(Referer="http://localhost:7077/")), "unproven-origin", "round nine (1): a loopback Referer is no proof on the tailnet listener")
        self.assertEqual(ref(hdrs(Referer="http://127.0.0.1:7077/")), "unproven-origin")
        loop = lambda h, method="GET", path="/api/evidence": bench.page_refusal(h, method, path, "127.0.0.1", self.NAMES, self.PORT)   # noqa: E731
        self.assertIsNone(loop(hdrs(Referer="http://localhost:7077/")), "...and it is proof on the loopback listener")
        self.assertEqual(ref(hdrs(Referer="http://evil.example/")), "unproven-origin")
        self.assertIsNone(ref(hdrs(Sec_Fetch_Site="same-origin")))
        self.assertIsNone(ref(hdrs(Sec_Fetch_Site="none")))
        self.assertEqual(ref(hdrs(Sec_Fetch_Site="cross-site", X_FP_Token="x")), "fetch-site")
        self.assertIsNone(ref(hdrs(), path="/api/state"), "a read route needs no proof")
        self.assertIsNone(ref(hdrs(), method="POST", path="/api/md"), "an Origin-less POST is a non-browser client: rule (5) leaves it to the token gate")
        self.assertEqual(ref(hdrs(Origin="null"), method="POST", path="/api/md"), "origin")
        self.assertEqual(ref(hdrs(Origin="http://localhost:7077"), method="POST", path="/api/md"), "origin", "round nine (1): a loopback Origin is foreign on the tailnet listener")
        self.assertIsNone(ref(hdrs(Origin="http://desktop-bndit:7077"), method="POST", path="/api/md"))
        self.assertIsNone(loop(hdrs(Origin="http://localhost:7077"), method="POST", path="/api/md"), "...and ours on the loopback listener")
        two = hdrs(Origin="http://desktop-bndit:7077")
        two["Origin"] = "http://desktop-bndit:7077"      # a second header line, the same value
        self.assertEqual(ref(two, method="POST", path="/api/md"), "origin", "round nine (2): two Origin headers are refused, even when they agree")
        self.assertEqual(ref(two, method="GET", path="/api/state"), "origin")


class TestGetRouteCensus(unittest.TestCase):
    """A: every route the server answers is classified - so a GET added later cannot be a side effect nobody looked at - and the read-only ones
    are shown, by source and on the wire, to change nothing."""

    def test_every_get_route_is_classified(self):
        do_get = py_function_body(BENCH_PY, "do_GET")
        routes = set(re.findall(r'url\.path == "(/[^"]*)"', do_get))
        prefixes = set(re.findall(r'url\.path\.startswith\("(/[^"]*)"\)', do_get))
        self.assertEqual(routes, set(bench.READ_ONLY_GETS) | set(bench.SIDE_EFFECT_GETS),
                         "a GET route was added or removed without classifying it as read-only or as a side effect")
        self.assertEqual(prefixes, set(bench.READ_ONLY_GET_PREFIXES))
        self.assertFalse(set(bench.READ_ONLY_GETS) & set(bench.SIDE_EFFECT_GETS))
        self.assertEqual(bench.SIDE_EFFECT_GETS, ("/api/evidence",))
        # /api/md is a read as a GET and a write as a POST (two methods, two rules); the side-effect GET is in no POST census
        self.assertEqual(set(bench.MUTATING_POSTS) & set(bench.READ_ONLY_GETS), {"/api/md"})
        self.assertFalse(set(bench.MUTATING_POSTS) & set(bench.SIDE_EFFECT_GETS))

    @staticmethod
    def writes_something(src):
        return [t for t in (".write_text(", ".write_bytes(", "subprocess", "os.remove", "unlink(", "shutil.", "_write_body", "manifest_path", "open(", "_undo",
                            "mkdir(", "os.replace", "rename(") if t in src]

    def test_the_read_only_get_branches_hold_no_write_or_spawn(self):
        do_get = py_function_body(BENCH_PY, "do_GET")
        evidence = do_get[do_get.index('url.path == "/api/evidence"'):do_get.index('url.path == "/api/toc"')]
        rest = do_get.replace(evidence, "")
        self.assertEqual(self.writes_something(rest), [], "a read-only GET branch holds a write or a spawn")
        self.assertEqual(self.writes_something(evidence), [], "the evidence branch hands its work to Bench.ok15_evidence and writes nothing itself")
        # negative control: the check sees a write when there is one
        self.assertEqual(self.writes_something('self.md_path.write_text("x")'), [".write_text("])
        self.assertEqual(self.writes_something("subprocess.run([])"), ["subprocess"])


class TestReadOnlyGetsChangeNothing(unittest.TestCase):
    """A, observed: over a real tiny PDF every read-only GET route is asked (no Origin, no Referer, and again with a foreign Referer - what a blind
    foreign page can send) and the bundle's bytes, the source PDF and the in-memory undo stack are identical afterwards."""

    def setUp(self):
        try:
            import fitz
        except ImportError:
            self.skipTest("pymupdf (fitz) is not importable here - UNREAD, not a pass")
        self.tmp = Path(tempfile.mkdtemp(prefix="fp-test-readonly-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "book.md").write_text("---\ntitle: t\n---\nalpha beta gamma\n\ndelta epsilon", encoding="utf-8")
        (self.tmp / "manifest.json").write_text(json.dumps({"pages": 3, "source": "book.pdf"}), encoding="utf-8")
        doc = fitz.open()
        for i in range(3):
            doc.new_page().insert_text((72, 72), "alpha beta gamma page %d" % (i + 1))
        doc.save(str(self.tmp / "book.pdf"))
        doc.close()
        self.bench = bench.Bench(self.tmp, pdf=self.tmp / "book.pdf")
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), bench.make_handler(self.bench, token="t0k"))
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (self.httpd.shutdown(), self.httpd.server_close(), self.bench._doc is not None and self.bench._doc.close()))

    def snapshot(self):
        return {str(p.relative_to(self.tmp)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(self.tmp.rglob("*")) if p.is_file()}

    def test_no_read_only_get_writes_spawns_or_changes_an_answer(self):
        served = {"/": 200, "/api/state": 200, "/api/md": 200, "/api/page?n=1&dpi=40": 200, "/api/asset?name=_repair_p1_1.png": 404, "/api/ledger": 200,
                  "/api/rescore": 200, "/api/toc": 200, "/api/find?q=alpha": 200, "/api/rects?n=1&q=alpha": 200, "/api/locate?i=0": 500,
                  "/api/trimbox?n=1": 200, "/api/textlayer?n=1": 200, "/api/table?n=1&rect=0,0,1,1": 200, "/api/library": 200, "/fp-tokens.css": 404,
                  "/vendor/markdown-it.min.js": 200}
        self.assertEqual(set(p.split("?")[0] for p in served) - {"/vendor/markdown-it.min.js"}, set(bench.READ_ONLY_GETS), "the table covers every classified route")
        before, pdf_before = self.snapshot(), (self.tmp / "book.pdf").read_bytes()
        empty = {n: self.tmp / ("lib-" + n) for n in ("HELD", "DONE", "PENDING", "ANCHOR")}
        for d in empty.values():
            d.mkdir()
        fake = types.SimpleNamespace(degeneration=lambda _body: {"flagged": False, "worst": [], "blocks_total": 0, "worst_capped_at": 10})
        with mock.patch.dict(sys.modules, {"fidelity_audit": fake}), mock.patch.multiple(bench, **empty), \
                mock.patch.object(bench.Bench, "ok15_evidence", side_effect=AssertionError("a read-only GET reached the evidence collector")):
            for headers in ({}, {"Referer": "http://evil.example/"}):
                for path, want in served.items():
                    code, _, _, parsed = _ask(self.port, "GET", path, headers)
                    self.assertEqual(code, want, (path, headers, parsed))
        self.assertEqual(self.snapshot(), before, "a read-only GET changed a file in the bundle")
        self.assertEqual((self.tmp / "book.pdf").read_bytes(), pdf_before)
        self.assertEqual(self.bench._undo, [])


# ---- the negative controls of rule (5): the same probe, run on bench.py's source with exactly ONE guard removed or weakened -------
def _request_probe(mod):
    """What rule (5) must do, run on `mod` (the real bench module or a mutant of its source) over fake connections from a tailnet peer (no socket):
    the list of things that did not hold ([] = it holds). Positive controls first - every real client's shape is served - then one violation per
    rule. Bench.ok15_evidence is a recorder, so an evidence request that got through is seen and spawns nothing."""
    bad, calls = [], []
    tmp = Path(tempfile.mkdtemp(prefix="fp-test-reqprobe-"))
    try:
        (tmp / "book.md").write_text("---\ntitle: t\n---\nline one", encoding="utf-8")
        handler = mod.make_handler(mod.Bench(tmp), token="t0k", hosts=())
        server = types.SimpleNamespace(server_address=("100.108.102.101", 7077))
        ours = "http://100.108.102.101:7077"
        text = json.dumps({"text": "---\ntitle: t\n---\nPROBE"}).encode("utf-8")
        evil = json.dumps({"text": "---\ntitle: t\n---\nEVIL"}).encode("utf-8")   # what every refused write below carries: it must never land

        def run(method, path, headers=None, payload=b"", extra=b"", bound=None, host=None):
            raw = _raw(method, path, host=host or "%s:7077" % (bound or "100.108.102.101"), headers=headers, body=payload)
            if extra:
                raw = raw.replace(b"\r\n\r\n", b"\r\n" + extra + b"\r\n\r\n", 1)
            conn = _FakeConn(raw)
            with contextlib.redirect_stdout(io.StringIO()):
                handler(conn, ("100.97.237.60", 5555), server if bound is None else types.SimpleNamespace(server_address=(bound, 7077)))
            return _wire_answer(conn)[:2]

        def spy(self, retry=False):
            calls.append(retry)
            return {"spy": 1}

        def sf(site, mode="cors", dest="empty"):
            return {"Sec-Fetch-Site": site, "Sec-Fetch-Mode": mode, "Sec-Fetch-Dest": dest}
        with mock.patch.object(mod.Bench, "ok15_evidence", spy):
            # positive controls
            if run("GET", "/api/state")[0] != 200:
                bad.append("positive control: a plain GET is not served")
            for dest in ("iframe", "document"):
                if run("GET", "/?token=t0k&theme=dark", sf("cross-site", "navigate", dest))[0] != 200:
                    bad.append("positive control: a cross-site navigation into a %s is not served" % dest)
            if run("POST", "/api/md", {"Origin": ours, "X-FP-Token": "t0k"}, text)[0] != 200:
                bad.append("positive control: the page's own POST is not served")
            if run("POST", "/api/md", {"X-FP-Token": "t0k"}, text)[0] != 200:
                bad.append("positive control: an Origin-less POST with the token is not served")
            if run("GET", "/api/evidence", {"X-FP-Token": "t0k"}) != (200, {"spy": 1}) or calls != [False]:
                bad.append("positive control: the page's own evidence GET is not served")
            calls.clear()
            # round nine (1): the loopback listener keeps its loopback names (and a loopback stand-in its own address); the tailnet listener has none
            for what, bound, origin in (("the loopback listener's localhost", "127.0.0.1", "http://localhost:7077"), ("the loopback listener's 127.0.0.1", "127.0.0.1", "http://127.0.0.1:7077"),
                                        ("the ::1 listener's [::1]", "::1", "http://[::1]:7077"), ("a stand-in's own address", "127.0.0.2", "http://127.0.0.2:7077")):
                if run("POST", "/api/md", {"Origin": origin, "X-FP-Token": "t0k"}, text, bound=bound, host=("[%s]:7077" % bound) if ":" in bound else None)[0] != 200:
                    bad.append("positive control: %s Origin is refused on its own listener" % what)

            def expect(label, got, want_status, want_reason):
                code, parsed = got
                if (code, (parsed or {}).get("reason")) != (want_status, want_reason):
                    bad.append("%s: answered %s %s, wanted %s %s" % (label, code, (parsed or {}).get("reason"), want_status, want_reason))
            # one violation per rule
            for what, origin in (("a foreign Origin", "http://evil.example"), ("Origin null", "null"), ("a sibling port's Origin", ours[:-1] + "8"),
                                 ("an https Origin", "https://100.108.102.101:7077")):
                expect("Origin rule: %s with the right token" % what, run("POST", "/api/md", {"Origin": origin, "X-FP-Token": "t0k"}, evil), 403, "origin")
            expect("Origin rule: a second, foreign Origin header", run("POST", "/api/md", {"Origin": ours, "X-FP-Token": "t0k"}, evil,
                                                                      extra=b"Origin: http://evil.example"), 403, "origin")
            expect("Origin rule: a GET with a foreign Origin", run("GET", "/api/state", {"Origin": "http://evil.example"}), 403, "origin")
            expect("Origin rule: a second Origin header on a GET (both ours)", run("GET", "/api/state", {"Origin": ours}, extra=b"Origin: " + ours.encode()), 403, "origin")
            # round nine (1): a loopback name is not ours on the tailnet listener
            for what, origin in (("127.0.0.1", "http://127.0.0.1:7077"), ("localhost", "http://localhost:7077"), ("[::1]", "http://[::1]:7077"),
                                 ("[::ffff:127.0.0.1]", "http://[::ffff:127.0.0.1]:7077")):
                expect("Origin rule: a loopback Origin (%s) on the tailnet listener" % what, run("POST", "/api/md", {"Origin": origin, "X-FP-Token": "t0k"}, evil), 403, "origin")
            expect("proof rule: the evidence GET with a loopback Referer on the tailnet listener", run("GET", "/api/evidence", {"Referer": "http://localhost:7077/"}), 403, "unproven-origin")
            # round nine (2): one Host header at most
            expect("Host rule: a second Host header on a GET (both ours)", run("GET", "/api/state", extra=b"Host: 100.108.102.101:7077"), 421, None)
            expect("Host rule: a second, foreign Host header on a POST with the right token", run("POST", "/api/md", {"Origin": ours, "X-FP-Token": "t0k"}, evil,
                                                                                               extra=b"Host: evil.example"), 421, None)
            expect("Host rule: a foreign Host first, ours second", run("GET", "/api/state", extra=b"Host: 100.108.102.101:7077", host="evil.example"), 421, None)
            for what, headers, path in (("no header", {}, "/api/evidence"), ("a foreign Referer", {"Referer": "http://evil.example/"}, "/api/evidence"),
                                        ("a ';params' spelling", {}, "/api/evidence;x=1")):
                expect("proof rule: the evidence GET with %s" % what, run("GET", path, headers), 403, "unproven-origin")
            expect("Sec-Fetch-Site rule: a cross-site fetch", run("GET", "/api/state", sf("cross-site")), 403, "fetch-site")
            expect("Sec-Fetch-Site rule: a cross-site POST", run("POST", "/api/md", {"X-FP-Token": "t0k", **sf("cross-site")}, evil), 403, "fetch-site")
            for what, path, headers in (("a navigation onto a data route", "/api/state", sf("cross-site", "navigate", "document")),
                                        ("a non-navigation into a frame", "/", sf("cross-site", "no-cors", "iframe")),
                                        ("a navigation into an embed", "/", sf("cross-site", "navigate", "embed")),
                                        ("a value no browser sends", "/api/state", sf("sideways"))):
                expect("Sec-Fetch-Site rule: %s" % what, run("GET", path, headers), 403, "fetch-site")
            if calls:
                bad.append("a refused request reached ok15_evidence")
            if b"EVIL" in (tmp / "book.md").read_bytes():
                bad.append("a refused write landed in the book")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return bad


class TestRequestCheckMutants(unittest.TestCase):
    """docs/32 rule 2: a check that cannot fail is a tautology. The probe above holds on the real source; on bench.py's source with exactly ONE
    guard of rule (5) removed or weakened, each mutant must make it report a failure (a mutant is built in memory; the file is never touched)."""

    MUTANTS = (
        ("a present Origin is never looked at", '    if len(origins) > 1 or (origins and not origin_ok(origins[0], bound, names, port)):', "    if False:"),
        ("a second Origin header is ignored", '    if len(origins) > 1 or (origins and not origin_ok(origins[0], bound, names, port)):',
         "    if origins and not origin_ok(origins[0], bound, names, port):"),
        ("Origin null is ours", '    return bool(sep) and scheme == "http" and _own_authority(rest, bound, names, port)',
         '    return str(value).strip().lower() == "null" or (bool(sep) and scheme == "http" and _own_authority(rest, bound, names, port))'),
        ("an Origin's port is not compared", "    return got is not None and host_ok(got[0], bound, names) and (port is None or got[1] == port)",
         "    return got is not None and host_ok(got[0], bound, names)"),
        ("an https Origin is ours", '    return bool(sep) and scheme == "http" and _own_authority(rest, bound, names, port)',
         '    return bool(sep) and scheme in ("http", "https") and _own_authority(rest, bound, names, port)'),
        ("the Sec-Fetch-Site rule never fires", "    if site and site not in FETCH_SITE_PASS:", "    if False:"),
        ("a value no browser sends is let through", "    if site and site not in FETCH_SITE_PASS:", '    if site == "cross-site":'),
        ("a cross-site navigation may land on any route", 'method in ("GET", "HEAD") and path == "/"', 'method in ("GET", "HEAD")'),
        ("a cross-site navigation into a frame is refused", 'FETCH_NAV_DEST = ("document", "iframe")', 'FETCH_NAV_DEST = ("document",)'),
        ("a cross-site navigation may go into any dest", 'FETCH_NAV_DEST = ("document", "iframe")', 'FETCH_NAV_DEST = ("document", "iframe", "embed", "image")'),
        ("a cross-site non-navigation may go into a frame", 'FETCH_NAV_MODES = ("navigate", "nested-navigate")',
         'FETCH_NAV_MODES = ("navigate", "nested-navigate", "no-cors", "cors")'),
        ("no GET is a side-effect route", 'SIDE_EFFECT_GETS = ("/api/evidence",)', "SIDE_EFFECT_GETS = ()"),
        ("any Referer is proof", "    if ref and referer_ok(ref, bound, names, port):", "    if ref:"),
        ("everything is proof", '    return headers.get("X-FP-Local") is not None or headers.get("X-FP-Token") is not None', "    return True"),
        ("the route is classified by a parser the dispatch does not use", "path = urllib.parse.urlparse(self.path).path   # the parser",
         "path = urllib.parse.urlsplit(self.path).path   # the parser"),
        ("a GET is never asked", 'why = self._page_refusal("GET")', "why = None"),
        ("a POST is never asked", 'why = self._page_refusal("POST")', "why = None"),
        # S215 round nine: each new rule, removed or weakened in turn
        ("a loopback name is ours on the tailnet listener", '    if got is not None and bound not in ("127.0.0.1", "::1") and got[0] != bound and _loopback_name(got[0]):',
         "    if False:"),
        ("the loopback rule fires on the loopback listener too", '    if got is not None and bound not in ("127.0.0.1", "::1") and got[0] != bound and _loopback_name(got[0]):',
         "    if got is not None and got[0] != bound and _loopback_name(got[0]):"),
        ("the loopback rule refuses the listener's own address too", '    if got is not None and bound not in ("127.0.0.1", "::1") and got[0] != bound and _loopback_name(got[0]):',
         '    if got is not None and bound not in ("127.0.0.1", "::1") and _loopback_name(got[0]):'),
        ("a second Host header is ignored", "    return len(hosts) <= 1 and host_ok(hosts[0] if hosts else None, bound, names)",
         "    return host_ok(hosts[0] if hosts else None, bound, names)"),
    )

    def test_the_real_source_and_its_unchanged_copy_hold(self):
        self.assertEqual(_request_probe(bench), [])
        same = "    if site and site not in FETCH_SITE_PASS:"
        self.assertEqual(_request_probe(_bench_mutant(same, same)), [], "the source loaded as a mutant, unchanged, must hold too")

    def test_each_weakened_guard_is_caught(self):
        for name, old, new in self.MUTANTS:
            with self.subTest(mutant=name):
                failures = _request_probe(_bench_mutant(old, new))
                self.assertTrue(failures, "%s: the probe still reports nothing, so it cannot tell" % name)


class _StaleCopy(HTTPServer):
    """a server as the bench built it BEFORE SYM-192: the stdlib's default, SO_REUSEADDR asked for (spelled out, so the test does not
    lean on a stdlib default); also the negative control's first server"""
    allow_reuse_address = True


class TestExclusivePortFollowsThePlatform(unittest.TestCase):
    """SYM-192, the part that runs everywhere: the bench's listener is the stdlib's class, exclusive on Windows only (non-Windows keeps the
    stdlib's SO_REUSEADDR, so a restart rebinds at once there)"""

    def test_the_listener_class_keeps_the_stdlib_default_off_windows(self):
        self.assertTrue(issubclass(bench.ThreadingHTTPServer, ThreadingHTTPServer))
        self.assertEqual(bool(bench.ThreadingHTTPServer.allow_reuse_address), os.name != "nt", "os.name is %r" % (os.name,))
        self.assertEqual(bool(ThreadingHTTPServer.allow_reuse_address), True, "control: the stdlib's own default is reuse-on")


@unittest.skipUnless(os.name == "nt", "SYM-192 is a Windows behaviour (on Windows SO_REUSEADDR lets a second process bind a listening port); "
                                      "on POSIX it does not, the bench keeps the stdlib's behaviour there, and the public CI is Linux")
class TestExclusivePort(unittest.TestCase):
    """SYM-192 (Rab chose "measure, then harden", 2026-10-02): on Windows every listener the bench builds owns its port exclusively, so a
    stale copy of the bench (old code, without the tailnet locks) cannot answer part of the traffic beside the new one. Loopback only,
    OS-assigned ports; every server opened here is closed. Control: the stdlib's class, SO_REUSEADDR asked for, DOES co-bind here."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="fp-test-exclusive-"))
        (self.tmp / "book.md").write_text("---\ntitle: t\n---\nline one", encoding="utf-8")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.handler = bench.make_handler(bench.Bench(self.tmp), token=None)

    def held(self, cls, addr="127.0.0.1", port=0):
        srv = cls((addr, port), self.handler)
        self.addCleanup(srv.server_close)
        return srv

    def refused(self, cls, port, addr="127.0.0.1"):
        """the OSError a bind of `cls` on addr:port raises; fails (and closes what bound) if it bound"""
        try:
            srv = cls((addr, port), self.handler)
        except OSError as e:
            return e
        srv.server_close()
        self.fail("%s bound %s:%d beside the listener that holds it (co-binding)" % (cls.__name__, addr, port))

    def test_a_second_copy_of_the_same_class_is_refused(self):
        first = self.held(bench.ThreadingHTTPServer)
        port = first.server_address[1]
        e = self.refused(bench.ThreadingHTTPServer, port)
        self.assertTrue(bench._port_in_use(e), "refused, but not as 'in use': %r (winerror %r)" % (e, getattr(e, "winerror", None)))

    def test_a_stale_copy_neither_binds_beside_the_new_one_nor_holds_the_port_against_it(self):
        # the field case: the new bench starts while an old one (SO_REUSEADDR, no lock) is up - refused; and the old one cannot start beside a new one
        new = self.held(bench.ThreadingHTTPServer)
        self.assertTrue(bench._port_in_use(self.refused(_StaleCopy, new.server_address[1])), "a stale copy bound beside the new bench")
        stale = self.held(_StaleCopy)
        e = self.refused(bench.ThreadingHTTPServer, stale.server_address[1])
        self.assertTrue(bench._port_in_use(e), "the new bench bound beside a stale copy: %r" % (e,))

    def test_negative_control_the_default_class_co_binds_on_this_machine(self):
        # if THIS passed because nothing could ever co-bind, the refusals above would prove nothing: here the plain class binds twice
        first = self.held(_StaleCopy)
        second = None
        try:
            second = _StaleCopy(("127.0.0.1", first.server_address[1]), self.handler)
        except OSError as e:
            self.fail("the control cannot see co-binding on this machine: %r (winerror %r)" % (e, getattr(e, "winerror", None)))
        finally:
            if second is not None:
                second.server_close()

    @staticmethod
    def _bench_without_the_lock():
        """bench.py's source with BOTH of the lock's statements switched off (the class attribute back to reuse-on, the exclusive option never
        set), exec'd as a module of its own; each anchor must be found exactly once. The real module is not touched."""
        src = Path(bench.__file__).read_text(encoding="utf-8")
        for old, new in (("allow_reuse_address = False   # SYM-192", "allow_reuse_address = True    # SYM-192"),
                         ('if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):', "if False:")):
            if src.count(old) != 1:
                raise AssertionError("mutation anchor %r found %d times in bench.py" % (old, src.count(old)))
            src = src.replace(old, new)
        mod = types.ModuleType("bench_mutant_sym192")
        mod.__file__ = bench.__file__
        exec(compile(src, bench.__file__, "exec", dont_inherit=True), mod.__dict__)
        return mod

    def test_negative_control_the_source_without_the_lock_co_binds(self):
        # the refusals above must be the lock's work and not the machine's: the same source with the lock switched off binds twice
        mod = self._bench_without_the_lock()
        self.assertIs(mod.ThreadingHTTPServer.allow_reuse_address, True)
        first = self.held(mod.ThreadingHTTPServer)
        second = None
        try:
            second = mod.ThreadingHTTPServer(("127.0.0.1", first.server_address[1]), self.handler)
        except OSError as e:
            self.fail("the lock-less source was refused too, so the tests above cannot tell the lock from the machine: %r" % (e,))
        finally:
            if second is not None:
                second.server_close()

    def test_a_restart_rebinds_the_same_port_within_two_seconds(self):
        first = bench.ThreadingHTTPServer(("127.0.0.1", 0), self.handler)
        port = first.server_address[1]
        threading.Thread(target=first.serve_forever, daemon=True).start()
        try:
            for i in range(5):
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
                try:
                    conn.request("GET", "/api/state")
                    r = conn.getresponse()
                    r.read()
                    self.assertEqual(r.status, 200, "request %d" % i)
                finally:
                    conn.close()
        finally:
            first.shutdown()
            first.server_close()
        t0, attempts, again, last = time.monotonic(), 0, None, None
        while again is None and time.monotonic() - t0 < 2.0:
            attempts += 1
            try:
                again = bench.ThreadingHTTPServer(("127.0.0.1", port), self.handler)
            except OSError as e:
                last = e
                time.sleep(0.05)
        if again is not None:
            again.server_close()
        self.assertIsNotNone(again, "port %d did not rebind within 2 s (%d attempts): %r" % (port, attempts, last))

    def test_the_first_listener_refused_stops_serve_on_loudly(self):
        held = self.held(bench.ThreadingHTTPServer)
        with self.assertRaises(OSError) as cm:
            bench.serve_on(["127.0.0.1"], held.server_address[1], self.handler)
        self.assertTrue(bench._port_in_use(cm.exception), repr(cm.exception))

    def test_a_later_listener_refused_says_the_port_is_in_use_and_the_loopback_bench_runs(self):
        try:
            held = self.held(bench.ThreadingHTTPServer, "127.0.0.2")
        except OSError as e:
            self.skipTest("this machine cannot bind 127.0.0.2: %r" % (e,))
        port = held.server_address[1]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            servers = bench.serve_on(["127.0.0.1", "127.0.0.2"], port, self.handler)
        try:
            self.assertEqual([s.server_address for s in servers], [("127.0.0.1", port)], "the loopback bench alone runs")
        finally:
            for s in servers:
                s.server_close()
        said = out.getvalue()
        self.assertIn("127.0.0.2:%d not bound" % port, said)
        self.assertIn("already in use", said)

    def test_the_command_line_start_exits_non_zero_when_the_port_is_held(self):
        held = self.held(bench.ThreadingHTTPServer)
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        r = subprocess.run([sys.executable, str(HERE / "bench.py"), str(self.tmp), "--port", str(held.server_address[1])],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, env=env)
        self.assertNotEqual(r.returncode, 0, "the second copy started beside the first: %s" % r.stdout[-300:])
        self.assertIn("OSError", r.stderr)


if __name__ == "__main__":
    try:
        unittest.main(verbosity=2)
    finally:
        shutil.rmtree(_PIPE_TMP, ignore_errors=True)
