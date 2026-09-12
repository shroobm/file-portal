#!/usr/bin/env python3
"""observability/error_families.py — THE ERROR CLASS FAMILIES, made mechanical (S123, Rab's order 2026-09-10:
"Start describing error class families, and putting them into our project folder, so then we can derive error
patterns faster, and group them accordingly." — "on all errors.")

Two registers describe two different objects, so there are two tiers of family:

  METHOD families    — from ERROR-BIN.md: how a CLAIM came to outrun its probe (the agent's mistake). Membership is
                       by the row's CLASS cell: every class belongs to exactly one family.
  MECHANISM families — from SYMPTOM-INDEX.md: how the SYSTEM broke. Membership is by row id, placed by a reader
                       (`docs/58-error-class-families/README.md` carries the reasoning); a new SYM row is UNPLACED
                       until it is placed here — the census refuses, so grouping happens at filing time.

    python observability/error_families.py --census              # every row of both registers, by family; exit 1 on
                                                                 # an unknown ERR class or an unplaced SYM row
    python observability/error_families.py --place "<text>"      # the nearest families for a new failure's words
    python observability/error_families.py --selftest            # positive + negative controls (docs/32 §5)

Read-only over the registers; stdlib; CRLF-safe. The document is the judgment half; this is the mechanical half.
"""
from __future__ import annotations

import io
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
ERROR_BIN = REPO / "ERROR-BIN.md"
SYMPTOM_INDEX = REPO / "SYMPTOM-INDEX.md"

# ── METHOD families (ERROR-BIN classes) ──────────────────────────────────────────────────────────────────
# name → (one-line mechanism, discriminating probe, classes)
METHOD = {
    "M1 CLAIM-BEFORE-PROBE": (
        "a confidence word (Verified · done · clean · running · unfiled) is asserted from a delegated report, a memory, "
        "a truncated read or a label — not from a same-turn measurement of the exact predicate",
        "which same-turn printed line, with a failure branch, does this word rest on?",
        ["DELEGATED-TRUST", "OVER-CLAIM", "PREMATURE-ALARM", "STATUS-THEATRE", "PHANTOM-MONITOR", "REGISTER-MISS"],
    ),
    "M2 WRONG-OBJECT-MEASURED": (
        "the probe ran and is internally consistent, but it measured the neighbour of what was asked — the raw file "
        "not the indexed body, the budget meter not the context, the post-override API field not the log",
        "a second measurement of a different shape on the SAME object — do the two agree?",
        ["PROBE-SHAPE", "METER-CONFUSION"],
    ),
    "M3 NUMBER-WITHOUT-ITS-QUESTION": (
        "a count is quoted without its population, or one number secretly sums two predicates over one population; "
        "wrong by question, not by amount — the tell is that it stays plausible when inverted",
        "name the population and the single predicate; recompute; does the number move?",
        ["DENOMINATOR", "PREDICATE-COLLAPSE"],
    ),
    "M4 PREMISE-AGED-BETWEEN-READ-AND-USE": (
        "a value was read or validated once (a GROUND number, a beat, a loaded record, an environment pin) and "
        "trusted later, after the world moved — time-of-check is not time-of-use",
        "re-derive the value from its live source at the moment of use — does it match what was assumed?",
        ["STALE-GROUND", "STALE-SNAPSHOT", "PARTIAL-PUBLISH"],
    ),
    "M5 ORDER-ASSUMED-NOT-PROVEN": (
        "a sequence (recorded-before-acting, two rounds, clean-after-commit, timed-out-before-hanging) is inferred "
        "from membership, not proven from the boundary events' timestamps or commit order",
        "name the two boundary events; read their real timestamps or SHAs; is the order what was claimed?",
        ["ORDERING", "BOUNDARY-OMISSION"],
    ),
    "M6 GUARD-NARROWER-THAN-THE-CLAIM": (
        "the lock, validator or record covers most of the surface — types, digests, one file's id floor, the lane "
        "address — and misses the one occupant, consumer, reference surface or predicate that defines correctness",
        "enumerate every surface the claim touches; plant one violation outside the tested scope — does the guard fire?",
        ["LOCK-SCOPE", "DEAD-SURFACE", "PROVENANCE-DROP", "NAMESPACE-SCOPE"],
    ),
    "M7 THE-LAYER-BELOW-ATE-THE-COMMAND": (
        "the shell, quoting, a persisted cwd, a short-circuit operator, a stale test double or a repo-identity refusal "
        "changed the command before the runtime saw it, and the empty or wrong result was read as product evidence",
        "rerun the identical intent through a form immune to the suspected artefact (a file via Write, an absolute path, "
        "an explicit safe.directory) — does the result change?",
        ["HARNESS-MISUSE", "QUOTING"],
    ),
    "M8 AN-INERT-ACT-REACHED-A-WIDER-SCOPE": (
        "a read-only or private act (a lock, a manifest read, a planted decoy) left residue in the tracked tree or "
        "reached an audience it was meant to be hidden from",
        "diff the scope boundary (git status; the audience list) immediately before and after the 'inert' step",
        ["RUNTIME-RESIDUE", "CONTROL-LEAK"],
    ),
    "M9 CONTEXT-BECAME-THE-REQUEST": (
        "benign work refused because the agent's name, inherited priming or adversarial verbs became part of the "
        "effective request",
        "resend the same scoped, local, read-only task under a fresh neutrally named agent — does it succeed?",
        ["DELEGATION-SHAPE"],
    ),
}

# ── MECHANISM families (SYMPTOM-INDEX rows, placed by id) ─────────────────────────────────────────────────
# name → (one-line mechanism, discriminating probe, SYM ids)
MECHANISM = {
    "S1 BYTES-CHANGE-BETWEEN-LAYERS": (
        "the layer between you and the bytes rewrites them: core.autocrlf stores LF and checks out CRLF; MSYS turns a "
        "/Flag into a path; the harness collapses an escape; a second toolchain keeps its own state",
        "compare the bytes on both sides of the layer: git show HEAD:<f> | grep -cU $'\\r' vs grep -cU $'\\r' <f>; "
        "the same command from PowerShell vs Git Bash",
        ["SYM-004", "SYM-017", "SYM-029", "SYM-036", "SYM-078", "SYM-079", "SYM-080", "SYM-082", "SYM-087"],
    ),
    "S2 GREEN-WITHOUT-A-MEASUREMENT": (
        "a pass, a green badge, a 1.0 or an exit 0 is derived from something other than the property — the system's "
        "own output, the exit code of the wrong pipeline stage, a post-override API field",
        "mutate what the check claims to verify (swap the algorithm, fail the gated stage, read the log) — does it go RED?",
        ["SYM-001", "SYM-038", "SYM-046", "SYM-055", "SYM-056", "SYM-075", "SYM-077", "SYM-100"],
    ),
    "S3 A-DEFAULT,-CAP-OR-CUT-WEARING-A-NUMBER": (
        "an unmeasured branch returns a value that looks measured: a default 'unknown' as an identity, a display cap "
        "read as the population, a truncation with no marker",
        "force the unmeasurable branch or exceed the cap — does the surface say UNREAD/total, or a plausible number?",
        ["SYM-005", "SYM-044", "SYM-052", "SYM-057", "SYM-066", "SYM-070", "SYM-088"],
    ),
    "S4 FAILED-PROBE-RENDERED-AS-NEGATIVE": (
        "the probe errored, timed out or could not match, and the surface printed a definite negative — down, clean, "
        "absent, no drift — instead of UNREAD",
        "make the probe fail on purpose (bad path, wrapped text, refused command) — does the surface say UNREAD?",
        # SYM-111 (S130): the events-mode tracker read a command line AFTER the start event and rendered a
        # gone process as an EMPTY cell, a dropped stop event as "still running" — a failed read printed as a reading
        ["SYM-024", "SYM-031", "SYM-034", "SYM-063", "SYM-071", "SYM-111"],
    ),
    "S5 A-GUARD-OFF-THE-PATH-THE-WORK-TAKES": (
        "the lock file, detector, CI trigger or job object sits on one entry path; a manual run, a feature branch, a "
        "zero-area geometry or a foreign process takes another and is invisible to every reader",
        "list every entry point that touches the guarded resource; one with zero writes to the signal is this family",
        # SYM-113 (S130 post-close): the ledger row's only parser sits on the OPEN path; the close writes the row
        # after its own gates and never reads it back — a malformed row is invisible until the next session
        ["SYM-018", "SYM-020", "SYM-032", "SYM-042", "SYM-047", "SYM-049", "SYM-054", "SYM-089", "SYM-107", "SYM-113"],
    ),
    "S6 THE-CHILD-OUTLIVES-THE-KILL": (
        "the kill, close or job is scoped to the direct child or one window; the real worker is a grandchild (a venv "
        "launcher's interpreter), a sibling or a shell chain's next command, and survives the event meant to end it",
        "kill the intended parent, then census survivors by command line and parent pid — a survivor is this family",
        ["SYM-006", "SYM-021", "SYM-022", "SYM-033", "SYM-068", "SYM-069"],
    ),
    "S7 PRODUCED-BUT-NEVER-PROJECTED": (
        "a phase computes and stores a correct value and no renderer reads it, reads another object, or shows it beside "
        "an unrelated verdict; or a surface promises a live lever the code baked in once",
        "grep the producer for the key, then every renderer for a read of that key — writes without reads",
        ["SYM-026", "SYM-027", "SYM-041", "SYM-043", "SYM-053", "SYM-058", "SYM-059", "SYM-060", "SYM-061", "SYM-092", "SYM-102", "SYM-103", "SYM-106"],
    ),
    "S8 A-FACT-FROZEN-WHILE-THE-WORLD-MOVED": (
        "a number, SHA, date or topology assumption typed once into prose, a guard or a default and never regenerated; "
        "healthy activity (a commit, a rewrap, a new window, a new day) falsifies it",
        "re-derive the cited value from its live source (rev-parse, the suite, the dependency's metadata) and diff",
        ["SYM-014", "SYM-016", "SYM-019", "SYM-023", "SYM-039", "SYM-065", "SYM-072", "SYM-098", "SYM-108", "SYM-117"],
    ),
    "S9 THE-WRONG-REFERENCE-OBJECT": (
        "an index, key or comparison target is computed from the wrong object — an offset already absolute, a "
        "sanitised stem, a positional 'newest', the pre-analyst body against the post-analyst one",
        "trace one flagged item by hand to its reference object; does the formula double-apply, or compare two texts?",
        ["SYM-002", "SYM-013", "SYM-025", "SYM-028", "SYM-050", "SYM-073", "SYM-114"],  # 114 (S131): the reference carried the disease
    ),
    "S10 IDENTITY-FROM-THE-WRONG-EVIDENCE": (
        "an identity or authority check reads a proxy — a pid that belongs to a launcher, a local counter for a global "
        "namespace, a decision string's length for a human's ruling",
        "what evidence would an impostor lack that this check actually reads? if the answer is 'nothing', this family",
        ["SYM-040", "SYM-045", "SYM-062", "SYM-081"],
    ),
    "S11 UNBOUNDED-OR-UNGUARDED-EFFECT": (
        "a destructive or blocking act has no guard: an rmtree over held state, an append that assumes a terminator, a "
        "fixture port that reaches the live server, a wait with no bound, an artefact that disables its own producer",
        "name the precondition the act assumes; violate it in a fixture — what happens to the held state or the clock?",
        # SYM-083 (ThinkPad S123): fastembed's default batch of 256 × a 512-token padded window → 9 GiB RSS —
        # a hidden-cost default, the shape of SYM-048's `xrefs=True`
        ["SYM-009", "SYM-010", "SYM-030", "SYM-037", "SYM-048", "SYM-064", "SYM-083", "SYM-085", "SYM-099"],
    ),
    "S12 PLATFORM-OR-LIBRARY-SEMANTICS-TRAP": (
        "the platform or library means something other than its name: force_ocr keeps the old text, inotify reports a "
        "move as create, MSIX virtualises writes and kills on update, a base interpreter is missing",
        "read the producer's own definition (its source or docs) of the flag or event before trusting the name",
        # SYM-084 (ThinkPad S123): Taildrop moves files only between devices of the same tailnet user; a tagged
        # node has no user — the platform's own definition, not its name
        ["SYM-007", "SYM-008", "SYM-011", "SYM-012", "SYM-015", "SYM-051", "SYM-084", "SYM-086", "SYM-101", "SYM-105", "SYM-109", "SYM-094", "SYM-112"],  # 094 moved S15 → S12 (S124 cross-check: the root is find_tables' semantics)
    ),
    "S13 MODEL-OUTPUT-HAZARD": (
        "the language model's own behaviour: degeneration loops on tabular structure; control tokens leaking into text",
        "diff the model's output against its input under the fence; count repeats and control tokens",
        ["SYM-003", "SYM-074", "SYM-115"],  # 115 (S131): a second leaked control token
    ),
    "S14 CONFOUNDED-COMPARISON": (
        "two arms run under a systematically different condition (heat, order), so the artefact scales with n like a "
        "real effect",
        "swap the arm order or interleave; does the effect survive?",
        ["SYM-035"],
    ),
    "S15 THE-INSTRUMENT-MANUFACTURES-THE-FINDING": (
        "the audit, census or ladder has its own preprocessing bug or unstated input-shape assumption and creates false "
        "loss or coverage indistinguishable from real defects until traced to the check itself",
        "re-derive the figure through a second, independently built extractor/parser — does the number move while the "
        "artefact does not?",
        ["SYM-067", "SYM-076", "SYM-095", "SYM-097"],
    ),
    "S16 GUARD-COARSER-THAN-THE-DEFECT": (
        "the guard's resolution is coarser than the defect (a window-overlap fraction cannot see one digit; a "
        "one-directional metric cannot see gain); moderate real loss passes at the margin",
        "plant a defect one notch below the guard's resolution — does it pass?",
        ["SYM-090", "SYM-091", "SYM-093", "SYM-096", "SYM-104", "SYM-110", "SYM-116"],  # S137: 116 the heredoc bypass beside the false deny; S124 (J55): the four closeout findings named above now have rows, plus S106 §10 f; S126: the guard's own false denies
    ),
}

# signature words for --place (lower-case substrings); a family's probe is the answer
SIGNATURES = {
    "M1 CLAIM-BEFORE-PROBE": ["verified", "confirmed", "done", "clean", "running", "monitor", "unfiled", "no register", "exists", "does not exist"],
    "M2 WRONG-OBJECT-MEASURED": ["measured", "wrong file", "raw", "meter", "counter", "api", "conclusion", "neighbour", "index", "column"],
    "M3 NUMBER-WITHOUT-ITS-QUESTION": ["percent", "%", "total", "count", "denominator", "population", "mean", "average", "two totals", "inverted"],
    "M4 PREMISE-AGED-BETWEEN-READ-AND-USE": ["ground", "stale", "snapshot", "earlier", "inherited", "pinned", "beat", "toctou", "between"],
    "M5 ORDER-ASSUMED-NOT-PROVEN": ["before", "after", "order", "sequence", "commit", "amend", "round", "timestamp", "record first"],
    "M6 GUARD-NARROWER-THAN-THE-CLAIM": ["lock", "scope", "occupant", "namespace", "consumer", "renders", "allocator", "boundary"],
    "M7 THE-LAYER-BELOW-ATE-THE-COMMAND": ["heredoc", "quote", "backslash", "backtick", "cwd", "cd ", "||", "safe.directory", "dubious", "argv", "exit code 0"],
    "M8 AN-INERT-ACT-REACHED-A-WIDER-SCOPE": ["untracked", "residue", ".venv", "uv.lock", "lock file", "decoy", "leak", "audience"],
    "M9 CONTEXT-BECAME-THE-REQUEST": ["refused", "agent name", "priming", "attack", "classifier"],
    "S1 BYTES-CHANGE-BETWEEN-LAYERS": ["crlf", "lf", "autocrlf", "byte-prefix", "msys", "/create", "/fi", "escape", "known_hosts", "\\r"],
    "S2 GREEN-WITHOUT-A-MEASUREMENT": ["green", "pass", "exit 0", "1.0", "self-referential", "pipefail", "sigpipe", "continue-on-error", "badge"],
    "S3 A-DEFAULT,-CAP-OR-CUT-WEARING-A-NUMBER": ["unknown", "default", "cap", "capped", "[:25]", "truncat", "400 chars", "shown"],
    "S4 FAILED-PROBE-RENDERED-AS-NEGATIVE": ["unread", "down", "absent", "not a git repo", "stderr", "empty parse", "negative observation"],
    "S5 A-GUARD-OFF-THE-PATH-THE-WORK-TAKES": ["gpu-lock", "path", "entry point", "manual run", "--resume", "trigger", "branch", "zero-area", "job object"],
    "S6 THE-CHILD-OUTLIVES-THE-KILL": ["kill", "orphan", "grandchild", "launcher", "taskkill", "/t", "tree", "window", "survives"],
    "S7 PRODUCED-BUT-NEVER-PROJECTED": ["renderer", "never read", "projection", "field", "payload", "lever", "baked", "surface"],
    "S8 A-FACT-FROZEN-WHILE-THE-WORLD-MOVED": ["hardcoded", "orphaned sha", "frozen", "prose", "unpinned", "filename date", "rewrap", "topology"],
    "S9 THE-WRONG-REFERENCE-OBJECT": ["offset", "doubled", "stem", "position", "tail -1", "pre-analyst", "post-analyst", "reference"],
    "S10 IDENTITY-FROM-THE-WRONG-EVIDENCE": ["pid", "identity", "counter", "monotonic", "len(", "authority", "impostor", "proxy"],
    "S11 UNBOUNDED-OR-UNGUARDED-EFFECT": ["rmtree", "overwrite", "append", "terminator", "port", "so_reuseaddr", "timeout", "blocking", "askpass"],
    "S12 PLATFORM-OR-LIBRARY-SEMANTICS-TRAP": ["force_ocr", "inotify", "msix", "virtualiz", "servicing", "missing", "flag means"],
    "S13 MODEL-OUTPUT-HAZARD": ["degenerat", "loop", "</think>", "control token", "model emits", "repeat"],
    "S14 CONFOUNDED-COMPARISON": ["confound", "thermal", "arm", "order", "scales with n"],
    "S15 THE-INSTRUMENT-MANUFACTURES-THE-FINDING": ["audit", "ladder", "census", "false loss", "survival", "unescape", "extractor", "manufactur"],
    "S16 GUARD-COARSER-THAN-THE-DEFECT": ["threshold", "margin", "granularity", "window-overlap", "one-directional", "resolution"],
}

# The class cell may be bold (ERR-014: `**PREDICATE-COLLAPSE**`) or carry a parenthetical (ERR-056: `CONTROL-LEAK
# (new class)`); a SYM id cell may carry a provenance note (SYM-037..039: `SYM-037 *(was SYM-028, ThinkPad lane…)*`).
# The first census missed exactly those four rows — the guard fired on real history before the tool was trusted.
ERR_ROW = re.compile(r"^\| (ERR-\d{4}-\d\d-\d\d-\d{3}) \| \*{0,2}([A-Z][A-Z /-]*?)\*{0,2}\s*(?:\([^)]*\))?\s*\|")
SYM_ROW = re.compile(r"^\| (SYM-\d{3})\b[^|]*\|")


def _lines(path: Path):
    return io.open(path, encoding="utf-8", newline="").read().replace("\r\n", "\n").split("\n")


def read_error_bin(path: Path):
    """[(id, class)] for every §B row; the class cell may carry a parenthetical ('(new class)')."""
    out = []
    for line in _lines(path):
        m = ERR_ROW.match(line)
        if m:
            out.append((m.group(1), m.group(2).strip()))
    return out


def read_symptom_index(path: Path):
    """[(id, symptom-cell-head)] for every SYM row."""
    out = []
    for line in _lines(path):
        m = SYM_ROW.match(line)
        if m:
            cells = line.split("|")
            out.append((m.group(1), (cells[2].strip() if len(cells) > 2 else "")[:80]))
    return out


def class_family():
    fam = {}
    for name, (_m, _p, classes) in METHOD.items():
        for c in classes:
            if c in fam:
                raise SystemExit(f"CONFIG: class {c} placed in two families ({fam[c]}, {name})")
            fam[c] = name
    return fam


def sym_family():
    fam = {}
    for name, (_m, _p, ids) in MECHANISM.items():
        for i in ids:
            if i in fam:
                raise SystemExit(f"CONFIG: {i} placed in two families ({fam[i]}, {name})")
            fam[i] = name
    return fam


def census(error_bin: Path, symptom_index: Path, out=sys.stdout) -> int:
    rc = 0
    cf, sf = class_family(), sym_family()
    errs = read_error_bin(error_bin)
    syms = read_symptom_index(symptom_index)
    counts = {name: 0 for name in list(METHOD) + list(MECHANISM)}
    unknown_classes, unplaced = [], []
    for eid, klass in errs:
        f = cf.get(klass)
        if f is None:
            unknown_classes.append((eid, klass))
        else:
            counts[f] += 1
    for sid, head in syms:
        f = sf.get(sid)
        if f is None:
            unplaced.append((sid, head))
        else:
            counts[f] += 1
    print(f"ERROR FAMILIES census · {error_bin.name}: {len(errs)} rows · {symptom_index.name}: {len(syms)} rows", file=out)
    print("  METHOD families (by class):", file=out)
    for name, (mech, probe, classes) in METHOD.items():
        print(f"    {name:42s} {counts[name]:3d}   classes: {', '.join(classes)}", file=out)
    print("  MECHANISM families (by id):", file=out)
    for name, (mech, probe, ids) in MECHANISM.items():
        print(f"    {name:42s} {counts[name]:3d}   placed ids: {len(ids)}", file=out)
    placed_syms = sum(counts[n] for n in MECHANISM)
    placed_errs = sum(counts[n] for n in METHOD)
    print(f"  placed: ERR {placed_errs}/{len(errs)} · SYM {placed_syms}/{len(syms)}", file=out)
    if unknown_classes:
        rc = 1
        for eid, klass in unknown_classes:
            print(f"  UNKNOWN CLASS — place it in a METHOD family before filing: {eid} class {klass!r}", file=out)
    if unplaced:
        rc = 1
        for sid, head in unplaced:
            print(f"  UNPLACED — place it in a MECHANISM family (or a new one) before filing: {sid} · {head}", file=out)
    # a family placed id that is not in the register is a config drift, not a register fault
    known_syms = {s for s, _ in syms}
    ghosts = [i for i in sf if i not in known_syms]
    if ghosts:
        rc = 1
        print(f"  GHOST — placed ids absent from the register: {ghosts}", file=out)
    print("  exit", rc, "(1 = a row is unplaced or its class unknown; UNREAD never renders as placed)", file=out)
    return rc


def place(text: str, out=sys.stdout) -> int:
    t = text.lower()
    scored = []
    for name, words in SIGNATURES.items():
        hits = [w for w in words if w.lower() in t]
        if hits:
            scored.append((len(hits), name, hits))
    if not scored:
        print("UNREAD — no family signature matched; read docs/58 §3 (the placing walk) and place by the probe", file=out)
        return 1
    scored.sort(key=lambda x: (-x[0], x[1]))
    for n, name, hits in scored[:3]:
        table = METHOD if name in METHOD else MECHANISM
        mech, probe, _ = table[name]
        print(f"{name}  (matched {n}: {', '.join(hits)})", file=out)
        print(f"   mechanism: {mech}", file=out)
        print(f"   probe:     {probe}", file=out)
    return 0


def selftest() -> int:
    passed = total = 0

    def check(name, ok):
        nonlocal passed, total
        total += 1
        passed += bool(ok)
        print(("PASS" if ok else "FAIL"), f"{total} — {name}")

    sink = io.StringIO()
    # 1 positive control: the live registers place completely
    rc = census(ERROR_BIN, SYMPTOM_INDEX, out=sink)
    check("live registers: every ERR class known and every SYM row placed (exit 0)", rc == 0)
    # 2 the class table's own classes are all in exactly one family (config sanity)
    check("every METHOD class placed once", len(class_family()) == sum(len(c) for _, _, c in METHOD.values()))
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        eb = d / "ERROR-BIN.md"
        si = d / "SYMPTOM-INDEX.md"
        base_err = io.open(ERROR_BIN, encoding="utf-8", newline="").read()
        base_sym = io.open(SYMPTOM_INDEX, encoding="utf-8", newline="").read()
        # 3 negative: an unknown class is REFUSED
        io.open(eb, "w", encoding="utf-8", newline="").write(base_err + "\n| ERR-2099-01-01-999 | NOVEL-CLASS | x | y | z | w | r |\n")
        io.open(si, "w", encoding="utf-8", newline="").write(base_sym)
        sink = io.StringIO()
        rc = census(eb, si, out=sink)
        check("negative: a row with an unknown class exits 1 and is named", rc == 1 and "NOVEL-CLASS" in sink.getvalue())
        # 4 negative: an unplaced SYM row is REFUSED
        io.open(eb, "w", encoding="utf-8", newline="").write(base_err)
        io.open(si, "w", encoding="utf-8", newline="").write(base_sym + "\n| SYM-999 | a brand new symptom | cause | S999 | OPEN | nowhere |\n")
        sink = io.StringIO()
        rc = census(eb, si, out=sink)
        check("negative: an unplaced SYM row exits 1 and is named", rc == 1 and "SYM-999" in sink.getvalue())
        # 5 the parser survives CRLF and the 5-pipe rows (059-062 have a merged cell)
        crlf = base_err.replace("\n", "\r\n")
        io.open(eb, "w", encoding="utf-8", newline="").write(crlf)
        n_crlf = len(read_error_bin(eb))
        n_lf = len(read_error_bin(ERROR_BIN))
        check(f"parser: CRLF and LF copies read the same row count ({n_crlf})", n_crlf == n_lf and n_lf >= 67)
        check("parser: the 5-pipe rows (ERR-…-059…062) are read with their class",
              dict(read_error_bin(ERROR_BIN)).get("ERR-2026-09-05-059") == "METER-CONFUSION"
              and dict(read_error_bin(ERROR_BIN)).get("ERR-2026-09-09-062") == "ORDERING")
    # 6 --place lands planted texts in the expected family, and nonsense is UNREAD
    for text, expect in (
        ("git show HEAD:relay.md is not a byte-prefix of the working copy under core.autocrlf", "S1 "),
        ("a subagent reported Verified and I relayed it to Rab without running the probe", "M1 "),
        ("the suite prints green but grep -q under pipefail returned 141 with the string present", "S2 "),
        ("taskkill on the pid left the venv launcher's grandchild interpreter alive", "S6 "),
    ):
        sink = io.StringIO()
        place(text, out=sink)
        first = sink.getvalue().splitlines()[0] if sink.getvalue() else ""
        check(f"place: {text[:48]!r}… → {expect.strip()}", first.startswith(expect))
    sink = io.StringIO()
    rc = place("zzzz qqqq", out=sink)
    check("place: nonsense renders UNREAD, never a family", rc == 1 and "UNREAD" in sink.getvalue())
    print(f"════ error_families selftest: {passed}/{total} ════")
    return 0 if passed == total else 1


def main(argv) -> int:
    if "--selftest" in argv:
        return selftest()
    if "--place" in argv:
        i = argv.index("--place")
        return place(" ".join(argv[i + 1:]))
    return census(ERROR_BIN, SYMPTOM_INDEX)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
