"""SYM-073 cause check: audit_convert on the rebuilt PRE-analyst Marker body vs on the held POST-analyst md.
If the Marker body reproduces the manifest's 0.9334 / 241 / 531 and the held md gives 0.9271 / 257 / 570, the
two manifest-vs-fresh numbers were audits of two different texts. Read-only."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "C:/Users/Bndit/Projects/file-portal/windows-converter")
import fidelity_audit as fa  # noqa: E402

SP = Path(__file__).parent
HELD = Path("C:/Users/Bndit/ml/library/held/14c66834bdfeaa2e")
man = json.loads((HELD / "manifest.json").read_text(encoding="utf-8"))
pdf = Path("C:/Users/Bndit/ml/library/drop/done") / man["source"]
marker = "\n\n".join(p.read_text(encoding="utf-8") for p in sorted((SP / "univ4e-marker").glob("slice-*.md")))
held = next(HELD.glob("*.md")).read_text(encoding="utf-8")
c = man["fidelity"]["convert"]
print("manifest convert block: doc_survival", c["doc_survival"], "pages_flagged", len(c["pages_flagged"]), "runs_total", c.get("runs_total"))
for label, text in (("PRE-analyst Marker body (slice cache)", marker), ("POST-analyst held md", held)):
    t = time.time()
    b = fa.audit_convert(pdf, text, man["lane"], asset_count=None)
    print(f"{label:40s} doc_survival {b['doc_survival']}  pages_flagged {len(b['pages_flagged'])}  runs_total {b.get('runs_total')}  "
          f"degeneration {b['tripwires']['degeneration']}  ({time.time()-t:.0f}s)")
