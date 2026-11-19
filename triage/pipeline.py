"""End-to-end pipeline: ingest -> LLM structured output -> schema validation ->
provenance check -> routing. One complaint in, one JSON-serialisable record out."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable, Optional

from pydantic import ValidationError

from .duplicates import group_duplicates
from .grounding import check_summary
from .ingest import IngestResult, OcrFn, ingest_item, tesseract_ocr
from .llm import LLMClient
from .routing import route
from .schema import TriageOutput, json_schema

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "prompts"

# Optional deterministic checks applied after the model (prompt versions may enable them).
RuleFn = Callable[[str, dict], list[str]]


def load_prompt(version: str) -> str:
    return (PROMPTS / f"{version}.md").read_text()


def build_user_message(text: str) -> str:
    # Delimit untrusted text; strip any delimiter the complainant typed so they cannot "close" it.
    safe = text.replace("<complaint>", "").replace("</complaint>", "")
    return f"<complaint>\n{safe}\n</complaint>"


def call_and_validate(client: LLMClient, system: str, user: str, max_attempts: int = 2):
    """Return (TriageOutput | None, list of error strings, raw text of last attempt)."""
    errors: list[str] = []
    raw = ""
    msg = user
    for _ in range(max_attempts):
        raw = client.complete(system, msg, json_schema())
        try:
            return TriageOutput.model_validate(json.loads(raw)), errors, raw
        except (json.JSONDecodeError, ValidationError) as e:
            err = str(e).splitlines()[0] if isinstance(e, json.JSONDecodeError) else e.errors()[0]["msg"]
            errors.append(err)
            msg = f"{user}\n\nYour previous answer was invalid ({err}). Return only valid JSON matching the schema."
    return None, errors, raw


def process_item(
    item: dict,
    client: LLMClient,
    system_prompt: str,
    scans_dir: Path = ROOT / "data" / "scans",
    ocr: OcrFn = tesseract_ocr,
    rules: Optional[RuleFn] = None,
) -> dict:
    t0 = time.time()
    ing: IngestResult = ingest_item(item, scans_dir, ocr=ocr)
    rec: dict = {
        "id": item["id"],
        "channel": item["channel"],
        "ingest": {"source": ing.source, "ocr_confidence": ing.ocr_confidence,
                   "ocr_words": ing.ocr_words, "readable": ing.readable, "note": ing.note},
        "text": ing.text,
    }
    out: Optional[TriageOutput] = None
    errors: list[str] = []
    llm_error = None
    if ing.readable:
        try:
            out, errors, raw = call_and_validate(client, system_prompt, build_user_message(ing.text))
            if out is None:
                rec["raw_invalid"] = raw[:2000]
        except Exception as e:  # provider outage after retries: never crash the batch, send to a human
            llm_error = f"{type(e).__name__}: {str(e)[:300]}"
    rec["llm_error"] = llm_error
    rec["schema_ok"] = out is not None
    rec["schema_errors"] = errors

    kept: list = []
    dropped: list = []
    if out is not None:
        g = check_summary([s.model_dump() for s in out.summary], ing.text)
        kept, dropped = g.kept, g.dropped
        rec["output"] = out.model_dump()
        rec["output"]["summary"] = kept
    rec["grounding_dropped"] = dropped

    flags = rules(ing.text, rec.get("output") or {}) if (rules and ing.readable) else []
    if llm_error:
        flags = ["llm_unavailable"]
    r = route(
        readable=ing.readable,
        schema_ok=out is not None,
        priority=out.priority if out else None,
        needs_review=out.needs_review if out else None,
        injection_suspected=out.injection_suspected if out else None,
        in_scope=out.key_fields.in_scope if out else None,
        grounding_dropped=len(dropped),
        kept_sentences=len(kept),
        rule_flags=flags,
    )
    rec["route"] = {"queue": r.queue, "reasons": r.reasons}
    rec["model"] = client.name
    rec["seconds"] = round(time.time() - t0, 2)
    return rec


def run_batch(items: list[dict], client: LLMClient, system_prompt: str, **kw) -> list[dict]:
    records = [process_item(it, client, system_prompt, **kw) for it in items]
    groups = group_duplicates({r["id"]: r["text"] for r in records if r["text"]})
    for r in records:
        r["duplicate_group"] = groups.get(r["id"])
    return records
