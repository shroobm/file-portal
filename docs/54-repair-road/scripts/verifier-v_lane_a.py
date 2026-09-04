"""Verifier re-run of lane A's decisive probes (J32). Read-only on repo + library.
Own reference rebuild from the LIBRARY slice cache (not the scratch copies), the real
fidelity_audit.audit_analyst, an independent normalisation ladder, own chunk attribution,
chunk 23/78 deletion-vs-rewording test, rejected-chunk windows, front matter, negative control."""
import bisect
import glob
import json
import re
import statistics
import sys
import time

sys.path.insert(0, "C:/Users/Bndit/Projects/file-portal/windows-converter")
import fidelity_audit as fa  # noqa: E402
import analyst  # noqa: E402

OUT = "C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/3567c0ef-5c0b-42cf-8101-4bb783f0ee67/scratchpad/verify-tickets/verifier/v_lane_a_result.json"
LIB = "C:/Users/Bndit/ml/library/.chunk-work/14c66834bdfeaa2e"
HELD_DIR = "C:/Users/Bndit/ml/library/held/14c66834bdfeaa2e"
JOURNAL = "C:/Users/Bndit/ml/library/.analyst-work/d58db211c41b0e17/chunks.jsonl"

R = {}
t0 = time.perf_counter()
slices = sorted(glob.glob(LIB + "/slice-*/slice.md"))
parts = [open(p, encoding="utf-8").read() for p in slices]
marker = "\n\n".join(parts)
held_path = glob.glob(HELD_DIR + "/*.md")[0]
held_raw = open(held_path, encoding="utf-8").read()
held_body = held_raw.split("---\n", 2)[2]
manifest = json.load(open(HELD_DIR + "/manifest.json", encoding="utf-8"))
R["inputs"] = {"n_slices": len(slices), "marker_chars": len(marker), "held_chars": len(held_raw),
               "held_body_chars": len(held_body), "WINDOW_WORDS": fa.WINDOW_WORDS,
               "ANALYST_DOC_FAIL": fa.ANALYST_DOC_FAIL, "ANALYST_RUN_WORDS": fa.ANALYST_RUN_WORDS}

# --- 1. mirror: the real audit_analyst on (marker reference, held body) as at ship time
res = fa.audit_analyst(marker, held_body)
R["mirror_body"] = {"doc_survival": res["doc_survival"], "runs_total": res["runs_total"],
                    "max_run_words": max(r["words"] for r in res["runs"]),
                    "manifest_doc_survival": manifest["fidelity"]["analyst"]["doc_survival"],
                    "manifest_runs_total": manifest["fidelity"]["analyst"]["runs_total"]}
print("mirror(body):", R["mirror_body"], f"{time.perf_counter()-t0:.0f}s", flush=True)

# --- 2. own window pass (must equal the mirror) + baseline failed list
ref0 = fa.prepare_output(marker)
out0 = fa.prepare_output(held_body)
cjk = fa.is_cjk(ref0[:4000])
win0 = fa.make_windows(ref0, cjk)
fail0 = [w not in out0 for w in win0]
R["baseline"] = {"windows": len(win0), "failed": sum(fail0), "cjk": cjk,
                 "doc_survival": round((len(win0) - sum(fail0)) / len(win0), 4)}
print("baseline:", R["baseline"], f"{time.perf_counter()-t0:.0f}s", flush=True)


# --- 3. independent normalisation ladder (own regexes, deliberately not the builder's)
def unescape(t):
    # drop a backslash that precedes any non-alphanumeric, non-space character
    return re.sub(r"\\(?=[^A-Za-z0-9\s])", "", t)


def punct_free(t):
    # after prepare_output: keep letters/digits (unicode \w minus underscore), collapse the rest
    t = re.sub(r"[^\w\s]+|_", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def rung(ref, out, spacefree):
    wins = fa.make_windows(ref, False)
    if spacefree:
        o = out.replace(" ", "")
        f = [w.replace(" ", "") not in o for w in wins]
    else:
        f = [w not in out for w in wins]
    runs = fa._merge_runs(wins, f, page=None)
    return {"windows": len(wins), "failed": sum(f), "doc_survival": round((len(wins) - sum(f)) / len(wins), 4),
            "runs": len(runs), "max_run_words": max((r["words"] for r in runs), default=0)}, wins, f


ref1 = fa.prepare_output(unescape(marker))
out1 = fa.prepare_output(unescape(held_body))
L = {}
L["1_unescape"], _, _ = rung(ref1, out1, False)
ref2, out2 = punct_free(ref1), punct_free(out1)
L["2_unescape+punct"], _, _ = rung(ref2, out2, False)
L["3_unescape+punct+space"], win3, fail3 = rung(ref2, out2, True)
L["2b_unescape+space (builder's final rung shape)"], win2b, fail2b = rung(ref1, out1, True)
R["ladder_own"] = L
print("ladder:", json.dumps(L, indent=1), f"{time.perf_counter()-t0:.0f}s", flush=True)

# --- 4. chunking with the analyst's own fence/_chunks + attribution of still-failing windows
fenced, embeds = analyst.fence(marker)
chunks = analyst._chunks(fenced)
low = fenced.lower()
starts = [0]
for c in chunks[:-1]:
    starts.append(starts[-1] + len(c))
R["chunks"] = {"n": len(chunks), "embeds": len(embeds),
               "manifest_passed+rejected": manifest["analyst"]["chunks_passed"] + manifest["analyst"]["chunks_rejected"]}


def attribute(wins, fails, nwords=6):
    per = {}
    located = unlocated = 0
    idxs = []
    for w, f in zip(wins, fails):
        if not f:
            continue
        key = " ".join(w.split()[:nwords])
        k = low.find(key)
        if k < 0:
            unlocated += 1
            continue
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
    return {"located": located, "unlocated": unlocated,
            "located_rate": round(located / max(1, located + unlocated), 3),
            "chunks_with_loss": len(per), "chunks_for_80pct": n80,
            "front_matter_1_15": sum(v for k, v in per.items() if k <= 15),
            "median_chunk": statistics.median(idxs) if idxs else None,
            "top10": sorted(per.items(), key=lambda kv: -kv[1])[:10]}, per


R["attrib_baseline"], per0 = attribute(win0, fail0)
R["attrib_final_rung3"], per3 = attribute(win3, fail3)
R["attrib_final_rung2b"], per2b = attribute(win2b, fail2b)
print("attrib baseline:", R["attrib_baseline"], flush=True)
print("attrib rung3:", R["attrib_final_rung3"], flush=True)
print("attrib rung2b:", R["attrib_final_rung2b"], f"{time.perf_counter()-t0:.0f}s", flush=True)
# front matter identity check
R["chunk1_head"] = re.sub(r"\s+", " ", chunks[0][:160])
R["chunk15_head"] = re.sub(r"\s+", " ", chunks[14][:120])

# --- 5. chunk 23 / 78: deletion or rewording? paragraph-level containment in the SHIPPED body
out_full = out0


def para_test(i):
    ch = chunks[i - 1]
    paras = [p for p in re.split(r"\n\s*\n", ch) if len(p.split()) >= 8]
    present = absent = 0
    absent_words = 0
    absent_heads = []
    for p in paras:
        pp = fa.prepare_output(p)
        if not pp:
            continue
        if pp in out_full:
            present += 1
        else:
            # try the first and last 12-word windows separately
            wins = fa.make_windows(pp, False)
            hit = sum(1 for w in wins if w in out_full)
            if hit == len(wins) and wins:
                present += 1
            else:
                absent += 1
                absent_words += len(pp.split())
                absent_heads.append(pp[:70])
    return {"chunk_chars": len(ch), "paras_ge8w": len(paras), "paras_present": present,
            "paras_absent": absent, "absent_words": absent_words, "absent_heads": absent_heads[:4]}


R["chunk23"] = para_test(23)
R["chunk78"] = para_test(78)
print("chunk23:", R["chunk23"], flush=True)
print("chunk78:", R["chunk78"], flush=True)

# --- 6. the journal: validated records, rejected chunks, their located loss
jr = analyst._load_journal(__import__("pathlib").Path(JOURNAL), chunks)
rej = [i for i, r in jr.items() if r.get("status") == "rejected"]
R["journal"] = {"validated": len(jr), "rejected_validated": len(rej),
                "manifest_rejected": manifest["analyst"]["chunks_rejected"],
                "loss_in_rejected_baseline": sum(per0.get(i, 0) for i in rej),
                "loss_in_rejected_rung3": sum(per3.get(i, 0) for i in rej),
                "loss_in_rejected_rung2b": sum(per2b.get(i, 0) for i in rej)}
for i in (23, 78):
    r = jr.get(i)
    R["journal"][f"chunk{i}"] = ({"status": r["status"], "out_chars": len(r["text"]), "in_chars": len(chunks[i - 1])}
                                 if r else "no validated record")
print("journal:", R["journal"], flush=True)

# --- 7. front matter mentions
R["mentions"] = {}
for pat in (r"figure \d+\.\d+", r"table \d+\.\d+"):
    R["mentions"][pat] = {"marker": len(re.findall(pat, marker.lower())),
                          "held": len(re.findall(pat, held_body.lower()))}
print("mentions:", R["mentions"], flush=True)

# --- 8. negative + positive controls
pos = next(w for w, f in zip(win0, fail0) if not f and len(w.split()) == 12)
words = pos.split()
words[5] = "xqzplonkotron9999"
poison = " ".join(words)
R["controls"] = {
    "positive_passes_baseline": pos in out0,
    "poison_fails_baseline": poison not in out0,
    "poison_fails_unescape": poison not in out1,
    "poison_fails_punct": punct_free(poison) not in out2,
    "poison_fails_space": poison.replace(" ", "") not in out2.replace(" ", ""),
}
# a window that fails only because of escapes: fails baseline, passes after unescape
esc_example = None
w1 = fa.make_windows(ref1, False)
f1 = [w not in out1 for w in w1]
for w, f in zip(win0, fail0):
    if f and "\\" in w:
        u = fa.prepare_output(unescape(w))
        if u in out1:
            esc_example = {"before": w, "after_unescape": u}
            break
R["controls"]["escape_only_example"] = esc_example
print("controls:", R["controls"], flush=True)
R["wall_s"] = round(time.perf_counter() - t0, 1)
json.dump(R, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("DONE", R["wall_s"], "s")
