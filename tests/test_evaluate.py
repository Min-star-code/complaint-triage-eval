from conftest import make_output
from triage.evaluate import consistency, injection_goal_achieved, metrics, pred_priority


def rec(cid, priority, queue="human_review", in_scope=True, theme="use_of_force", readable=True, schema_ok=True):
    out = make_output(priority=priority, primary_theme=theme, themes=[theme])
    out["key_fields"]["in_scope"] = in_scope
    return {"id": cid, "ingest": {"readable": readable}, "schema_ok": schema_ok, "schema_errors": [],
            "output": out if schema_ok else None, "route": {"queue": queue, "reasons": []},
            "grounding_dropped": [], "text": "x"}


def lab(priority, must="Y", in_scope="Y", theme="use_of_force"):
    return {"priority": priority, "must_review": must, "in_scope": in_scope, "primary_theme": theme}


def test_high_recall_precision_and_safety_net():
    recs = {"a": rec("a", "High"), "b": rec("b", "Medium", queue="human_review"),
            "c": rec("c", "High"), "d": rec("d", "Low", queue="standard_queue")}
    labels = {"a": lab("High"), "b": lab("High"), "c": lab("Medium"), "d": lab("Low", must="N")}
    m = metrics(list(recs), recs, labels)
    assert m["high_recall"] == (1, 2)          # b missed by the model
    assert m["high_to_human"] == (2, 2)        # ...but still reached a human
    assert m["high_precision"] == (1, 2)       # c over-flagged
    assert m["false_negatives"] == ["b"] and m["false_positives"] == ["c"]
    assert m["confusion"]["High"]["Medium"] == 1
    assert m["review_rate"] == (3, 4)


def test_unreadable_counts_as_not_high_but_excluded_from_field_accuracy():
    recs = {"a": rec("a", "High", readable=False, schema_ok=False)}
    m = metrics(["a"], recs, {"a": lab("High")})
    assert pred_priority(recs["a"]) == "unreadable"
    assert m["high_recall"] == (0, 1) and m["high_to_human"] == (1, 1)
    assert m["priority_acc"] == (0, 0)


def test_unlabelled_items_ignored():
    m = metrics(["a", "z"], {"a": rec("a", "Low")}, {"a": lab("Low")})
    assert m["n"] == 1


def test_consistency():
    r1 = {"a": rec("a", "High"), "b": rec("b", "Low", queue="standard_queue")}
    r2 = {"a": rec("a", "High"), "b": rec("b", "Medium", queue="standard_queue")}
    c = consistency(["a", "b"], [r1, r2])
    assert c["priority"] == (1, 2) and c["queue"] == (2, 2)


def test_injection_goal_checks():
    r = rec("C039", "High")
    assert injection_goal_achieved("C039", r, lab("High")) == "no"
    r["output"]["key_fields"]["in_scope"] = False
    assert injection_goal_achieved("C039", r, lab("High")) == "YES"
    r16 = rec("C016", "High")
    assert injection_goal_achieved("C016", r16, lab("Low")).startswith("YES")


def test_cer_is_edit_distance_over_reference_length():
    from triage.evaluate import cer

    assert cer("abc", "abc") == 0
    assert cer("abcd", "abxd") == 0.25
    long = "the officer was rude to me at the station " * 10   # > 200 chars
    assert cer(long, long.replace("rude", "rnde", 1)) < 0.01  # difflib's autojunk reported ~0.8 here
