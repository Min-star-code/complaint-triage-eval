# Complaint Triage Eval

An LLM triage assistant for public complaints to a (fictional) police oversight office, and
an evaluation harness that measures where it fails — above all, whether it misses high-risk
complaints.

> **All data is synthetic.** Every complaint, person, place and police service is invented.
> No real complaint data was used.

## What it does

```
complaint (typed text, or a scanned letter)
  → intake: Tesseract OCR for scans; low OCR confidence → full human review, no LLM
  → LLM structured output (JSON): title, summary with a source quote per sentence,
    key fields, themes, priority (High/Medium/Low), needs_review + reason, injection flag
  → schema validation (pydantic, strict); one retry with the error; then human review
  → provenance check: drop any summary sentence whose quote is not in the complaint,
    or that contains a number the complaint does not
  → routing (deterministic code): human_review / out_of_scope_confirm / standard_queue
    — the model can never close or discard a complaint
  → near-duplicate grouping (form-letter campaigns), never merged
```

Every step is in `triage/`: `ingest.py`, `llm.py`, `schema.py`, `grounding.py`, `routing.py`,
`duplicates.py`, `pipeline.py`, `evaluate.py`.

## Data and labels

- `data/complaints.json` — 54 synthetic complaints written to cover failure modes: clear
  high-risk, ordinary, multi-issue with the serious issue buried, a 5-letter form campaign,
  out-of-scope bodies, 2 in French, 4 prompt-injection attempts, vague and understated cases.
  `design_scenario` records why each was written; it is not a label.
- `data/scans/` — 4 of them rendered as noisy, rotated scanned letters (PDF / PNG / JPG);
  C054 is deliberately near-unreadable.
- `data/split.csv` — 30 dev / 24 test, stratified, fixed **before** labels or model runs.
- `data/labels/labels.csv` — labels following [`LABELING_GUIDE.md`](LABELING_GUIDE.md).
  **Who labeled:** first pass by Claude (the coding assistant) following the guide, before any
  model run; the project owner reviewed the two most borderline items (changed one) and skimmed
  the rest. The `labeler` column records this per row. The labeler also wrote the complaints,
  so labels lean toward each item's design intent — results may be optimistic.

## How to run

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env          # add GEMINI_API_KEY (or Azure OpenAI settings)
.venv/bin/python -m pytest -q # unit tests, fake LLM, no key needed
.venv/bin/python scripts/run_eval.py --tag v1 --prompt v1 --runs 3   # add --skip-scans without Tesseract
.venv/bin/python scripts/label_server.py   # labeling page on http://127.0.0.1:8765
```

Docker (Tesseract included; **not yet built or run** — Docker is not installed on the development Mac):

```bash
docker build -t triage-eval .
docker run --rm --env-file .env triage-eval
```

## Results (Gemini 3.5 Flash Lite, temperature 0, 3 runs per version, 54 items)

Full reports: [`reports/eval_v1.md`](reports/eval_v1.md), [`reports/eval_v2.md`](reports/eval_v2.md),
[`reports/compare_v1_v2.md`](reports/compare_v1_v2.md); error analysis in `reports/analysis/`;
browsable dashboard: `reports/dashboard.html` (`python scripts/make_dashboard.py v1 v2`).

| held-out TEST (24) | v1 | v2 |
|---|---|---|
| High recall (model said High) | 8/8 | 8/8 |
| High reaching human review | 8/8 | 8/8 |
| High precision | 8/10 | 8/8 |
| Priority accuracy | 22/24 | 24/24 |
| Must-review items sent to human | 10/10 | **9/10** |
| Same priority in all 3 runs | 24/24 | 24/24 |

| DEV (30, used to design v2) | v1 | v2 |
|---|---|---|
| High recall (model said High) | 10/11 | 11/11 |
| High reaching human review | 11/11 | 11/11 |
| Same priority in all 3 runs | 26/30 | 29/30 |

What the numbers do and do not show:

- **The test gains are not independent.** The only test items v2 fixed (C009, C012) are copies of
  the dev campaign letters the change was designed on (the split leaked across duplicate groups).
  The only other test change is a **regression**: C030, a vague complaint, no longer goes to human
  review. See [`reports/analysis/v2_notes.md`](reports/analysis/v2_notes.md).
- **temperature 0 is not deterministic**: in v1, 4 of 30 dev items changed priority across 3
  identical runs (C042: High → Low → Low).
- **Prompt injection**: 4/4 attempts flagged, 0 achieved their goal, in both versions.
- **Provenance check** caught real altered quotes (a misspelled name; two passages stitched with "…").
- **OCR**: character error rate 9.7% / 1.7% / 5.3% on the readable scans; the fax-quality scan
  (mean confidence 36) went straight to human review without an LLM call.
- 24 test items is very small; treat every percentage as rough.

## Limitations

- Synthetic data, 54 items: numbers are small and have wide uncertainty.
- Labels were drafted by the same assistant that wrote the data (see above).
- Split stratified by scenario, not grouped by duplicate cluster (leak described above).
- Only one model evaluated (Gemini). The Azure OpenAI backend is implemented but has not been run.
- Tesseract was installed user-level via micromamba (`TESSERACT_CMD` in `.env`); the 4 scans were
  added to v1 in a second pass after installation (recorded in `runs/v1/meta.json`).
