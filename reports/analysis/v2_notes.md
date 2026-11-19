# v2 analysis

v2 = `prompts/v2.md` (3 prompt edits designed on DEV errors only; see `v1_dev_error_notes.md`).
Same model, temperature 0, 3 runs, all 54 items including scans. Full numbers: `reports/eval_v2.md`;
side by side: `reports/compare_v1_v2.md`.

## What changed on DEV (where the edits were designed)

- The one v1 false negative (C020, vague) is now High in all 3 runs. C042 (vague, gold High),
  which went High → Low → Low in v1, is High in all 3 runs.
- The 3 campaign letters over-called High (C010, C011, C013) are now Medium.
- C033 (RCMP, out of scope) now goes to `out_of_scope_confirm` instead of `human_review`.
- Same priority in all 3 runs: 26/30 → 29/30. Review rate 18/30 → 14/30 (gold: 13/30).
- These are expected — the edits were written to fix exactly these items — so DEV gains are not
  evidence that v2 is better in general.

## What changed on TEST (held out; not used to design anything)

Only three items changed:

| id | v1 → v2 | independent evidence? |
|---|---|---|
| C009 | High → Medium (correct) | **No** — a copy of the dev campaign letters the edit was designed on (split leak, see BUILD_LOG D15) |
| C012 | High → Medium (correct) | **No** — same campaign |
| C030 | human_review → standard_queue (**worse**) | Yes |

So the headline gains on test (priority accuracy 22/24 → 24/24, High precision 8/10 → 8/8) come
entirely from the two leaked campaign letters. **Excluding them, v2 shows no independent
improvement on the held-out set, and one regression.**

## The regression: C030

"I've had a lot of problems with the police in this town for years… I just want it on the
record that I complained." Gold: Low, must_review = Y (too vague to judge). v1 sent it to human
review in all 3 runs; v2 marks it Low with `needs_review = false` in all 3 runs, so it lands in
the standard queue.

Likely cause: v2 tightened when `needs_review` should be set (out of scope alone is no longer a
reason) and made the vague-complaint rule about *possible harm*. C030 describes no harm, so the
model treated it as an ordinary Low complaint instead of "too vague to judge". The edit fixed
over-review on dev and introduced an under-review on test.

Severity: low in practice — the item is still in a queue a person reads, and its gold priority is
Low — but it is exactly the kind of side effect a held-out set exists to catch.

Not fixed here: changing the prompt again because of a test item would turn the test set into a
second dev set. A v3 would need new held-out data.

## Unchanged

- High recall: test 8/8 in both versions; dev 10/11 → 11/11.
- Prompt injection: 4/4 flagged, 0 goals achieved, in both versions.
- Remaining instability on dev: C008 queue (review flag 1 of 3 runs), C015 (French) Medium,
  Medium, Low.
- Remaining dev errors: C014 (mall security guard, gold Medium) and C052 (scan, never collected
  evidence, gold Medium) predicted Low in both versions.
- Provenance check dropped 1 sentence per split in v2 (C049 quote too short; C008 the model
  stitched two separate passages together with "..." into one quote).
