"""Verifier (Fable) - own re-run of lane A's decisive probes for J32. Read-only on repo + library.
Reference rebuilt from the LIBRARY slice cache. Real fidelity_audit + analyst functions.
Own normalisation regexes (different from lane A's and the builder's) PLUS the builder's own
regexes run through the cumulative 3-step the builder never measured. Position-aware chunk
attribution. Chunk 23/78 paragraph containment in the SHIPPED body. Journal provenance
(resume key). Per-chunk survival = a deletion-guard measurement. Controls."""
import bisect
import glob
import hashlib
import json
import re
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, "C:/Users/Bndit/Projects/file-portal/windows-converter")
import fidelity_audit as fa  # noqa: E402
import analyst  # noqa: E402

V = ("C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/"
     "3567c0ef-5c0b-42cf-8101-4bb783f0ee67/scratchpad/verify-tickets/V")
LIB = "C:/Users/Bndit/ml/library/.chunk-work/14c66834bdfeaa2e"
HELD_DIR = "C:/Users/Bndit/ml/library/held/14c66834bdfeaa2e"
JOURNAL = Path("C:/Users/Bndit/ml/library/.analyst-work/d58db211c41b0e17/chunks.jsonl")
R = {}
t0 = time.perf_counter()


def lap():
    return f"{time.perf_counter() - t0:.0f}s"


slices = sorted(glob.glob(LIB + "/slice-*/slice.md"))
marker_raw = "\n\n".join(open(p, encoding="utf-8").read() for p in slices)
# the pipeline hands the analyst rewrite_image_links(markdown): ![x](t) -> ![[assets/name]]
_IMAGE_LINK = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def rewrite_image_links(md):
    def _r(m):
        t = m.group(1)
        if t.startswith(("http://", "https://", "data:")):
            return m.group(0)
        return f"![[assets/{Path(t).name}]]"
    return _IMAGE_LINK.sub(_r, md)


marker = rewrite_image_links(marker_raw)
held_raw = open(glob.glob(HELD_DIR + "/*.md")[0], encoding="utf-8").read()
held_body = held_raw.split("---\n", 2)[2]
manifest = json.load(open(HELD_DIR + "/manifest.json", encoding="utf-8"))
R["inputs"] = {"n_slices": len(slices), "marker_raw_chars": len(marker_raw),
               "marker_rewritten_chars": len(marker), "held_body_chars": len(held_body),
               "sha16_marker_raw": hashlib.sha256(marker_raw.encode()).hexdigest()[:16],
               "WINDOW_WORDS": fa.WINDOW_WORDS, "ANALYST_DOC_FAIL": fa.ANALYST_DOC_FAIL,
               "ANALYST_RUN_WORDS": fa.ANALYST_RUN_WORDS}

# 1. mirror with the real audit_analyst, both reference forms
for name, ref_text in (("raw_join", marker_raw), ("rewritten", marker)):
    res = fa.audit_analyst(ref_text, held_body)
    R[f"mirror_{name}"] = {"doc_survival": res["doc_survival"], "runs_total": res["runs_total"],
                           "max_run_words": max(r["words"] for r in res["runs"])}
R["manifest_analyst"] = {"doc_survival": manifest["fidelity"]["analyst"]["doc_survival"],
                         "runs_total": manifest["fidelity"]["analyst"]["runs_total"]}
print("mirror:", R["mirror_raw_join"], R["mirror_rewritten"], R["manifest_analyst"], lap(), flush=True)

ref0, out0 = fa.prepare_output(marker), fa.prepare_output(held_body)
win0 = fa.make_windows(ref0, False)
fail0 = [w not in out0 for w in win0]
R["baseline"] = {"windows": len(win0), "failed": sum(fail0),
                 "doc_survival": round((len(win0) - sum(fail0)) / len(win0), 4)}
print("baseline:", R["baseline"], lap(), flush=True)


# 2. ladder - OWN regexes (not lane A's backslash-any, not the builder's char-class)
def my_unescape(t):
    # a backslash before punctuation/symbol only; a backslash before a letter is LaTeX (\rm) and stays
    return re.sub(r"\\(?=[^\w\s])", "", t)


def my_punct_free(t):
    # keep letters (any script) / digits / spaces; everything else -> space
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]|_", " ", t)).strip()


def rung(ref, out, spacefree):
    wins = fa.make_windows(ref, False)
    if spacefree:
        o = out.replace(" ", "")
        f = [w.replace(" ", "") not in o for w in wins]
    else:
        f = [w not in out for w in wins]
    runs = fa._merge_runs(wins, f, page=None)
    return ({"windows": len(wins), "failed": sum(f),
             "doc_survival": round((len(wins) - sum(f)) / len(wins), 4),
             "runs": len(runs), "max_run_words": max((r["words"] for r in runs), default=0)}, wins, f)


L = {}
ref1, out1 = fa.prepare_output(my_unescape(marker)), fa.prepare_output(my_unescape(held_body))
L["1_unescape"], w1, f1 = rung(ref1, out1, False)
L["2b_unescape+space (the builder 0.9718 shape)"], w2b, f2b = rung(ref1, out1, True)
ref2, out2 = my_punct_free(ref1), my_punct_free(out1)
L["2_unescape+punct"], _, _ = rung(ref2, out2, False)
L["3_unescape+punct+space"], w3, f3 = rung(ref2, out2, True)
print("ladder(own):", json.dumps(L), lap(), flush=True)
R["ladder_own"] = L
# 2c. the BUILDER's regexes, cumulative 3-step (classify2.py skipped it: both space-free variants hit `continue`)
ESC = re.compile(r"\\([\\`*_{}\[\]()#+\-.!$|<>~])")


def bstrip(s):
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", " ", s)


bref1, bout1 = fa.prepare_output(ESC.sub(r"\1", marker)), fa.prepare_output(ESC.sub(r"\1", held_body))
B = {}
B["1_unescape"], _, _ = rung(bref1, bout1, False)
B["2b_unescape+space"], bw2b, bf2b = rung(bref1, bout1, True)
bref2, bout2 = fa._finalize(bstrip(bref1)), fa._finalize(bstrip(bout1))
B["2_unescape+punct"], _, _ = rung(bref2, bout2, False)
B["3_unescape+punct+space (NEVER measured by the builder)"], bw3, bf3 = rung(bref2, bout2, True)
R["ladder_builder_regexes"] = B
print("ladder(builder regexes):", json.dumps(B), lap(), flush=True)

# 3. chunking + position-aware attribution
fenced, embeds = analyst.fence(marker)
chunks = analyst._chunks(fenced)
low = fenced.lower()
starts = [0]
for c in chunks[:-1]:
    starts.append(starts[-1] + len(c) + 2)   # chunks are re-joined with a blank line in process()
R["chunks"] = {"n": len(chunks), "embeds": len(embeds),
               "manifest_passed+rejected": manifest["analyst"]["chunks_passed"] + manifest["analyst"]["chunks_rejected"]}


def attribute(wins, fails, nwords=6):
    per, idxs = {}, []
    located = unlocated = 0
    pos = 0
    for w, f in zip(wins, fails):
        if not f:
            continue
        key = " ".join(w.split()[:nwords])
        k = low.find(key, max(0, pos - 30000))
        if k < 0:
            k = low.find(key)
        if k < 0:
            unlocated += 1
            continue
        pos = k
        located += 1
        i = bisect.bisect_right(starts, k)
        per[i] = per.get(i, 0) + 1
        idxs.append(i)
    tot = sum(per.values())
    cum = n80 = 0
    for i, n in sorted(per.items(), key=lambda kv: -kv[1]):
        cum += n
        n80 += 1
        if cum >= 0.8 * tot:
            break
    return ({"located": located, "unlocated": unlocated,
             "located_rate": round(located / max(1, located + unlocated), 3),
             "chunks_with_loss": len(per), "chunks_for_80pct": n80,
             "front_matter_chunks_1_15": sum(v for k, v in per.items() if k <= 15),
             "median_chunk": statistics.median(idxs) if idxs else None,
             "top10": sorted(per.items(), key=lambda kv: -kv[1])[:10]}, per)


R["attrib_baseline"], per0 = attribute(win0, fail0)
R["attrib_rung2b_own"], per2b = attribute(w2b, f2b)
R["attrib_rung3_own"], per3 = attribute(w3, f3)
R["attrib_rung2b_builder"], perb = attribute(bw2b, bf2b)
for k in ("attrib_baseline", "attrib_rung2b_own", "attrib_rung3_own", "attrib_rung2b_builder"):
    print(k, R[k], flush=True)
R["chunk1_head"] = re.sub(r"\s+", " ", chunks[0][:160])
R["chunk15_head"] = re.sub(r"\s+", " ", chunks[14][:120])


# 4. chunk 23 / 78 / 296 / 678 / 128: paragraph containment in the SHIPPED body (journal-independent)
def para_test(i):
    ch = chunks[i - 1]
    paras = [p for p in re.split(r"\n\s*\n", ch) if len(p.split()) >= 8]
    present = absent = absent_words = 0
    heads = []
    for p in paras:
        pp = fa.prepare_output(p)
        if not pp:
            continue
        wins = fa.make_windows(pp, False)
        hit = sum(1 for w in wins if w in out0)
        if pp in out0 or (wins and hit == len(wins)):
            present += 1
        else:
            absent += 1
            absent_words += len(pp.split())
            heads.append(pp[:80])
    return {"chunk_chars": len(ch), "chunk_words": len(ch.split()), "paras_ge8w": len(paras),
            "paras_present": present, "paras_absent": absent, "absent_words": absent_words,
            "absent_heads": heads[:4]}


for i in (23, 78, 296, 678, 128):
    R[f"chunk{i}"] = para_test(i)
    print(f"chunk{i}:", R[f"chunk{i}"], flush=True)

# 5. journal: resume key + validation + rejected + per-chunk survival (deletion-guard measurement)
key_raw = analyst._resume_key(analyst.fence(marker_raw)[0], "local", "readability")
key_rw = analyst._resume_key(fenced, "local", "readability")
lines = [ln for ln in JOURNAL.read_text(encoding="utf-8").splitlines() if ln.strip()]
jr = analyst._load_journal(JOURNAL, chunks)
jr_raw = analyst._load_journal(JOURNAL, analyst._chunks(analyst.fence(marker_raw)[0]))
rej = [i for i, r in jr.items() if r.get("status") == "rejected"]
R["journal"] = {"dir_key_on_disk": "d58db211c41b0e17", "resume_key_rewritten": key_rw,
                "resume_key_raw_join": key_raw, "raw_lines": len(lines),
                "validated_same_index_rewritten": len(jr), "validated_same_index_raw": len(jr_raw),
                "rejected_validated": len(rej), "manifest_rejected": manifest["analyst"]["chunks_rejected"],
                "manifest_resumed": manifest["analyst"]["chunks_resumed"],
                "loss_in_rejected_baseline": sum(per0.get(i, 0) for i in rej),
                "loss_in_rejected_rung2b_own": sum(per2b.get(i, 0) for i in rej),
                "loss_in_rejected_rung2b_builder": sum(perb.get(i, 0) for i in rej)}
# deletion guard: per-chunk 12-word-window survival of the INPUT chunk in the journal's OUTPUT (passed records only)
surv = []
for i, r in jr.items():
    if r.get("status") != "passed":
        continue
    pin, pout = fa.prepare_output(chunks[i - 1]), fa.prepare_output(r["text"])
    wins = fa.make_windows(pin, False)
    if not wins:
        continue
    ok = sum(1 for w in wins if w in pout)
    surv.append((i, round(ok / len(wins), 4), len(wins), len(pin.split()), len(pout.split()), per0.get(i, 0)))
surv.sort(key=lambda t: t[1])
R["journal"]["passed_validated_with_windows"] = len(surv)
for th in (0.5, 0.8, 0.9, 0.95, 0.98, 0.995):
    below = [s for s in surv if s[1] < th]
    R["journal"][f"passed_chunks_below_{th}"] = {"chunks": len(below),
                                                "baseline_loss_windows_they_carry": sum(s[5] for s in below)}
R["journal"]["worst10_passed"] = surv[:10]
R["journal"]["total_baseline_loss_in_validated_passed"] = sum(s[5] for s in surv)
R["journal"]["word_ratio_lt_0.9"] = sum(1 for s in surv if s[4] < 0.9 * s[3])
for i in (23, 78):
    r = jr.get(i)
    R["journal"][f"chunk{i}"] = ({"status": r["status"], "out_chars": len(r["text"]),
                                  "in_chars": len(chunks[i - 1])} if r else "no validated record")
print("journal:", json.dumps(R["journal"]), lap(), flush=True)

# 6. mentions
R["mentions"] = {pat: {"marker": len(re.findall(pat, marker.lower())),
                       "held": len(re.findall(pat, held_body.lower()))}
                 for pat in (r"figure \d+\.\d+", r"table \d+\.\d+")}
# 7. controls
pos = next(w for w, f in zip(win0, fail0) if not f and len(w.split()) == 12)
words = pos.split()
words[5] = "xqzplonkotron9999"
poison = " ".join(words)
R["controls"] = {"positive_passes_baseline": pos in out0, "poison_fails_baseline": poison not in out0,
                 "poison_fails_unescape": poison not in out1,
                 "poison_fails_punct": my_punct_free(poison) not in out2,
                 "poison_fails_space": my_punct_free(poison).replace(" ", "") not in out2.replace(" ", "")}
esc_example = None
for w, f in zip(win0, fail0):
    if f and "\\" in w:
        u = fa.prepare_output(my_unescape(w))
        if u in out1:
            esc_example = {"before": w, "after_unescape": u}
            break
R["controls"]["escape_only_example"] = esc_example
print("mentions:", R["mentions"], "controls:", R["controls"], flush=True)
R["wall_s"] = round(time.perf_counter() - t0, 1)
json.dump(R, open(V + "/v_a_result.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("DONE", R["wall_s"], "s")
