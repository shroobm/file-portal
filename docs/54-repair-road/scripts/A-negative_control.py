"""Negative control: plant a window whose CONTENT the model certainly changed (word swapped
for an antonym/nonsense token that cannot appear anywhere else in a 3.4M-char finance text)
and confirm it fails containment at every ladder stage (baseline / unescape / punct-free /
space-free). If it ever PASSES, the ladder is leaking (a methodology bug), which would
undermine claims (1)-(3)."""
import glob
import re
import sys

sys.path.insert(0, r"C:/Users/Bndit/Projects/file-portal/windows-converter")
import fidelity_audit as fa  # noqa: E402

SLICE_DIR = r"C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/3567c0ef-5c0b-42cf-8101-4bb783f0ee67/scratchpad/univ4e-marker"
ANALYST_MD = r"C:/Users/Bndit/ml/library/held/14c66834bdfeaa2e/Investment Valuation, University Edition _ Tools and -- Aswath Damodaran -- Four.md"


def unescape(t):
    return re.sub(r"\\(.)", r"\1", t)


def punct_free(t):
    t = re.sub(r"[^\w\s]", "", t, flags=re.UNICODE)
    return re.sub(r"\s+", " ", t).strip()


files = sorted(glob.glob(SLICE_DIR + "/slice-*.md"))
marker_ref = "\n\n".join(open(f, encoding="utf-8").read() for f in files)
analyst_md = open(ANALYST_MD, encoding="utf-8").read()

ref0 = fa.prepare_output(marker_ref)
out0 = fa.prepare_output(analyst_md)
words = ref0.split()
# take a genuine 12-word window, then poison one interior word with a token that cannot exist
# anywhere in a Damodaran valuation textbook
i0 = 500000 % (len(words) - 12)
genuine = words[i0:i0 + 12]
poisoned = list(genuine)
poisoned[6] = "xqzplonkotron9999"  # certainly not a real word in this book
planted = " ".join(poisoned)
print("planted window:", planted)

stages = {
    "0_baseline": (ref0, out0),
}
r1, o1 = unescape(ref0), unescape(out0)
stages["1_unescape"] = (r1, o1)
r2, o2 = punct_free(r1), punct_free(o1)
stages["2_punct_free"] = (r2, o2)

for name, (_, out_text) in stages.items():
    hit = planted in out_text
    print(f"{name}: planted window found in output? {hit}  (expected False)")

# space-free stage: strip spaces from both window and output
out_ns = o2.replace(" ", "")
hit = planted.replace(" ", "") in out_ns
print(f"3_space_free: planted window found (space-free)? {hit}  (expected False)")

# sanity: the GENUINE (unpoisoned) window at the same location -- does it survive? (tells us
# whether this location was itself a real loss location or a normal passing one)
genuine_w = " ".join(genuine)
print("\ngenuine (unpoisoned) window:", genuine_w)
print("genuine window found in baseline output?", genuine_w in out0)
