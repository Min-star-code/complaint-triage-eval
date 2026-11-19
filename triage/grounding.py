"""Provenance check: every summary sentence must cite an exact quote from the complaint.

A sentence is dropped (and counted) if
  - its quote is shorter than MIN_QUOTE_WORDS words,
  - its quote does not appear in the source text after normalisation, or
  - the sentence contains a number that appears nowhere in the source (invented detail).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

MIN_QUOTE_WORDS = 3

_QUOTES = {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"}


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    for a, b in _QUOTES.items():
        s = s.replace(a, b)
    s = s.lower()
    s = re.sub(r"[\"'`]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip(" .,;:")


def _numbers(s: str) -> set[str]:
    return set(re.findall(r"\d+", s))


@dataclass
class GroundingResult:
    kept: list[dict] = field(default_factory=list)
    dropped: list[dict] = field(default_factory=list)  # each has "reason"

    @property
    def n_dropped(self) -> int:
        return len(self.dropped)


def check_summary(summary: list[dict], source: str) -> GroundingResult:
    src = normalize(source)
    src_numbers = _numbers(source)
    res = GroundingResult()
    for s in summary:
        quote = normalize(s.get("source_quote", ""))
        if len(quote.split()) < MIN_QUOTE_WORDS:
            res.dropped.append({**s, "reason": "quote too short"})
        elif quote not in src:
            res.dropped.append({**s, "reason": "quote not found in source"})
        elif _numbers(s.get("sentence", "")) - src_numbers:
            extra = sorted(_numbers(s["sentence"]) - src_numbers)
            res.dropped.append({**s, "reason": f"number not in source: {', '.join(extra)}"})
        else:
            res.kept.append(s)
    return res
