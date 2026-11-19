"""One command: run the pipeline N times over every complaint, save raw runs, write the report.

    python scripts/run_eval.py --tag v1 --prompt v1 --runs 3            # call the model + report
    python scripts/run_eval.py --tag v1 --report-only                   # rebuild report from saved runs
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

from triage.duplicates import group_duplicates  # noqa: E402
from triage.evaluate import build_report, load_items  # noqa: E402
from triage.llm import make_client  # noqa: E402
from triage.pipeline import load_prompt, process_item  # noqa: E402


def load_rules(name: str | None):
    if not name:
        return None
    return importlib.import_module(f"triage.rules_{name}").rules


def run_once(items: list[dict], client, prompt: str, rules, workers: int) -> list[dict]:
    with ThreadPoolExecutor(max_workers=workers) as ex:
        recs = list(ex.map(lambda it: process_item(it, client, prompt, rules=rules), items))
    groups = group_duplicates({r["id"]: r["text"] for r in recs if r["text"]})
    for r in recs:
        r["duplicate_group"] = groups.get(r["id"])
    return recs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True, help="name for runs/<tag>/ and reports/eval_<tag>.md")
    ap.add_argument("--prompt", default="v1")
    ap.add_argument("--rules", default=None, help="optional deterministic rule set, e.g. v2 -> triage/rules_v2.py")
    ap.add_argument("--backend", default="gemini", choices=["gemini", "azure"])
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--report-only", action="store_true")
    ap.add_argument("--ids", default=None, help="comma-separated ids to run (default: all)")
    ap.add_argument("--merge", action="store_true", help="merge these ids into existing runs/<tag>/run*.jsonl")
    ap.add_argument("--skip-scans", action="store_true", help="leave out mail_scan items (e.g. Tesseract not installed)")
    args = ap.parse_args()

    load_dotenv(ROOT / ".env")
    run_dir = ROOT / "runs" / args.tag
    meta_path = run_dir / "meta.json"

    if not args.report_only:
        run_dir.mkdir(parents=True, exist_ok=True)
        client = make_client(args.backend)
        prompt = load_prompt(args.prompt)
        rules = load_rules(args.rules)
        items = list(load_items().values())
        if args.skip_scans:
            items = [it for it in items if it["channel"] != "mail_scan"]
        if args.ids:
            wanted = set(args.ids.split(","))
            items = [it for it in items if it["id"] in wanted]
        t0 = time.time()
        for k in range(1, args.runs + 1):
            recs = run_once(items, client, prompt, rules, args.workers)
            path = run_dir / f"run{k}.jsonl"
            if args.merge and path.exists():
                merged = {r["id"]: r for r in map(json.loads, path.read_text().splitlines())}
                merged.update({r["id"]: r for r in recs})
                recs = [merged[i] for i in sorted(merged)]
                groups = group_duplicates({r["id"]: r["text"] for r in recs if r["text"]})
                for r in recs:
                    r["duplicate_group"] = groups.get(r["id"])
            (run_dir / f"run{k}.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recs) + "\n")
            print(f"run {k}/{args.runs} done ({time.time() - t0:.0f}s)")
        old_meta = json.loads(meta_path.read_text()) if (args.merge and meta_path.exists()) else None
        meta = {"prompt": f"prompts/{args.prompt}.md", "rules": f"triage/rules_{args.rules}.py" if args.rules else "none",
                "model": client.name, "temperature": 0, "runs": args.runs, "items": len(items),
                "scans": "skipped (OCR not run)" if args.skip_scans else "included",
                "ran_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "wall_seconds": round(time.time() - t0)}
        if old_meta:
            old_meta.setdefault("merged_passes", []).append(
                {"ids": args.ids, "model": client.name, "ran_at": meta["ran_at"], "note": "added in a later pass"})
            old_meta["items"] = len(merged)
            if any(it["channel"] == "mail_scan" for it in items):
                old_meta["scans"] = "included (OCR pass added after Tesseract was installed)"
            meta = old_meta
        meta_path.write_text(json.dumps(meta, indent=2))

    meta = json.loads(meta_path.read_text())
    runs = [dict((r["id"], r) for r in map(json.loads, p.read_text().splitlines()))
            for p in sorted(run_dir.glob("run*.jsonl"))]
    report, data = build_report(args.tag, runs, meta, ROOT / "reports" / "analysis" / f"{args.tag}_fn_causes.csv")
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / f"eval_{args.tag}.md").write_text(report)
    (ROOT / "reports" / f"eval_{args.tag}.json").write_text(json.dumps(data, indent=2, default=list))
    print(f"wrote reports/eval_{args.tag}.md")


if __name__ == "__main__":
    main()
