"""Tests for the claim-entailment judge (Sprint 4). No API — the judge
function is injected as a deterministic fake."""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.rag.v2.entailment import (
    judge_facts, _parse_judge_json, _normalize_label,
    ENTAIL_SUPPORTED, ENTAIL_PARTIAL, ENTAIL_NOT_SUPPORTED, ENTAIL_SKIPPED,
)


def fake_judge(claim: str, quote: str):
    """Deterministic stand-in for gpt-5: SUPPORTED if the claim's key words
    appear in the quote, NOT_SUPPORTED if the claim is negated."""
    c = claim.lower()
    q = quote.lower()
    if "fully paid" in c and "behind" in q:
        return "NOT_SUPPORTED", "quote says behind, claim says paid"
    if "480" in c and "480" in q:
        return "SUPPORTED", "amount matches"
    if "9%" in c and "9%" in q:
        return "SUPPORTED", "rate matches"
    return "PARTIAL", "insufficient overlap"


def test_supported_and_failed_separated():
    facts = [
        {"id": "f1", "claim": "Debtor is $480k behind",
         "verbatim_quote": "they are $480k behind in payments"},
        {"id": "f2", "claim": "CrossCountry is fully paid up",
         "verbatim_quote": "they are $480k behind in payments"},
    ]
    rep = judge_facts(facts, judge_fn=fake_judge)
    by = {i.fact_id: i for i in rep.items}
    assert by["f1"].label == ENTAIL_SUPPORTED
    assert by["f2"].label == ENTAIL_NOT_SUPPORTED
    assert not rep.all_ok
    assert [i.fact_id for i in rep.failed] == ["f2"]


def test_missing_quote_skipped():
    facts = [{"id": "f3", "claim": "something", "verbatim_quote": ""}]
    rep = judge_facts(facts, judge_fn=fake_judge)
    assert rep.items[0].label == ENTAIL_SKIPPED
    assert rep.all_ok  # skipped is not a failure


def test_partial_not_blocking_by_default():
    facts = [{"id": "f4", "claim": "unrelated thing",
              "verbatim_quote": "totally different text"}]
    rep = judge_facts(facts, judge_fn=fake_judge)
    assert rep.items[0].label == ENTAIL_PARTIAL
    assert rep.all_ok  # PARTIAL doesn't hard-fail unless configured


def test_partial_blocking_when_configured():
    facts = [{"id": "f5", "claim": "unrelated thing",
              "verbatim_quote": "totally different text"}]
    rep = judge_facts(facts, judge_fn=fake_judge, fail_on_partial=True)
    assert not rep.all_ok


def test_judge_never_crashes_answer():
    def boom(claim, quote):
        raise RuntimeError("model down")
    facts = [{"id": "f6", "claim": "x", "verbatim_quote": "y quote long enough"}]
    rep = judge_facts(facts, judge_fn=boom)
    assert rep.items[0].label == "ERROR"
    assert rep.all_ok  # ERROR is non-blocking (deterministic verifier still gates)


def test_json_parsing_robust():
    assert _parse_judge_json('{"label":"SUPPORTED","reason":"ok"}')[0] == "SUPPORTED"
    assert _parse_judge_json('noise {"label":"NOT_SUPPORTED","reason":"no"} tail')[0] == "NOT_SUPPORTED"
    assert _normalize_label("not supported") == ENTAIL_NOT_SUPPORTED
    assert _normalize_label("Supported") == ENTAIL_SUPPORTED


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
            passed += 1
        except Exception:  # noqa: BLE001
            print(f"FAIL  {fn.__name__}")
            traceback.print_exc()
    print(f"\n{passed}/{len(fns)} test functions passed")
    sys.exit(0 if passed == len(fns) else 1)
