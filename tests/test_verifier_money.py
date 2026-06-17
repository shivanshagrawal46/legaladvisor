"""Tests for currency reconciliation in the verifier critical-token check
(Sprint 7.6 normalization wired into verify). Formatting differences must
PASS; materially different amounts must still FAIL."""
from src.rag.v2.verifier import _check_critical_tokens, _normalize

D = "$"  # avoid shell-escaping pain in any harness


def _ok(quote, chunk):
    return _check_critical_tokens(quote, _normalize(chunk)) is None


def test_comma_cents_formatting_passes():
    assert _ok(f"paid {D}2,300", "invoice total 2,300.00 dollars")
    assert _ok(f"sold for {D}810,000", "consideration 810,000.00")


def test_millions_shorthand_passes():
    assert _ok(f"value of {D}1.45M", "market value 1,450,000.00")


def test_exact_substring_still_passes():
    assert _ok(f"check for {D}29,000", "a check for $29,000 to the HOA")


def test_materially_different_amount_fails():
    # $450,000 vs $405,000 is a ~10% real difference — must NOT verify.
    assert not _ok(f"settlement {D}450,000", "amount 405,000.00")


def test_missing_amount_fails():
    assert not _ok(f"paid {D}99,999", "no monetary figure remotely close here 12.00")


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
