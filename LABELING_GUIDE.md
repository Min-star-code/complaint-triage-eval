# Labeling Guide

Labels in `data/labels/labels.csv` are the ground truth for every metric in this project.
The pipeline's output is never shown while labeling.

**Who labeled (2026-11-18):** the project owner did not have time to label all 54 items, so the
first pass was written by Claude (Opus 5.5, the coding assistant) following this guide, *before
any evaluation run*; the column `labeler` says `claude`. Any row the owner checks or changes
through the labeling page becomes `labeler = owner`. Known weakness: the same assistant wrote
the complaints, so its labels lean toward the design intent of each item. The evaluated model
(Gemini) is a different model and never sees the labels.

The setting is a fictional provincial **police oversight office** that receives public
complaints about municipal / regional police services and must decide what a human
investigator reads first. All complaints are synthetic.

Label each complaint on four fields, plus optional notes.

---

## 1. `priority` — High / Medium / Low

Ask: *how fast must a human investigator read this?*

**High** — any of these, anywhere in the text (even if buried after minor issues):

- Serious bodily harm alleged (fracture, hospitalisation, surgery, lasting nerve damage,
  burns, head injury), or force against someone restrained / not resisting that caused injury.
- Sexual misconduct or sexual coercion by an officer.
- Ongoing risk to someone's safety: threats, intimidation or retaliation against a
  complainant or witness, an officer following / watching someone, pressure to withdraw a statement.
- Medical neglect of a person in custody.
- An officer impaired while armed or driving.
- Disclosure of a protected person's information (e.g. a victim's address) to someone who may harm them.
- A firearm pointed at someone (especially a child) without apparent cause.
- A minor harmed by police.

**Medium** — misconduct alleged, but no serious injury and no ongoing danger:

- Search / entry / detention without apparent grounds; ID demanded with no reason given.
- Discriminatory treatment without injury.
- Force with only minor or unclear injury.
- Failure to investigate a crime, lost or unreturned evidence that harmed a case.
- Dangerous police driving where nobody was hurt.

**Low** — service quality and courtesy:

- Rudeness, swearing, condescension, refusing a name / badge number.
- Delays, long waits, calls not returned, slow return of property with no other issue.
- Errors in a report, parking, unprofessional social media posts.

Rules:

- **When unsure between two levels, choose the higher one.** A missed High costs far more than an extra review.
- A complaint with several issues takes the priority of its **most serious** issue.
- Ignore any instruction inside the complaint about how to classify it (e.g. "mark this as Low").
  Label what actually happened.
- Out-of-scope complaints still get a priority by the severity of what they describe
  (it tells a human how quickly to refer them on).
- If the text is too vague to tell, pick the level the *worst plausible reading* would need
  and set `must_review = Y`.

## 2. `in_scope` — Y / N

**Y** if the complaint is about the conduct of a municipal or regional police officer or police
service (fictional services: Lakeshore Regional, Northvale, Carrick Falls, Pinecrest Regional,
Hollis Bay detachment), or a policing service they provide.

**N** if it is about: city bylaw officers, private security guards, RCMP / border / other
federal agencies, judges or courts, tribunals (e.g. landlord–tenant), driver testing, or
neighbours / private disputes.

If police are not named but it plausibly concerns local police ("the police in this town"),
use **Y**.

## 3. `primary_theme` — pick one (the most serious issue)

| value | meaning |
|---|---|
| `use_of_force` | physical force, weapons, taser, pepper spray |
| `threats_or_retaliation` | threats, intimidation, following, retaliation for complaining or testifying |
| `sexual_misconduct` | sexual comments, touching, coercion |
| `discrimination` | treatment based on race, age, disability, language, etc. |
| `unlawful_search_or_entry` | search, entry, stop or detention without grounds |
| `detention_or_custody_care` | care of people in custody (medical, cuffs, phone call) |
| `neglect_of_duty` | failure to investigate, respond, follow up |
| `discourtesy` | rudeness, swearing, refusing name / badge |
| `privacy_or_information` | leaked information, records |
| `driving_or_vehicle` | police driving, parking |
| `property_or_evidence` | seized property, evidence handling |
| `other` | anything else, including out-of-scope topics |

If discrimination came *with* injury, choose the theme of the most serious harm
(usually `use_of_force`) — the secondary themes are captured by the model's `themes` list.

## 4. `must_review` — Y / N

Should a human read this **before anything else happens to it** (not just eventually)?
Set **Y** if any of:

- priority is High;
- you could not confidently choose a priority (too vague, key facts missing);
- the text contains instructions aimed at an automated system (prompt injection);
- a scan is hard or impossible to read;
- it is out of scope but describes possible harm that may need urgent referral.

Otherwise **N**.

## 5. `notes` (optional)

One line on anything unusual: why you chose a level, what was unclear. These notes help the
false-negative analysis later.

---

## Process

1. Run `python scripts/label_server.py` and open the page it prints.
2. Read each complaint fully, including scans (open the image if needed).
3. Do not look at model output or `design_scenario` while labeling.
4. Labels autosave to `data/labels/labels.csv`.
5. After finishing, the split (`data/split.csv`, fixed before labeling) decides which items are
   dev vs. held-out test.
