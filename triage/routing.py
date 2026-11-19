"""Routing rules. Deterministic code, not the model, decides where a complaint goes.

Queues:
  human_review          - a person reads it before anything else happens
  out_of_scope_confirm  - model thinks it is out of scope; a person must confirm and refer it.
                          The model can never close or discard a complaint on its own.
  standard_queue        - normal investigator queue (still read by a person, just not first)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Route:
    queue: str
    reasons: list[str] = field(default_factory=list)


def route(
    *,
    readable: bool,
    schema_ok: bool,
    priority: Optional[str],
    needs_review: Optional[bool],
    injection_suspected: Optional[bool],
    in_scope: Optional[bool],
    grounding_dropped: int,
    kept_sentences: int,
    rule_flags: list[str] | None = None,
) -> Route:
    reasons: list[str] = []
    if not readable:
        reasons.append("ocr_unreadable")
    if not schema_ok:
        reasons.append("schema_invalid")
    if priority == "High":
        reasons.append("high_priority")
    if needs_review:
        reasons.append("model_flagged_review")
    if injection_suspected:
        reasons.append("injection_suspected")
    if schema_ok and kept_sentences == 0:
        reasons.append("no_grounded_summary")
    elif grounding_dropped:
        reasons.append("summary_sentence_dropped")
    reasons.extend(rule_flags or [])
    if reasons:
        return Route("human_review", reasons)
    if in_scope is False:
        return Route("out_of_scope_confirm", ["model_says_out_of_scope"])
    return Route("standard_queue", [])
