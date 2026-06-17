"""Tests for bitemporal ownership-interval logic (Sprint 3.2.3).

Pure (no DB): proves `until` closes at the next conveyance, co-owners on the
same date share an `until`, the most-recent owner stays open, and the
as-of-date activity test is correct.
"""
from datetime import datetime

from src.graph.bitemporal import compute_until, _active, owner_as_of


def _d(y, m, day):
    return datetime(y, m, day)


def test_compute_until_closes_at_next_conveyance():
    dates = [_d(2010, 1, 1), _d(2015, 6, 1), _d(2020, 3, 1)]
    nxt = compute_until(dates)
    assert nxt[_d(2010, 1, 1)] == _d(2015, 6, 1)
    assert nxt[_d(2015, 6, 1)] == _d(2020, 3, 1)
    # most recent owner stays open
    assert nxt[_d(2020, 3, 1)] is None


def test_compute_until_coowners_share_until():
    # two grantees acquire on the same date -> same until (next distinct date)
    dates = [_d(2017, 8, 23), _d(2017, 8, 23), _d(2019, 1, 1)]
    nxt = compute_until(dates)
    assert nxt[_d(2017, 8, 23)] == _d(2019, 1, 1)
    assert nxt[_d(2019, 1, 1)] is None


def test_compute_until_ignores_none_dates():
    nxt = compute_until([None, _d(2012, 5, 5), None])
    assert nxt == {_d(2012, 5, 5): None}


def test_active_interval_boundaries():
    e = {"as_of": _d(2015, 1, 1), "until": _d(2020, 1, 1)}
    assert _active(e, _d(2017, 6, 1)) is True
    # as_of is inclusive
    assert _active(e, _d(2015, 1, 1)) is True
    # until is exclusive (the day of the next transfer, the new owner holds)
    assert _active(e, _d(2020, 1, 1)) is False
    assert _active(e, _d(2014, 12, 31)) is False
    # open interval (current owner)
    assert _active({"as_of": _d(2020, 1, 1), "until": None}, _d(2026, 1, 1)) is True


def test_owner_as_of_picks_correct_holder():
    class _Col:
        def __init__(self, rows):
            self._rows = rows

        def find(self, q):
            t = q.get("type", {})
            allowed = t.get("$in") if isinstance(t, dict) else [t]
            return [r for r in self._rows
                    if r["type"] in allowed and r["dst"] == q.get("dst")]

    rows = [
        {"type": "GRANTEE_OF", "src": "ent_A", "dst": "prop_1",
         "as_of": _d(2010, 1, 1), "until": _d(2018, 5, 1)},
        {"type": "GRANTEE_OF", "src": "ent_B", "dst": "prop_1",
         "as_of": _d(2018, 5, 1), "until": None},
    ]
    col = _Col(rows)
    owners_2015 = [e["src"] for e in owner_as_of(col, "prop_1", _d(2015, 6, 1))]
    owners_2020 = [e["src"] for e in owner_as_of(col, "prop_1", _d(2020, 6, 1))]
    assert owners_2015 == ["ent_A"]
    assert owners_2020 == ["ent_B"]


if __name__ == "__main__":
    import sys
    import traceback
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        try:
            fn()
            print(f"  PASS {fn.__name__}")
            passed += 1
        except Exception:
            print(f"  FAIL {fn.__name__}")
            traceback.print_exc()
    print(f"\n{passed}/{len(fns)} passed")
    sys.exit(0 if passed == len(fns) else 1)
