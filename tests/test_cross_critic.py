"""Tests for the cross-family critique -> revise loop (no API)."""
from __future__ import annotations

import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.rag.v3.cross_critic import _parse_critique, run_cross_critique


@dataclass
class _Chunk:
    _id: str = "c1"
    body: str = "the sum of $1,437,491.34 shall be paid to MangoTree"
    text: str = ""
    date: Any = None
    from_email: str = "wheuer@westermanllp.com"


class _FakeCritic:
    def __init__(self, result):
        self._r = result
    def critique(self, question, answer, facts):
        return self._r


FACTS = [{"id": "f1", "claim": "MangoTree gets $1,437,491.34",
          "verbatim_quote": "the sum of $1,437,491.34 shall be paid to MangoTree"}]


def test_parse_valid_gaps():
    r = _parse_critique('{"has_gaps": true, "findings": ["missing July 9 deadline"]}')
    assert r["has_gaps"] is True
    assert r["findings"] == ["missing July 9 deadline"]


def test_parse_no_gaps_or_empty():
    assert _parse_critique('{"has_gaps": true, "findings": []}')["has_gaps"] is False
    assert _parse_critique("not json")["has_gaps"] is False
    assert _parse_critique("")["has_gaps"] is False


def test_no_gaps_keeps_original():
    critic = _FakeCritic({"has_gaps": False, "findings": []})
    out = run_cross_critique(
        anthropic_client=None, model="x", question="q", answer="orig",
        facts=FACTS, chunks=[_Chunk()], critic=critic)
    assert out["revised"] is False
    assert out["answer"] == "orig"


def test_empty_facts_noop():
    critic = _FakeCritic({"has_gaps": True, "findings": ["x"]})
    out = run_cross_critique(
        anthropic_client=None, model="x", question="q", answer="orig",
        facts=[], chunks=[_Chunk()], critic=critic)
    assert out["revised"] is False


def test_gaps_trigger_fable_revision(monkeypatch_generate=None):
    # Monkeypatch generate_verified_answer so Fable's revision needs no API.
    import src.rag.v2.answer_pipeline as ap

    @dataclass
    class _VA:
        answer: str = "REVISED answer addressing the July 9 deadline [#1]"
        facts: List[Dict[str, Any]] = field(default_factory=lambda: FACTS)
        fact_verdicts: List[Dict[str, Any]] = field(
            default_factory=lambda: [{"fact_id": "f1", "verdict": "VERIFIED"}])

    orig = ap.generate_verified_answer
    ap.generate_verified_answer = lambda **kw: _VA()
    try:
        critic = _FakeCritic({"has_gaps": True, "findings": ["missing July 9 deadline"]})
        out = run_cross_critique(
            anthropic_client=object(), model="claude", question="q",
            answer="orig", facts=FACTS, chunks=[_Chunk()], critic=critic)
        assert out["revised"] is True
        assert "REVISED" in out["answer"]
        assert out["fact_verdicts"][0]["verdict"] == "VERIFIED"
    finally:
        ap.generate_verified_answer = orig


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
