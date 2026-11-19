"""Build a static results dashboard: reports/dashboard.html (no server, no dependencies).

Reads reports/eval_<tag>.json and runs/<tag>/run1.jsonl for each tag given.
    python scripts/make_dashboard.py v1 v2
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from triage.evaluate import load_labels, load_split, pred_priority  # noqa: E402

COLORS = {"High": "#c62828", "Medium": "#ef6c00", "Low": "#2e7d32"}


def pct(pair) -> str:
    n, d = pair
    return f"{n}/{d}" + (f" <small>({100 * n / d:.0f}%)</small>" if d else "")


def badge(p: str) -> str:
    c = COLORS.get(p, "#555")
    return f'<span class="b" style="background:{c}">{html.escape(p)}</span>'


def main(tags: list[str]) -> None:
    labels, split = load_labels(), load_split()
    evals = {t: json.loads((ROOT / "reports" / f"eval_{t}.json").read_text()) for t in tags}
    runs = {t: {r["id"]: r for r in map(json.loads, (ROOT / "runs" / t / "run1.jsonl").read_text().splitlines())}
            for t in tags}

    rows = [("High recall (model)", "high_recall"), ("High → human review", "high_to_human"),
            ("High precision", "high_precision"), ("Priority accuracy", "priority_acc"),
            ("In-scope accuracy", "in_scope_acc"), ("Theme accuracy", "theme_acc"),
            ("Review rate", "review_rate")]
    head = "".join(f"<th>{t} test</th><th>{t} dev</th>" for t in tags)
    metric_rows = ""
    for name, key in rows:
        cells = "".join(f"<td>{pct(evals[t]['splits'][s][key])}</td>" for t in tags for s in ("test", "dev"))
        metric_rows += f"<tr><th>{name}</th>{cells}</tr>"
    cells = "".join(f"<td>{pct(evals[t]['splits'][s]['consistency']['priority'])}</td>" for t in tags for s in ("test", "dev"))
    metric_rows += f"<tr><th>Same priority in all runs</th>{cells}</tr>"

    last = tags[-1]
    item_rows = ""
    for cid in sorted(labels):
        r = runs[last].get(cid)
        if not r:
            continue
        o = r.get("output") or {}
        preds = "".join(f"<td>{badge(pred_priority(runs[t][cid]))}</td>" if cid in runs[t] else "<td>-</td>" for t in tags)
        summ = "".join(f'<li>{html.escape(s["sentence"])}<br><q>{html.escape(s["source_quote"])}</q></li>'
                       for s in o.get("summary", []))
        dropped = "".join(f'<li class="drop">dropped ({html.escape(d["reason"])}): {html.escape(d["sentence"])}</li>'
                          for d in r["grounding_dropped"])
        miss = ' class="miss"' if labels[cid]["priority"] == "High" and pred_priority(r) != "High" else ""
        item_rows += (f"<tr{miss}><td>{cid}<br><small>{split[cid]} · {r['channel']}</small></td>"
                      f"<td>{badge(labels[cid]['priority'])}</td>{preds}"
                      f"<td>{html.escape(r['route']['queue'])}<br><small>{html.escape(', '.join(r['route']['reasons']))}</small></td>"
                      f"<td><b>{html.escape(o.get('title', r['ingest'].get('note', '')))}</b><ul>{summ}{dropped}</ul></td></tr>")

    pred_heads = "".join(f"<th>{t}</th>" for t in tags)
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Triage Eval Results</title>
<style>
:root{{--bg:#fafafa;--fg:#1d1d1f;--card:#fff;--line:#ddd;--muted:#666}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151515;--fg:#eee;--card:#1f1f1f;--line:#333;--muted:#aaa}}}}
body{{font-family:-apple-system,Helvetica,sans-serif;background:var(--bg);color:var(--fg);max-width:1200px;margin:0 auto;padding:16px}}
table{{border-collapse:collapse;width:100%;background:var(--card);margin:12px 0}}
th,td{{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top;font-size:14px}}
small,q{{color:var(--muted)}} .b{{color:#fff;border-radius:4px;padding:1px 6px;font-size:12px}}
tr.miss{{outline:2px solid #c62828}} li{{margin:4px 0}} .drop{{color:#c62828}} .wrap{{overflow-x:auto}}
</style></head><body>
<h1>Complaint triage — evaluation results</h1>
<p>Synthetic complaints · labels per LABELING_GUIDE.md (first pass by Claude, reviewed by the owner) ·
model {html.escape(evals[last]['meta']['model'])} · every number computed from saved runs.</p>
<div class="wrap"><table><tr><th>metric</th>{head}</tr>{metric_rows}</table></div>
<h2>Every complaint ({last}, run 1)</h2>
<p>Red outline = gold High that the model did not call High. Summaries show each sentence with its source quote.</p>
<div class="wrap"><table><tr><th>id</th><th>gold</th>{pred_heads}<th>queue · reasons</th><th>title · grounded summary</th></tr>{item_rows}</table></div>
</body></html>"""
    out = ROOT / "reports" / "dashboard.html"
    out.write_text(page)
    print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main(sys.argv[1:] or ["v1"])
