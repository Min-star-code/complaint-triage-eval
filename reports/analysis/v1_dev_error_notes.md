# v1 error analysis (DEV split only)

Read every dev error in `runs/v1/`. The test split was not used to design any change.

## False negatives (gold High, model not High)

| id | cause category | what happened |
|---|---|---|
| C020 | vague wording + rule gap | No facts given. Guide rule "use the worst plausible reading" is missing from prompt v1. Medium in run 1, High in runs 2–3. Still reached human review through `needs_review`. |

Related instability (not a run-1 false negative, but the same cause): **C042** (anonymous, vague,
gold High) was High in run 1 and **Low** in runs 2 and 3. It reached human review in all runs
only because the model also set `needs_review`. If that flag had been missed, a possible serious
allegation would have sat in the standard queue.

Categories considered: incomplete information, vague wording, OCR error, rule gap, injection.
No dev false negative came from OCR (C053, the readable high-risk scan, was High) or from
injection (C016, C017 both resisted).

## False positives (model High, gold Medium)

C010, C011, C013 — form-campaign letters: pepper spray on seated protesters, **no injury stated**.
Prompt v1 says High for "force against a restrained or non-resisting person causing injury", but
the model ignored "causing injury". The guide puts force with minor or unclear injury at Medium.
C011 and C013 also flipped High ↔ Medium across runs.

## Over-review and queue instability

- C008 (Medium, entry + search + slur, no injury): flagged for review in 1 of 3 runs.
- C023, C033, C040 (out of scope, no harm): the model sometimes set `needs_review` for "out of
  scope", which sends them to `human_review` instead of `out_of_scope_confirm`. Not dangerous —
  a person still sees them — but it inflates the review rate and makes routing unstable.

## Grounding

- C022: the model's quote misspelled the service as "Carick Falls"; the source says "Carrick".
  The provenance check dropped that sentence correctly — a real altered quote.

## Changes for v2 (prompt only; no new code rules)

1. Add the guide's vague-complaint rule: judge by the most serious plausible reading; a vague
   complaint that could involve harm to a person, especially in custody, is never Low.
2. Make the force rule explicit: High needs a stated injury (or a weapon pointed / a minor
   harmed); force with no stated injury or minor injury is Medium.
3. Out of scope: set `needs_review` only if it describes possible harm needing urgent referral.

## Known leak between splits

The form-campaign letters were split by scenario, not by duplicate group: C010, C011, C013 are
in dev, C009 and C012 in test. Fix 2 is designed on the dev letters, so any improvement on C009
and C012 in test is **not** independent evidence. The right design is to split by duplicate
group; noted as a lesson, not changed now (changing the split after seeing results would be
worse).
