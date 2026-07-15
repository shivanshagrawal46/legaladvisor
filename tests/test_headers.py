"""Tests for RFC 2047 header decoding + mojibake detection (Sprint 2)."""
from __future__ import annotations

import sys
import traceback
from email.header import Header
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cleaner.headers import (
    is_encoded_word, decode_mime_header, looks_like_mojibake, try_fix_mojibake,
)


def _encode(subject: str, charset: str = "utf-8") -> str:
    return Header(subject, charset).encode()


def test_plain_header_unchanged_idempotent():
    plain = "RE: 31 Fort Hill Drive — escrow release"
    assert not is_encoded_word(plain)
    assert decode_mime_header(plain) == plain


def test_b_encoded_subject_decodes():
    original = "RE: IPA/MangoTree — Escrow Release & Warshawsky Mediation"
    enc = _encode(original)
    assert is_encoded_word(enc)
    assert decode_mime_header(enc) == original


def test_multipart_encoded_subject_decodes():
    # Two encoded-words concatenated (the real-world case in the PDF export).
    enc = _encode("RE: 31 Fort Hill Drive (Case No. 8-24-73893-spg) ") + " " + _encode("— $14M Offer + Note Maturity")
    decoded = decode_mime_header(enc)
    assert "31 Fort Hill Drive" in decoded
    assert "$14M Offer" in decoded
    assert "=?" not in decoded, "encoded-word残 leaked through"


def test_malformed_header_never_raises():
    assert decode_mime_header("=?utf-8?B?not-valid-base64!!?=") is not None
    assert decode_mime_header(None) == ""


def test_mojibake_detected_and_fixed():
    # Build a mojibake string: valid HTML encoded utf-16-le then read cp1252.
    html = "<html><body>Dear Bill, the escrow is $1,437,491.34</body></html>"
    garbage = html.encode("cp1252").decode("utf-16-le", errors="ignore")
    assert looks_like_mojibake(garbage), "should detect CJK-garbage mojibake"
    fixed = try_fix_mojibake(garbage)
    assert "html" in fixed.lower() or "escrow" in fixed.lower()


def test_clean_english_not_flagged():
    clean = "Dear Bill, the escrow settlement is $1,437,491.34 due July 9."
    assert not looks_like_mojibake(clean)
    assert try_fix_mojibake(clean) == clean


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
