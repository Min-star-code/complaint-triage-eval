# v1 vs v2

Computed from `reports/eval_*.json` and `runs/*/run1.jsonl`.

## test

| metric | v1 | v2 |
|---|---|---|
| High recall (model) | 8/8 (100.0%) | 8/8 (100.0%) |
| High reaching human review | 8/8 (100.0%) | 8/8 (100.0%) |
| High precision | 8/10 (80.0%) | 8/8 (100.0%) |
| Priority accuracy | 22/24 (91.7%) | 24/24 (100.0%) |
| In-scope accuracy | 24/24 (100.0%) | 24/24 (100.0%) |
| Primary theme accuracy | 18/24 (75.0%) | 18/24 (75.0%) |
| Must-review items sent to human | 10/10 (100.0%) | 9/10 (90.0%) |
| Review rate | 12/24 (50.0%) | 9/24 (37.5%) |
| Same priority in all runs | 24/24 (100.0%) | 24/24 (100.0%) |
| Same queue in all runs | 23/24 (95.8%) | 24/24 (100.0%) |

## dev

| metric | v1 | v2 |
|---|---|---|
| High recall (model) | 10/11 (90.9%) | 11/11 (100.0%) |
| High reaching human review | 11/11 (100.0%) | 11/11 (100.0%) |
| High precision | 10/13 (76.9%) | 11/11 (100.0%) |
| Priority accuracy | 23/29 (79.3%) | 27/29 (93.1%) |
| In-scope accuracy | 29/29 (100.0%) | 29/29 (100.0%) |
| Primary theme accuracy | 25/29 (86.2%) | 26/29 (89.7%) |
| Must-review items sent to human | 13/13 (100.0%) | 13/13 (100.0%) |
| Review rate | 18/30 (60.0%) | 14/30 (46.7%) |
| Same priority in all runs | 26/30 (86.7%) | 29/30 (96.7%) |
| Same queue in all runs | 25/30 (83.3%) | 29/30 (96.7%) |

## Items whose priority or queue changed (run 1)

| id | split | gold priority | gold must_review | v1 | v2 | better / worse |
|---|---|---|---|---|---|---|
| C009 | test | Medium | N | High · human_review | Medium · standard_queue | better |
| C010 | dev | Medium | N | High · human_review | Medium · standard_queue | better |
| C011 | dev | Medium | N | High · human_review | Medium · standard_queue | better |
| C012 | test | Medium | N | High · human_review | Medium · standard_queue | better |
| C013 | dev | Medium | N | High · human_review | Medium · standard_queue | better |
| C020 | dev | High | Y | Medium · human_review | High · human_review | better |
| C030 | test | Low | Y | Low · human_review | Low · standard_queue | worse |
| C033 | dev | Low | N | Low · human_review | Low · out_of_scope_confirm | better |
