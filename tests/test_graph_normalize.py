"""Tests for the consolidated graph normalization layer.

Proves the shared functions match production behaviour and that the known
historical bugs (directional spelling, parcel punctuation, address-coded LLCs)
stay fixed.
"""
from src.graph.normalize import (
    norm_name, strip_suffixes, slug, norm_addr, norm_address, addr_core,
    address_key, parcel_digits, normalize_parcel, llc_matches_address,
)
from src.graph import schema


def test_norm_name_strips_suffixes():
    # norm_name turns punctuation to spaces first, so "L.L.C." becomes "L L C";
    # strip_suffixes (the fuzzy-match path) is what fully removes it.
    assert norm_name("520E LLC") == "520E"
    assert norm_name("Thomas J. Sauers, Inc.") == "THOMAS J SAUERS"
    assert strip_suffixes(norm_name("IPA Asset Management, L.L.C.")) == "IPA ASSET MANAGEMENT"


def test_strip_suffixes():
    assert strip_suffixes("IPA ASSET MANAGEMENT LLC") == "IPA ASSET MANAGEMENT"
    assert strip_suffixes("ACME CORP") == "ACME"


def test_slug():
    assert slug("520E LLC") == "520e_llc"
    assert slug("  ") == "x"


def test_directional_bug_fixed():
    # The bug that re-OCR'd 227 W Neck because 'W' != 'West'.
    assert addr_core(norm_address("227 W Neck Rd")) == addr_core(norm_address("227 West Neck Road"))
    # Directional placement independence.
    assert addr_core(norm_address("83 S Ann Drive")) == addr_core(norm_address("83 Ann Drive S"))
    assert address_key("227 W Neck Rd") == "227 west neck"


def test_addr_core_drops_city_and_suffix():
    # City and street-type must not enter the key.
    assert addr_core(norm_address("59 Beecher St, Smithtown NY")) == \
           addr_core(norm_address("59 Beecher Street"))


def test_parcel_digits_collapses_punctuation():
    assert parcel_digits("0200-123.00-04.00-005.000") == "0200123000400005000"
    assert parcel_digits("0200 123 4 5") == parcel_digits("0200-123-4-5")
    assert normalize_parcel("  0200-123 ") == "0200-123"


def test_address_coded_llc():
    assert llc_matches_address("132W130 LLC", "132 West 130th Street") is True
    assert llc_matches_address("9RO LLC", "9 Roda Ave") is True
    # Negatives: name does not lead with house number.
    assert llc_matches_address("RH PHILLIPS LLC", "12 Phillips Rd") is False
    assert llc_matches_address("JDK COVE LLC", "5 Cove Ln") is False


def test_schema_vocab_consistent():
    assert schema.SIDE_DAVID == "david_network"
    assert schema.REL_OWNS in schema.EDGE_TYPES
    assert schema.authority_for("court_order") > schema.authority_for("email_body")
    assert schema.authority_for("title_report") == 1.15
    assert schema.authority_for("unknown_type") == schema.DEFAULT_AUTHORITY


if __name__ == "__main__":
    import sys
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
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
