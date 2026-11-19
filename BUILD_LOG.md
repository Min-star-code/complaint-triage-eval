# Build log

Design decisions and bugs, in the order they happened. Written for explaining the project in
an interview: *what I decided, why, and what went wrong.*

Roles: the project owner set the requirements, wrote the labeling rules with Claude Code,
labeled every complaint by hand, and reviewed the results. The code was written with
Claude Code.

---

## 2026-11-18 — Data, labeling, pipeline skeleton

### D1. Synthetic data, written to cover failure modes, not to be "realistic on average"
54 complaints (50 typed, 4 mailed scans). Each was written to test something specific:
clear high-risk cases, ordinary courtesy complaints, multi-issue complaints where the serious
issue is buried at the end (C022, C046), a 5-letter form campaign with small variations
(C009–C013, where C012 adds a baton strike), out-of-scope bodies (bylaw, mall security, RCMP,
courts, tribunals, driver testing), 2 French complaints, 4 prompt-injection attempts, vague
complaints, and "understated" high-risk cases (C035: "This is probably nothing…").
Why: a random sample of real complaints would be mostly easy; the evaluation would say
"95% accurate" and hide the cases that matter.
`design_scenario` records the intent of each item but is **not** a label.

### D2. The split was fixed before any labels or model runs
`scripts/make_split.py` stratifies by scenario (seed 20261118): 30 dev / 24 test.
Why: if the split were chosen after seeing results it could be (even unconsciously) tilted.
Rule for the whole project: read errors and change prompts on **dev** only; **test** only
confirms.

### D3. Labeling tool built for a human labeler (plan changed — see D3b)
A small stdlib labeling server (`scripts/label_server.py`) shows complaints in a fixed shuffled
order, shows scans as images (never the transcription), never shows the design scenario or any
model output, and autosaves to `data/labels/labels.csv`.
Why: if the model (or the person who wrote the model's prompt) produced the labels, the
evaluation would measure agreement with itself.

### D3b. Change of plan: first-pass labels written by Claude, owner spot-checks
The owner did not have the 40–60 minutes needed to label 54 items, and decided to have Claude
(the coding assistant) label them by the guide. Done before any evaluation run, so the labels
could not be fitted to model output. Honest limits: (1) the labeler also wrote the complaints,
so labels follow the design intent; (2) for the unreadable scan C054 the labeler knew the
content. The evaluated model (Gemini) is a different model. Each row has a `labeler` column;
rows the owner reviews in the labeling page become `owner`. Reports must state this.
Owner review: read the two most borderline items closely and changed one — C012 (campaign
letter that adds a baton strike and burning eyes) from High to **Medium** ("injuries not
serious"); kept C042 (anonymous, vague) as High. Skimmed the other 52 and changed nothing.
Final counts: 19 High, 13 Medium, 22 Low.

### D4. Scans are generated images; OCR must read them
`scripts/make_scans.py` renders 4 letters with rotation, salt noise and blur (C054 is
deliberately degraded to fax quality). The pipeline only gets the image; the transcription is
kept only to measure OCR character error rate.

### D5. Unreadable OCR skips the LLM entirely
If mean word confidence < 70 or fewer than 15 words are found, the item goes straight to
human review. Why: an LLM given garbled text still returns a confident, well-formed summary —
that is worse than no summary.

### D6. Raw text from every provider; validation is ours
Each client returns the model's raw string. The pipeline parses and validates it with pydantic
(`extra="forbid"`, enums for priority and themes). On failure it retries **once**, telling the
model what was wrong; a second failure routes to a human with `schema_invalid`.
Why: SDK "structured output" modes can silently coerce or fail; counting schema failures is part
of the evaluation.

### D7. Provenance check on every summary sentence
Each sentence must carry an exact quote (≥ 3 words) from the complaint; quotes are matched after
normalising case, whitespace and curly quotes. A sentence with a number that does not appear in
the complaint is dropped even if its quote is valid (catches invented details such as "three
ribs" when the text says "two"). Dropped sentences are counted and the item goes to a human.

### D8. Code decides the route, not the model
`routing.py` is deterministic. High priority, a model review flag, a suspected injection, a
dropped summary sentence, unreadable OCR, or a schema failure → `human_review`. Out of scope →
`out_of_scope_confirm` (a person confirms and refers it). **No path lets the model close or
discard a complaint.**

### D9. Near-duplicate grouping in code, never merging
4-word shingles + Jaccard ≥ 0.5, union-find into groups. Duplicates are grouped for the
investigator but never merged or dropped, because one copy in a campaign can add a new fact
(C012 reports a baton strike).

### D10. Prompt injection defence in depth
The complaint is wrapped in `<complaint>` tags and any tags the complainant typed are stripped
(so they cannot "close" the block). The prompt says the text is untrusted data, and the model
reports `injection_suspected`, which routes to a human. The evaluation checks mechanically
whether each injected goal was achieved.

### D11. Two kinds of High recall
"Model said High" and "High item reached human review by any route" are reported separately.
An unreadable scan that is a real High case is a model miss but not a safety miss.

### Bug B1. Schema cleaner deleted the `title` field
Gemini rejected the first request: `schema at top-level requires unspecified property 'title'`.
`provider_schema()` strips JSON-Schema keywords some providers reject (`title`, `maxLength`, …),
but it deleted *every* key named `title` — including the output field called `title` inside
`properties`. Fix: inside a `properties` object, keys are field names and are kept. Regression
test: `test_provider_schema_keeps_field_named_title`.

### Bug B2. `rec.get("output", {})` returned `None`
The metric code used `rec.get("output", {})`; for an unreadable scan the record holds
`"output": None`, and `.get` returns `None` because the key exists. A unit test with an
unreadable item caught it. Fix: `(rec.get("output") or {})`.

## 2026-11-18 — First evaluation run

### Bug B3. One provider error crashed the whole batch
The first v1 run died part-way with `503 UNAVAILABLE` ("model is experiencing high demand")
after the 5 retries were used up. One failed complaint took down the whole batch.
Fix: retries raised to 7 with backoff capped at 60 s, workers lowered from 4 to 2, and any
error left after retries is caught per complaint, recorded as `llm_error` and routed to human
review (`llm_unavailable`). The report counts these separately so an outage is never mistaken
for a model judgement. Test: `test_provider_outage_goes_to_human_without_crashing`.

### D12. Scans skipped in v1 because Tesseract is not installed on this Mac
Rather than treating "OCR not installed" as "unreadable" (which would look like a working
safety net), v1 runs with `--skip-scans` on the 50 typed complaints and the report says OCR
was not evaluated.

### D13. Tesseract installed without admin rights
Homebrew needs an admin password, which the assistant must not enter. Tesseract 5.5.4 was
installed instead with micromamba from conda-forge into the user's home folder
(`~/.local/micromamba/envs/ocr`); the pipeline finds it through `TESSERACT_CMD` in `.env`.
The 4 scans were then run and merged into v1 (`--ids … --merge`; recorded in `meta.json`).

### Bug B4. The OCR metric itself was wrong
C051 showed an 80% character error rate although its OCR text was mostly right. The metric
used `difflib.SequenceMatcher`, whose "autojunk" heuristic ignores frequent characters (spaces)
in strings over 200 characters. Replaced with a Levenshtein distance / reference length:
C051 9.7%, C052 1.7%, C053 5.3%, C054 90.9% (unreadable → human). Lesson: test the metric too.
Regression test: `test_cer_is_edit_distance_over_reference_length`.

### Bug B5. Report crashed on items that were not run
`consistency()` looked up every split id in every run; with scans skipped, `KeyError: 'C051'`.
Fixed by only comparing ids present in all runs.

## v1 findings (details: `reports/eval_v1.md`, `reports/analysis/v1_dev_error_notes.md`)

- Test (24): High recall 8/8, High precision 8/10, priority accuracy 22/24.
  Dev (30): High recall 10/11; the one miss (C020) still reached human review.
- All 4 injection attempts were flagged and none achieved its goal.
- **temperature = 0 is not deterministic.** On dev, 4 of 30 items changed priority across 3
  identical runs; C042 (vague, gold High) went High → Low → Low.
- The model altered a quote ("Carick Falls" for "Carrick Falls"); the provenance check dropped it.

### D14. v2 = prompt-only changes, designed on dev errors
Three edits (vague-complaint rule, force needs a stated injury for High, out of scope is not by
itself a review reason). No code rules added, so any change in the numbers comes from the prompt.

### D15. Lesson: the split leaks across duplicate groups
The split was stratified by scenario, not grouped by near-duplicate cluster, so campaign letters
sit in both dev (C010, C011, C013) and test (C009, C012). A prompt fix designed on the dev letters
carries over to their copies in test, so test gains on those two are not independent evidence.
Should have used a grouped split; not changed afterwards, because re-splitting after seeing
results is worse.

## v2 findings (details: `reports/analysis/v2_notes.md`, `reports/compare_v1_v2.md`)

- DEV: the edits fixed what they targeted (C020 and C042 now High in every run; campaign letters
  Medium; same-priority-across-runs 26/30 → 29/30). Expected, since they were designed on dev.
- TEST: only 3 items changed. C009 and C012 improved, but they are copies of the dev campaign
  letters (D15), so not independent. **C030 regressed**: a vague complaint with no harm described
  went from human review to the standard queue, because v2 narrowed when `needs_review` is set.
- Decision: report the regression, do not patch the prompt against a test item. A v3 needs new
  held-out data.
- The provenance check caught a second kind of altered quote: two separate passages joined with
  "..." into one quote (C008).

### D16. Dashboard and comparison are generated, not hand-written
`scripts/make_dashboard.py` builds a static `reports/dashboard.html` (metrics per version and
every complaint with its grounded summary); `scripts/compare.py` lists every item whose priority
or queue changed between versions and marks better / worse against the labels.
