"""Tests for the deadline radar (Sprint 5)."""
from __future__ import annotations

import sys
import traceback
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.detect.deadline_radar import extract_deadlines, upcoming


TODAY = date(2026, 7, 2)

CORPUS = (
    "On July 7, 2026 at 2:15 p.m., premises known as 520 East 81st Street "
    "forecloses.\n"
    "The hearing on the escrow settlement is scheduled for July 9, 2026.\n"
    "The Settlement Agreement Note matures on July 15, 2026.\n"
    "We had a nice call on June 3, 2026 about the weather.\n"  # no consequence
    "The Plan Administrator will take control on 2026-07-15.\n"
)


def test_extracts_consequential_dates():
    dls = extract_deadlines(CORPUS, today=TODAY)
    whens = {d.when for d in dls}
    assert date(2026, 7, 7) in whens, "foreclosure date missed"
    assert date(2026, 7, 9) in whens, "hearing date missed"
    assert date(2026, 7, 15) in whens, "note maturity missed"


def test_ignores_non_consequential_date():
    dls = extract_deadlines(CORPUS, today=TODAY)
    assert date(2026, 6, 3) not in {d.when for d in dls}, "weather date wrongly flagged"


def test_days_out_computed():
    dls = extract_deadlines(CORPUS, today=TODAY)
    by_date = {d.when: d for d in dls}
    assert by_date[date(2026, 7, 7)].days_out == 5
    assert by_date[date(2026, 7, 9)].days_out == 7


def test_iso_format_parsed():
    dls = extract_deadlines("takeover on 2026-07-15", today=TODAY)
    assert any(d.when == date(2026, 7, 15) for d in dls)


def test_upcoming_filter():
    dls = extract_deadlines(CORPUS, today=TODAY)
    up = upcoming(dls, within_days=10)
    assert all(0 <= d.days_out <= 10 for d in up)
    assert date(2026, 7, 7) in {d.when for d in up}


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
