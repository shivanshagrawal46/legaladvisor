from src.rag.normalize_values import (normalize_money, money_matches, all_money,
                                       dates_match, normalize_date_iso)


def test_money_formats_reconcile():
    assert normalize_money("$1.45M") == 1_450_000.0
    assert normalize_money("1,450,000.00") == 1_450_000.0
    assert normalize_money("$1,450,000") == 1_450_000.0
    assert normalize_money("450K") == 450_000.0
    assert money_matches("$1.45M", "1,450,000.00")
    assert money_matches("$1,450,000", "1450000.49")  # rounding tol
    assert not money_matches("$1.45M", "$1.40M")


def test_all_money():
    vals = all_money("mortgage $450,000 and a lien of $12,500.50")
    assert 450000.0 in vals and 12500.5 in vals


def test_dates():
    assert normalize_date_iso("March 5, 2021") == "2021-03-05"
    assert dates_match("3/5/2021", "March 5, 2021")
    assert not dates_match("3/5/2021", "3/8/2021")
    assert dates_match("3/5/2021", "3/8/2021", days_tol=5)


if __name__ == "__main__":
    import sys, traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    ok = 0
    for fn in fns:
        try:
            fn(); print(f"  PASS {fn.__name__}"); ok += 1
        except Exception:
            print(f"  FAIL {fn.__name__}"); traceback.print_exc()
    print(f"{ok}/{len(fns)} passed")
    sys.exit(0 if ok == len(fns) else 1)
