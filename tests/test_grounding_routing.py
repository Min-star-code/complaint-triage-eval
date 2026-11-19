from triage.duplicates import group_duplicates
from triage.grounding import check_summary
from triage.routing import route

SRC = "On March 3 the officer pushed me into the cruiser. I have two cracked ribs. He said “stop wasting my time”."


def s(sentence, quote):
    return {"sentence": sentence, "source_quote": quote}


def test_exact_quote_kept():
    g = check_summary([s("The officer pushed the complainant.", "the officer pushed me into the cruiser")], SRC)
    assert len(g.kept) == 1 and g.n_dropped == 0


def test_quote_matching_ignores_case_whitespace_and_curly_quotes():
    g = check_summary([s("Officer was dismissive.", 'He said "stop   wasting my time"')], SRC)
    assert g.n_dropped == 0


def test_paraphrased_quote_dropped():
    g = check_summary([s("The officer shoved them.", "the officer shoved me onto the car")], SRC)
    assert g.dropped[0]["reason"] == "quote not found in source"


def test_short_quote_dropped():
    g = check_summary([s("Ribs were injured.", "ribs")], SRC)
    assert g.dropped[0]["reason"] == "quote too short"


def test_invented_number_dropped_even_with_valid_quote():
    g = check_summary([s("The complainant has three cracked ribs and 4 bruises.", "I have two cracked ribs")], SRC)
    assert g.dropped[0]["reason"].startswith("number not in source")


def test_number_present_in_source_is_fine():
    g = check_summary([s("It happened on March 3.", "On March 3 the officer")], SRC)
    assert g.n_dropped == 0


BASE = dict(readable=True, schema_ok=True, priority="Low", needs_review=False, injection_suspected=False,
            in_scope=True, grounding_dropped=0, kept_sentences=2)


def test_low_clean_goes_to_standard_queue():
    assert route(**BASE).queue == "standard_queue"


def test_high_goes_to_human():
    r = route(**{**BASE, "priority": "High"})
    assert r.queue == "human_review" and "high_priority" in r.reasons


def test_out_of_scope_is_never_closed_only_sent_for_confirmation():
    r = route(**{**BASE, "in_scope": False})
    assert r.queue == "out_of_scope_confirm"


def test_out_of_scope_but_high_still_human_first():
    assert route(**{**BASE, "in_scope": False, "priority": "High"}).queue == "human_review"


def test_unreadable_scan_goes_to_human_without_model():
    r = route(**{**BASE, "readable": False, "schema_ok": False, "priority": None, "needs_review": None,
                 "injection_suspected": None, "in_scope": None, "kept_sentences": 0})
    assert r.queue == "human_review" and "ocr_unreadable" in r.reasons


def test_injection_flag_goes_to_human():
    assert "injection_suspected" in route(**{**BASE, "injection_suspected": True}).reasons


def test_dropped_sentence_goes_to_human():
    assert "summary_sentence_dropped" in route(**{**BASE, "grounding_dropped": 1}).reasons


def test_no_grounded_sentence_left():
    assert "no_grounded_summary" in route(**{**BASE, "grounding_dropped": 2, "kept_sentences": 0}).reasons


def test_rule_flags_force_human():
    r = route(**{**BASE, "rule_flags": ["keyword_hospital"]})
    assert r.queue == "human_review" and "keyword_hospital" in r.reasons


def test_duplicates_grouped_but_distinct_texts_not():
    letter = ("I am writing to express my concern about the police response to the peaceful gathering at the park "
              "on June 1. Officers used pepper spray on people sitting down. I call on your office to review it.")
    texts = {"A": letter + " Concerned resident.", "B": letter + " A citizen.",
             "C": "My bike was stolen from the library and nobody called me back about the report."}
    g = group_duplicates(texts)
    assert g["A"] == g["B"] and "C" not in g
