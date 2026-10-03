"""Run all sample stories and report coverage / relevance against the 80% target."""
import _path  # noqa: F401
import json

from tcgen.config import ROOT
from tcgen.service import run_generation

stories = json.loads((ROOT / "data" / "sample_stories.json").read_text(encoding="utf-8"))
rows = []
print(f"{'#':<3}{'Title':<28}{'Category':<18}{'Cases':>6}{'Cov%':>7}{'Rel%':>7}{'Dup%':>6}")
for s in stories:
    r = run_generation(s["user_story"], persist=False)
    m = r["metrics"]
    rows.append(m)
    print(f"{s['id']:<3}{s['title'][:26]:<28}{r['classification']['category']:<18}"
          f"{m['total']:>6}{m['coverage_percent']:>7}{m['relevance_percent']:>7}{m['duplicate_percent']:>6}")
avg = lambda k: sum(m[k] for m in rows) / len(rows)
print(f"\nAverage coverage={avg('coverage_percent'):.1f}%  relevance={avg('relevance_percent'):.1f}%  "
      f"(target: 80%+)  LLM: {r['llm_status']}")
