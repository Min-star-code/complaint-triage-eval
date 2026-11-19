"""Side-by-side comparison of two evaluated versions -> reports/compare_<a>_<b>.md

    python scripts/compare.py v1 v2
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from triage.evaluate import load_labels, load_split, pred_priority  # noqa: E402

METRICS = [("High recall (model)", "high_recall"), ("High reaching human review", "high_to_human"),
           ("High precision", "high_precision"), ("Priority accuracy", "priority_acc"),
           ("In-scope accuracy", "in_scope_acc"), ("Primary theme accuracy", "theme_acc"),
           ("Must-review items sent to human", "must_review_recall"), ("Review rate", "review_rate")]


def fmt(p) -> str:
    n, d = p
    return f"{n}/{d} ({100 * n / d:.1f}%)" if d else "n/a"


def main(a: str, b: str) -> None:
    ea, eb = (json.loads((ROOT / "reports" / f"eval_{t}.json").read_text()) for t in (a, b))
    labels, split = load_labels(), load_split()
    lines = [f"# {a} vs {b}\n", "Computed from `reports/eval_*.json` and `runs/*/run1.jsonl`.\n"]
    for s in ("test", "dev"):
        lines += [f"## {s}\n", f"| metric | {a} | {b} |", "|---|---|---|"]
        for name, key in METRICS:
            lines.append(f"| {name} | {fmt(ea['splits'][s][key])} | {fmt(eb['splits'][s][key])} |")
        for key, name in (("priority", "Same priority in all runs"), ("queue", "Same queue in all runs")):
            lines.append(f"| {name} | {fmt(ea['splits'][s]['consistency'][key])} | {fmt(eb['splits'][s]['consistency'][key])} |")
        lines.append("")

    ra, rb = ({r["id"]: r for r in map(json.loads, (ROOT / "runs" / t / "run1.jsonl").read_text().splitlines())} for t in (a, b))
    lines += ["## Items whose priority or queue changed (run 1)\n",
              f"| id | split | gold priority | gold must_review | {a} | {b} | better / worse |", "|---|---|---|---|---|---|---|"]
    for i in sorted(labels):
        pa, pb = pred_priority(ra[i]), pred_priority(rb[i])
        qa, qb = ra[i]["route"]["queue"], rb[i]["route"]["queue"]
        if (pa, qa) == (pb, qb):
            continue
        g, must = labels[i]["priority"], labels[i]["must_review"] == "Y"
        score = lambda p, q: (p == g) + (q == "human_review") * must + (q != "human_review") * (not must)  # noqa: E731
        verdict = {1: "better", -1: "worse", 0: "mixed / same"}[max(-1, min(1, score(pb, qb) - score(pa, qa)))]
        lines.append(f"| {i} | {split[i]} | {g} | {labels[i]['must_review']} | {pa} · {qa} | {pb} · {qb} | {verdict} |")
    out = ROOT / "reports" / f"compare_{a}_{b}.md"
    out.write_text("\n".join(lines) + "\n")
    print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main(*sys.argv[1:3])
