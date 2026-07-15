"""Tests for the answer coverage checker (Sprint 4)."""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.rag.v2.coverage import check_coverage


FACTS = [
    {"id": "f1", "claim": "MangoTree receives $1,437,491.34",
     "verbatim_quote": "the sum of $1,437,491.34 shall be paid to MangoTree",
     "source_chunk_id": 1},
    {"id": "f2", "claim": "Hearing is July 9",
     "verbatim_quote": "The hearing on the escrow settlement is scheduled for the 9th",
     "source_chunk_id": 2},
    {"id": "f3", "claim": "Note rate is 9%",
     "verbatim_quote": "the Note ($6,450,990.55 at 9%, dated July 17, 2023)",
     "source_chunk_id": 3},
]


def test_fully_covered_answer_ok():
    answer = (
        "MangoTree is owed $1,437,491.34 from escrow [#1]. The Note carries "
        "a 9% rate [#3]."
    )
    rep = check_coverage(answer, FACTS)
    assert rep.ok, f"expected ok, gaps={rep.to_dict()['gaps']}"


def test_uncited_number_flagged():
    answer = (
        "MangoTree is owed $1,437,491.34 [#1], and separately a $999,999 "
        "payment was made."   # $999,999 appears in no fact
    )
    rep = check_coverage(answer, FACTS)
    assert not rep.ok
    assert any(g.token.replace(" ", "") == "$999,999" or "999,999" in g.token for g in rep.gaps)


def test_currency_formatting_tolerated():
    # Prose says $1.44M-ish shorthand; fact quotes the full figure.
    answer = "The escrow to MangoTree is $1,437,491.34 [#1]."
    rep = check_coverage(answer, FACTS)
    assert rep.ok


def test_analysis_paragraph_exempt():
    answer = (
        "MangoTree is owed $1,437,491.34 [#1].\n\n"
        "Based on legal analysis: a recovery near $10,000,000 is plausible "
        "if the sale closes, though this figure is inferred."
    )
    rep = check_coverage(answer, FACTS)
    # $10,000,000 is only in a labelled-analysis paragraph -> exempt.
    assert rep.ok, f"analysis paragraph should be exempt, gaps={rep.to_dict()['gaps']}"


def test_uncited_date_flagged():
    answer = "The plan administrator takes control on July 15, 2026."
    rep = check_coverage(answer, FACTS)
    assert not rep.ok
    assert any(g.kind == "date" for g in rep.gaps)


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
