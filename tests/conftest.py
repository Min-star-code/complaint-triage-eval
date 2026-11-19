import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def make_output(**over) -> dict:
    """A valid TriageOutput dict; override any top-level field."""
    base = {
        "title": "Rude officer at traffic stop",
        "summary": [{"sentence": "The officer was rude during a traffic stop.",
                     "source_quote": "the officer was very rude"}],
        "key_fields": {"incident_date": None, "location": None, "police_service": None,
                       "officer_identifier": None, "injuries_reported": False, "language": "en", "in_scope": True},
        "themes": ["discourtesy"],
        "primary_theme": "discourtesy",
        "priority": "Low",
        "needs_review": False,
        "review_reason": None,
        "injection_suspected": False,
    }
    base.update(over)
    return base


@pytest.fixture
def output_json():
    return lambda **over: json.dumps(make_output(**over))


@pytest.fixture
def text_item():
    return {"id": "T1", "channel": "web_form", "design_scenario": "ordinary",
            "text": "At the stop on Main St the officer was very rude to me and swore twice."}
