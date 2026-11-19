"""Near-duplicate detection (form-letter campaigns) with word-shingle Jaccard similarity.

Deterministic and cheap, so it is done in code rather than by the LLM. Duplicates are only
grouped for the investigator; they are never merged or dropped, because a copy can add a
new fact (e.g. one letter in a campaign reports an injury).
"""
from __future__ import annotations

import re

THRESHOLD = 0.5


def shingles(text: str, k: int = 4) -> set[tuple[str, ...]]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    return {tuple(words[i : i + k]) for i in range(max(len(words) - k + 1, 1))}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def group_duplicates(texts: dict[str, str], threshold: float = THRESHOLD) -> dict[str, str]:
    """Return {id: group_id} for items that have at least one near-duplicate (union-find)."""
    ids = sorted(texts)
    sh = {i: shingles(texts[i]) for i in ids}
    parent = {i: i for i in ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, a in enumerate(ids):
        for b in ids[i + 1 :]:
            if jaccard(sh[a], sh[b]) >= threshold:
                parent[find(b)] = find(a)
    groups: dict[str, list[str]] = {}
    for i in ids:
        groups.setdefault(find(i), []).append(i)
    return {m: f"dup-{root}" for root, members in groups.items() if len(members) > 1 for m in members}
