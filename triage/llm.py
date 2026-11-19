"""LLM clients. Every client returns the model's raw text; parsing and validation happen
in the pipeline so that a schema failure is observable and counted, not hidden by an SDK.

Backends:
  gemini  - Google Gemini API (GEMINI_API_KEY, GEMINI_MODEL)
  azure   - Azure OpenAI (AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT,
            AZURE_OPENAI_API_VERSION)
  fake    - scripted responses for tests
"""
from __future__ import annotations

import copy
import os
import time
from dataclasses import dataclass, field
from typing import Callable, Protocol

UNSUPPORTED_KEYS = {"maxLength", "minLength", "minItems", "maxItems", "title", "default"}


def provider_schema(schema: dict) -> dict:
    """Inline $defs and drop keywords some providers reject. Pydantic still enforces them afterwards."""
    schema = copy.deepcopy(schema)
    defs = schema.pop("$defs", {})

    def walk(node, in_properties: bool = False):
        if isinstance(node, dict):
            if "$ref" in node and not in_properties:
                return walk(copy.deepcopy(defs[node["$ref"].split("/")[-1]]))
            if in_properties:  # keys here are field names (e.g. a field called "title"), keep them all
                return {k: walk(v) for k, v in node.items()}
            return {k: walk(v, in_properties=(k == "properties")) for k, v in node.items() if k not in UNSUPPORTED_KEYS}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    return walk(schema)


class LLMClient(Protocol):
    name: str

    def complete(self, system: str, user: str, schema: dict) -> str: ...


def _with_retry(fn: Callable[[], str], tries: int = 7) -> str:
    delay = 5.0
    for attempt in range(tries):
        try:
            return fn()
        except Exception as e:  # provider SDKs raise many types; retry only rate/server errors
            msg = str(e)
            retryable = any(s in msg for s in ("429", "RESOURCE_EXHAUSTED", "503", "500", "UNAVAILABLE", "overloaded"))
            if not retryable or attempt == tries - 1:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 60)
    raise RuntimeError("unreachable")


class GeminiClient:
    def __init__(self, model: str | None = None, temperature: float = 0.0):
        from google import genai

        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
        self.temperature = temperature
        self.name = f"gemini:{self.model}"
        self._client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def complete(self, system: str, user: str, schema: dict) -> str:
        from google.genai import types

        cfg = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_json_schema=provider_schema(schema),
            temperature=self.temperature,
        )
        return _with_retry(
            lambda: self._client.models.generate_content(model=self.model, contents=user, config=cfg).text or ""
        )


class AzureOpenAIClient:
    def __init__(self, deployment: str | None = None, temperature: float = 0.0):
        from openai import AzureOpenAI

        self.deployment = deployment or os.environ["AZURE_OPENAI_DEPLOYMENT"]
        self.temperature = temperature
        self.name = f"azure:{self.deployment}"
        self._client = AzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        )

    def complete(self, system: str, user: str, schema: dict) -> str:
        def call() -> str:
            r = self._client.chat.completions.create(
                model=self.deployment,
                temperature=self.temperature,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "triage_output", "schema": provider_schema(schema), "strict": False},
                },
            )
            return r.choices[0].message.content or ""

        return _with_retry(call)


@dataclass
class FakeClient:
    """Returns scripted responses in order (or via a function of the user prompt)."""

    responses: list[str] | Callable[[str], str] = field(default_factory=list)
    name: str = "fake"
    calls: list[tuple[str, str]] = field(default_factory=list)

    def complete(self, system: str, user: str, schema: dict) -> str:
        self.calls.append((system, user))
        if callable(self.responses):
            return self.responses(user)
        return self.responses[len(self.calls) - 1]


def make_client(backend: str) -> LLMClient:
    if backend == "gemini":
        return GeminiClient()
    if backend == "azure":
        return AzureOpenAIClient()
    raise ValueError(f"unknown backend {backend!r}")
