import pytest
from pydantic import ValidationError

from conftest import make_output
from triage.llm import provider_schema
from triage.schema import TriageOutput, json_schema


def test_valid_output_parses():
    out = TriageOutput.model_validate(make_output())
    assert out.priority == "Low"


@pytest.mark.parametrize("bad", [
    {"priority": "Urgent"},                 # not an allowed enum value
    {"themes": []},                         # at least one theme
    {"primary_theme": "speeding"},          # unknown theme
    {"summary": []},                        # at least one sentence
    {"unexpected_field": 1},                # extra fields forbidden
    {"title": "x" * 121},                   # title too long
])
def test_invalid_outputs_rejected(bad):
    with pytest.raises(ValidationError):
        TriageOutput.model_validate(make_output(**bad))


def test_missing_key_field_rejected():
    d = make_output()
    del d["key_fields"]["in_scope"]
    with pytest.raises(ValidationError):
        TriageOutput.model_validate(d)


def test_provider_schema_keeps_field_named_title():
    # Regression: the cleaner used to delete every key called "title", including the
    # output field "title", and Gemini rejected the schema ("requires unspecified property 'title'").
    s = provider_schema(json_schema())
    assert "title" in s["properties"]
    assert "title" in s["required"]


def test_provider_schema_inlines_refs_and_strips_constraints():
    s = provider_schema(json_schema())
    text = str(s)
    assert "$ref" not in text and "$defs" not in text
    assert "maxLength" not in text and "minItems" not in text
    assert s["properties"]["key_fields"]["properties"]["in_scope"]["type"] == "boolean"
