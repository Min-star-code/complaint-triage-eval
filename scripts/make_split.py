"""Fix the dev / test split once, BEFORE any labels or model runs exist.

Stratified by design_scenario so both halves contain high-risk, injection, scans, French, etc.
dev  = used to read errors and change the prompt/rules.
test = held out; only used to confirm a change, never to design it.
"""
from __future__ import annotations

import csv
import json
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261118


def main() -> None:
    items = json.loads((ROOT / "data" / "complaints.json").read_text())["complaints"]
    groups: dict[str, list[str]] = defaultdict(list)
    for c in items:
        # merge tiny groups so each split still gets a mix
        g = c["design_scenario"].replace("_scan", "").replace("subtle_", "")
        groups[g].append(c["id"])
    rng = random.Random(SEED)
    split = {}
    for g, ids in sorted(groups.items()):
        ids = sorted(ids)
        rng.shuffle(ids)
        n_test = len(ids) // 2  # floor -> dev gets the odd one
        for j, cid in enumerate(ids):
            split[cid] = "test" if j < n_test else "dev"
    out = ROOT / "data" / "split.csv"
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "split"])
        for cid in sorted(split):
            w.writerow([cid, split[cid]])
    n_test = sum(v == "test" for v in split.values())
    print(f"wrote {out.relative_to(ROOT)}: dev={len(split) - n_test} test={n_test}")


if __name__ == "__main__":
    main()
