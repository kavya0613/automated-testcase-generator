"""Write the synthetic training set to data/training_stories.csv"""
import _path  # noqa: F401
import csv

from tcgen.config import ROOT
from tcgen.ml.dataset import generate_dataset

rows = generate_dataset()
out = ROOT / "data" / "training_stories.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["text", "category", "quality"])
    w.writeheader()
    w.writerows(rows)
print(f"Wrote {len(rows)} rows to {out}")
