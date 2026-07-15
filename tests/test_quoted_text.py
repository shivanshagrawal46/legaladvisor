"""Tests for the three-bucket quoted-text recovery (Sprint 2).

Pure logic — no DB, no embeddings. Proves:
  * the head/tail split matches what the cleaner drops today,
  * exact re-quotes are DUPLICATE (skip),
  * edited re-quotes are NEAR_MATCH (tamper candidate),
  * quoted text with no matching original is NOVEL (must be indexed).
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cleaner.quoted_text import (
    split_quoted_tail, iter_quoted_segments,
    quote_fingerprint, classify_block, classify_email_tail,
    BUCKET_DUPLICATE, BUCKET_NEAR_MATCH, BUCKET_NOVEL,
)

REPLY = (
    "Thanks Bill, that works for me. Let's proceed.\n\n"
    "On Mon, Jun 22, 2026 at 9:14 AM William Heuer <wheuer@westermanllp.com> wrote:\n"
    "> The 31FO proceeds are a separate recovery bucket from the IPA GWFG\n"
    "> escrow ($1,437,491.34). Both are MangoTree recovery paths but they\n"
    "> are independent and must not be netted against each other.\n"
)

ORIGINAL = (
    "The 31FO proceeds are a separate recovery bucket from the IPA GWFG "
    "escrow ($1,437,491.34). Both are MangoTree recovery paths but they "
    "are independent and must not be netted against each other."
)


def test_split_head_and_tail():
    head, tail = split_quoted_tail(REPLY)
    assert "Thanks Bill" in head
    assert "wrote:" not in head, "reply header leaked into head"
    assert "$1,437,491.34" in tail, "quoted evidence not captured in tail"


def test_split_no_tail_when_no_quotes():
    head, tail = split_quoted_tail("A short standalone note with no reply chain.")
    assert tail == ""
    assert head.startswith("A short standalone note")


def test_exact_requote_is_duplicate():
    known = {quote_fingerprint(ORIGINAL)}
    _, tail = split_quoted_tail(REPLY)
    segs = iter_quoted_segments(tail)
    assert segs, "expected at least one quoted segment"
    v = classify_block(segs[-1], known_fingerprints=known, candidate_texts=[ORIGINAL])
    assert v.bucket == BUCKET_DUPLICATE, f"expected duplicate, got {v.bucket}"
    assert not v.should_index


def test_edited_requote_is_near_match_tamper():
    # Someone changed the amount before forwarding: 1,437,491.34 -> 1,437,911.34
    edited_reply = REPLY.replace("$1,437,491.34", "$1,437,911.34")
    known = {quote_fingerprint(ORIGINAL)}  # only the TRUE original is known
    _, tail = split_quoted_tail(edited_reply)
    segs = iter_quoted_segments(tail)
    v = classify_block(segs[-1], known_fingerprints=known, candidate_texts=[ORIGINAL])
    assert v.bucket == BUCKET_NEAR_MATCH, f"expected near_match, got {v.bucket} (sim={v.best_similarity})"
    assert v.is_tamper_candidate
    assert not v.should_index


def test_novel_quote_must_be_indexed():
    # A forwarded message we were never party to; no matching original.
    novel_reply = (
        "See below — we were never copied on this.\n\n"
        "On Fri, Apr 3, 2026 David DeRosa <david@example.com> wrote:\n"
        "> Move the Granny White Pike funds to the new account before the\n"
        "> trustee reconciles the escrow. Keep this between us for now.\n"
    )
    known = {quote_fingerprint(ORIGINAL)}
    _, tail = split_quoted_tail(novel_reply)
    segs = iter_quoted_segments(tail)
    v = classify_block(segs[-1], known_fingerprints=known, candidate_texts=[ORIGINAL])
    assert v.bucket == BUCKET_NOVEL, f"expected novel, got {v.bucket} (sim={v.best_similarity})"
    assert v.should_index, "novel forwarded evidence would be lost!"


def test_classify_email_tail_endtoend():
    known = {quote_fingerprint(ORIGINAL)}
    verdicts = classify_email_tail(
        REPLY, known_fingerprints=known,
        candidate_provider=lambda seg: [ORIGINAL],
    )
    assert verdicts
    assert any(v.bucket == BUCKET_DUPLICATE for v in verdicts)


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
