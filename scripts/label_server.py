"""Tiny local labeling tool (stdlib only).

    python scripts/label_server.py        # then open http://127.0.0.1:8765

Shows every complaint (text, or the scanned image for mail scans) in a fixed shuffled
order, never shows design_scenario or any model output, and autosaves each label to
data/labels/labels.csv.
"""
from __future__ import annotations

import csv
import html
import json
import random
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / "data" / "labels" / "labels.csv"
SCANS = ROOT / "data" / "scans"
FIELDS = ["id", "priority", "in_scope", "primary_theme", "must_review", "notes", "labeler", "labeled_at"]
THEMES = [
    "use_of_force", "threats_or_retaliation", "sexual_misconduct", "discrimination",
    "unlawful_search_or_entry", "detention_or_custody_care", "neglect_of_duty", "discourtesy",
    "privacy_or_information", "driving_or_vehicle", "property_or_evidence", "other",
]


def load_items() -> list[dict]:
    items = json.loads((ROOT / "data" / "complaints.json").read_text())["complaints"]
    order = sorted(items, key=lambda c: c["id"])
    random.Random(7).shuffle(order)
    return order


def load_labels() -> dict[str, dict]:
    if not LABELS.exists():
        return {}
    with LABELS.open() as f:
        return {r["id"]: r for r in csv.DictReader(f)}


def save_label(row: dict) -> None:
    labels = load_labels()
    row = {k: (row.get(k) or "").strip() for k in FIELDS}
    row["labeler"] = "owner"  # anything saved through this page is a human edit
    row["labeled_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    labels[row["id"]] = row
    LABELS.parent.mkdir(parents=True, exist_ok=True)
    with LABELS.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for cid in sorted(labels):
            w.writerow(labels[cid])


def scan_file(cid: str) -> Path | None:
    hits = sorted(SCANS.glob(f"{cid}.*"))
    return hits[0] if hits else None


def radio(name: str, cid: str, values: list[str], current: str) -> str:
    return " ".join(
        f'<label><input type="radio" name="{name}-{cid}" value="{v}"'
        f'{" checked" if v == current else ""}> {v}</label>'
        for v in values
    )


def render_page() -> str:
    labels = load_labels()
    cards = []
    for n, c in enumerate(load_items(), 1):
        cid = c["id"]
        lab = labels.get(cid, {})
        scan = scan_file(cid) if c["channel"] == "mail_scan" else None
        if scan is not None:
            src = f"/scan/{scan.name}"
            body = (f'<iframe src="{src}" class="scan"></iframe>' if scan.suffix == ".pdf"
                    else f'<img src="{src}" class="scan">')
            body += f'<div><a href="{src}" target="_blank">open scan in new tab</a></div>'
        else:
            body = f'<p class="txt">{html.escape(c["text"])}</p>'
        theme_opts = "".join(
            f'<option{" selected" if t == lab.get("primary_theme") else ""}>{t}</option>' for t in THEMES
        )
        cards.append(f"""
<section class="card{' done' if lab else ''}" id="card-{cid}" data-id="{cid}">
  <h3>#{n} · {cid} <small>({html.escape(c['channel'])})</small> <span class="ok">{'✓ saved' if lab else ''}</span></h3>
  {body}
  <div class="row"><b>priority</b> {radio('priority', cid, ['High', 'Medium', 'Low'], lab.get('priority', ''))}</div>
  <div class="row"><b>in_scope</b> {radio('in_scope', cid, ['Y', 'N'], lab.get('in_scope', ''))}</div>
  <div class="row"><b>primary_theme</b> <select name="primary_theme-{cid}"><option value=""></option>{theme_opts}</select></div>
  <div class="row"><b>must_review</b> {radio('must_review', cid, ['Y', 'N'], lab.get('must_review', ''))}</div>
  <div class="row"><b>notes</b> <input type="text" size="80" name="notes-{cid}" value="{html.escape(lab.get('notes', ''))}"></div>
  <button onclick="save('{cid}')">Save {cid}</button>
</section>""")
    total = len(cards)
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Complaint labeling</title>
<style>
body{{font-family:-apple-system,Helvetica,sans-serif;max-width:900px;margin:20px auto;padding:0 16px;background:#fafafa;color:#222}}
.card{{background:#fff;border:1px solid #ddd;border-radius:8px;padding:14px 18px;margin:18px 0}}
.card.done{{border-left:6px solid #2e7d32}} .ok{{color:#2e7d32;font-size:14px}}
.txt{{font-size:16px;line-height:1.5;white-space:pre-wrap}} .row{{margin:8px 0}} label{{margin-right:14px}}
.scan{{width:100%;height:700px;border:1px solid #ccc}} img.scan{{height:auto}}
header{{position:sticky;top:0;background:#fafafa;padding:8px 0;border-bottom:1px solid #ddd}}
button{{padding:6px 14px}}
</style></head><body>
<header><b>Complaint labeling</b> — follow LABELING_GUIDE.md · <span id="count">{len(labels)}</span>/{total} saved · labels go to data/labels/labels.csv</header>
{''.join(cards)}
<script>
function val(name){{const el=document.querySelector(`[name="${{name}}"]:checked`)||document.querySelector(`select[name="${{name}}"],input[type=text][name="${{name}}"]`);return el?el.value:"";}}
async function save(id){{
  const row={{id,priority:val('priority-'+id),in_scope:val('in_scope-'+id),primary_theme:val('primary_theme-'+id),must_review:val('must_review-'+id),notes:val('notes-'+id)}};
  for(const k of ['priority','in_scope','primary_theme','must_review']) if(!row[k]){{alert(id+': please fill '+k);return;}}
  const r=await fetch('/save',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(row)}});
  const j=await r.json(); const card=document.getElementById('card-'+id);
  card.classList.add('done'); card.querySelector('.ok').textContent='✓ saved'; document.getElementById('count').textContent=j.count;
  const next=card.nextElementSibling; if(next) next.scrollIntoView({{behavior:'smooth'}});
}}
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            self._send(200, render_page().encode(), "text/html; charset=utf-8")
        elif self.path.startswith("/scan/"):
            name = Path(self.path[len("/scan/"):]).name  # no path traversal
            f = SCANS / name
            if not f.is_file():
                self._send(404, b"not found", "text/plain")
                return
            ctype = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg"}.get(f.suffix, "application/octet-stream")
            self._send(200, f.read_bytes(), ctype)
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/save":
            self._send(404, b"not found", "text/plain")
            return
        row = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        save_label(row)
        self._send(200, json.dumps({"count": len(load_labels())}).encode(), "application/json")

    def log_message(self, *args) -> None:
        pass


if __name__ == "__main__":
    print("Labeling page: http://127.0.0.1:8765  (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
