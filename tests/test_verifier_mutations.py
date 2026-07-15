"""
Verifier mutation suite (Sprint 1 — measurement harness).

Goal: prove — deterministically, with no API/DB — that the citation
verifier catches corrupted facts. We take a set of KNOWN-GOOD facts (a
verbatim quote that genuinely appears in its chunk) and apply families of
mutations that a hallucinating model would produce, then assert the
verifier's catch behaviour.

Honesty about scope (this is the whole point of the exercise):

  * The deterministic verifier (`verify_facts`) guarantees ONE thing:
    the verbatim_quote actually appears in the cited chunk, with exact
    critical tokens (currency / dates / big numbers / percentages) and a
    fuzzy floor for the rest. Every mutation that corrupts those, OR the
    citation index, MUST be caught. We assert 100% on those families.

  * The verifier provably does NOT judge whether the CLAIM follows from
    the quote. So a "claim inversion" — flip the claim's meaning while
    keeping a real, verbatim quote — will (correctly, by design) still
    VERIFY here. We assert that too, as an executable record of the gap
    that the Sprint 4 cross-family entailment judge is built to close.

Run standalone:  python tests/test_verifier_mutations.py
Run via pytest:  pytest tests/test_verifier_mutations.py
"""
from __future__ import annotations

import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.rag.v2.verifier import (
    verify_facts,
    VERDICT_VERIFIED,
    VERDICT_CITATION_INVALID,
)


# ---------------------------------------------------------------------------
# Lightweight chunk stub — verify_facts only ever reads `.body` / `.text`.
# ---------------------------------------------------------------------------
@dataclass
class _Chunk:
    body: str
    text: str = ""


# ---------------------------------------------------------------------------
# Base corpus of known-good (chunk, claim, verbatim_quote) triples.
# Each quote appears verbatim in its chunk and carries at least one
# critical token so the critical-token gate is exercised.
# ---------------------------------------------------------------------------
BASE_CASES: List[Tuple[str, str, str]] = [
    (
        "the sum of $1,437,491.34 shall be paid to MangoTree; and the sum "
        "of $450,000 shall be paid to the IPA Debtor's estate",
        "MangoTree is to receive $1,437,491.34 from escrow",
        "the sum of $1,437,491.34 shall be paid to MangoTree",
    ),
    (
        "The Settlement Agreement Note ($6,450,990.55 at 9%, dated July 17, "
        "2023) matures in 23 days.",
        "The note carries a 9% rate",
        "The Settlement Agreement Note ($6,450,990.55 at 9%, dated July 17, 2023)",
    ),
    (
        "On June 19, 2026, broker Maida Srdanovic submitted a revised "
        "all-cash offer: Offer $14,000,000; Deposit 10% ($1,400,000).",
        "The new offer is $14,000,000 all cash",
        "Offer $14,000,000; Deposit 10% ($1,400,000)",
    ),
    (
        "they are $480k behind in payments to CrossCountry, but they are "
        "willing to propose a payment of $250k to get them to withdraw",
        "Debtor is $480k behind to CrossCountry",
        "they are $480k behind in payments to CrossCountry",
    ),
    (
        "premises known as 520 East 81st Street, Unit 2M forecloses on "
        "July 7, 2026 at 2:15 p.m.",
        "520 East 81st Street forecloses July 7, 2026",
        "520 East 81st Street, Unit 2M forecloses on July 7, 2026",
    ),
    (
        "the purchaser's $650,000 deposit is expected to be forfeited and "
        "placed into escrow with the firm as an additional asset",
        "A $650,000 deposit is expected to be forfeited",
        "the purchaser's $650,000 deposit is expected to be forfeited",
    ),
    (
        "Case No. 8-24-73893-spg — the stipulation was So-Ordered by the "
        "Court on February 3, 2026.",
        "The stipulation was so-ordered on February 3, 2026",
        "So-Ordered by the Court on February 3, 2026",
    ),
    (
        "subordinate the MangoTree recoveries until they have recovered "
        "$1,369,240 between the two of them.",
        "Subordination threshold is $1,369,240",
        "until they have recovered $1,369,240 between the two of them",
    ),
    (
        "the Debtor shall pay the amount of One Hundred Thousand Dollars "
        "($100,000.00) as an adequate protection payment within 3 days.",
        "Adequate protection payment is $100,000.00",
        "pay the amount of One Hundred Thousand Dollars ($100,000.00)",
    ),
    (
        "The COJ ($8,591,948.55, dated July 19, 2024) already reflects "
        "acceleration of the full balance.",
        "The COJ is $8,591,948.55",
        "The COJ ($8,591,948.55, dated July 19, 2024)",
    ),
    (
        "the collapsed sale to the confidential buyer was priced at "
        "$16,800,000 and never closed.",
        "The failed sale was $16,800,000",
        "priced at $16,800,000 and never closed",
    ),
    (
        "the purchaser's $840,000 contract deposit is at risk of forfeiture "
        "following the time-of-the-essence default.",
        "The contract deposit at risk is $840,000",
        "the purchaser's $840,000 contract deposit is at risk of forfeiture",
    ),
    (
        "64 North 16th St, Wheatley Heights $431,597.75 per settlement "
        "sheet; total escrow $1,887,491.34.",
        "64 North 16th St escrow is $431,597.75",
        "64 North 16th St, Wheatley Heights $431,597.75 per settlement sheet",
    ),
    (
        "the separate $20,000 held by Matt Tannenbaum is to be distributed "
        "60% to MangoTree / 40% to IPA.",
        "The Tannenbaum fund is $20,000 split 60/40",
        "the separate $20,000 held by Matt Tannenbaum",
    ),
    (
        "5161 Granny White Pike, Nashville $648,357.58 per settlement sheet.",
        "5161 Granny White Pike escrow is $648,357.58",
        "5161 Granny White Pike, Nashville $648,357.58 per settlement sheet",
    ),
    (
        "Island Properties directed removal of MangoTree from Lloyd's "
        "certificate LR20000531937 without Court authorization on June 12, 2026.",
        "MangoTree was removed from certificate LR20000531937",
        "certificate LR20000531937 without Court authorization",
    ),
    (
        "38 Parkside Ave, Miller Place $386,187.00 per settlement sheet.",
        "38 Parkside escrow is $386,187.00",
        "38 Parkside Ave, Miller Place $386,187.00 per settlement sheet",
    ),
    (
        "4 Calverton Court, Calverton $421,349.01 per settlement sheet.",
        "4 Calverton escrow is $421,349.01",
        "4 Calverton Court, Calverton $421,349.01 per settlement sheet",
    ),
]


def _good_facts_and_chunks() -> Tuple[List[dict], List[_Chunk]]:
    """One chunk per base case; one correct fact citing each (1-based)."""
    chunks = [_Chunk(body=c) for (c, _, _) in BASE_CASES]
    facts = [
        {
            "id": f"f{i+1}",
            "claim": claim,
            "source_chunk_id": i + 1,
            "verbatim_quote": quote,
            "confidence": "high",
        }
        for i, (_, claim, quote) in enumerate(BASE_CASES)
    ]
    return facts, chunks


# ---------------------------------------------------------------------------
# Mutators. Each returns a NEW quote (or None if not applicable to the case).
# These corrupt what the DETERMINISTIC verifier must catch.
# ---------------------------------------------------------------------------
def _mut_currency_drift(quote: str) -> str | None:
    import re
    m = re.search(r"\$([\d,]+)(\.\d+)?", quote)
    if not m:
        return None
    digits = m.group(1)
    # swap the first two significant digits -> a materially different amount
    only = digits.replace(",", "")
    if len(only) < 2 or only[0] == only[1]:
        # force a change
        bumped = str((int(only[0]) + 1) % 10) + only[1:]
    else:
        bumped = only[1] + only[0] + only[2:]
    # re-group with commas
    regrouped = f"{int(bumped):,}"
    return quote[: m.start()] + "$" + regrouped + (m.group(2) or "") + quote[m.end():]


def _mut_currency_magnitude(quote: str) -> str | None:
    """Drop a digit from the integer part -> an order-of-magnitude error
    ($450,000 -> $45,000). A distinct corruption from digit-swap: catches
    the 'off by a zero' class that is common and dangerous."""
    import re
    m = re.search(r"\$([\d,]+)(\.\d+)?", quote)
    if not m:
        return None
    only = m.group(1).replace(",", "")
    if len(only) < 2:
        return None
    shifted = only[:-1]  # drop last integer digit
    regrouped = f"{int(shifted):,}"
    return quote[: m.start()] + "$" + regrouped + (m.group(2) or "") + quote[m.end():]


def _mut_date_drift(quote: str) -> str | None:
    import re
    # bump a "Month DD, YYYY" day by 1
    m = re.search(r"([A-Z][a-z]+ )(\d{1,2})(, \d{4})", quote)
    if not m:
        return None
    day = int(m.group(2))
    new_day = day + 1 if day < 28 else day - 1
    return quote[: m.start()] + m.group(1) + str(new_day) + m.group(3) + quote[m.end():]


def _mut_bignum_drift(quote: str) -> str | None:
    import re
    # change a 4+ digit integer that is NOT part of a $ amount or a year
    for m in re.finditer(r"\b(\d{4,})\b", quote):
        tok = m.group(1)
        start = m.start()
        if start > 0 and quote[start - 1] in "$,.":
            continue
        if re.fullmatch(r"(19|20)\d{2}", tok):
            continue
        mutated = tok[:-1] + str((int(tok[-1]) + 1) % 10)
        return quote[: m.start()] + mutated + quote[m.end():]
    return None


def _mut_percent_drift(quote: str) -> str | None:
    import re
    m = re.search(r"(\d+)(%)", quote)
    if not m:
        return None
    val = int(m.group(1))
    new = val + 1 if val < 99 else val - 1
    return quote[: m.start()] + str(new) + "%" + quote[m.end():]


def _mut_paraphrase(quote: str) -> str:
    # a plausible paraphrase that is NOT verbatim in the chunk
    return "approximately " + quote.replace(" the ", " a ").replace("shall", "will") + " (paraphrased)"


# Families that corrupt a CRITICAL TOKEN (currency / date / big number /
# percentage). The verifier's critical-token gate GUARANTEES these are
# rejected, so we assert 100% catch on them.
DETERMINISTIC_MUTATORS: List[Tuple[str, Callable[[str], "str | None"]]] = [
    ("currency_drift", _mut_currency_drift),
    ("currency_magnitude", _mut_currency_magnitude),
    ("date_drift", _mut_date_drift),
    ("bignum_drift", _mut_bignum_drift),
    ("percent_drift", _mut_percent_drift),
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_positive_controls_verify():
    """Sanity: the un-mutated known-good facts must all VERIFY. If this
    fails, the suite would report false 'catches' and be worthless."""
    facts, chunks = _good_facts_and_chunks()
    report = verify_facts(facts, chunks)
    verified = [i for i in report.items if i.verdict == VERDICT_VERIFIED]
    assert len(verified) == len(facts), (
        f"positive control failed: only {len(verified)}/{len(facts)} "
        f"good facts verified — {[ (i.fact_id, i.reason) for i in report.items if i.verdict != VERDICT_VERIFIED ]}"
    )


def test_fabricated_citation_is_caught():
    """A citation pointing outside the retrieved set is a HARD fail."""
    facts, chunks = _good_facts_and_chunks()
    for f in facts:
        f["source_chunk_id"] = len(chunks) + 99  # nonexistent
    report = verify_facts(facts, chunks)
    caught = [i for i in report.items if i.verdict == VERDICT_CITATION_INVALID]
    assert len(caught) == len(facts), "fabricated citations not all caught"


def test_deterministic_mutations_all_caught():
    """Every applicable corruption of a critical token / verbatim span must
    be rejected (verdict != VERIFIED). Target: 100%."""
    _, chunks = _good_facts_and_chunks()
    total = 0
    caught = 0
    escapes: List[str] = []
    for i, (_, claim, quote) in enumerate(BASE_CASES):
        for name, mut in DETERMINISTIC_MUTATORS:
            new_q = mut(quote)
            if not new_q or new_q == quote:
                continue
            total += 1
            fact = {
                "id": f"m_{i}_{name}",
                "claim": claim,
                "source_chunk_id": i + 1,
                "verbatim_quote": new_q,
                "confidence": "high",
            }
            report = verify_facts([fact], [chunks[i]])
            verdict = report.items[0].verdict
            if verdict != VERDICT_VERIFIED:
                caught += 1
            else:
                escapes.append(f"[{name}] {new_q!r} wrongly VERIFIED against chunk #{i+1}")
    assert total >= 30, f"expected a substantial suite, only generated {total} mutations"
    assert caught == total, (
        f"catch rate {caught}/{total} — escapes:\n  " + "\n  ".join(escapes)
    )
    print(f"  critical-token mutations: {caught}/{total} caught (100%)")


def test_paraphrase_catch_rate_reported():
    """Paraphrase catching is NOT a hard guarantee (it depends on the fuzzy
    threshold), so we REPORT the rate rather than asserting 100%. A quote
    that keeps its critical tokens but rewords the surrounding text may or
    may not fall below the fuzzy floor. This surfaces the soft boundary."""
    _, chunks = _good_facts_and_chunks()
    total = 0
    caught = 0
    for i, (_, claim, quote) in enumerate(BASE_CASES):
        new_q = _mut_paraphrase(quote)
        if not new_q or new_q == quote:
            continue
        total += 1
        fact = {
            "id": f"p_{i}",
            "claim": claim,
            "source_chunk_id": i + 1,
            "verbatim_quote": new_q,
            "confidence": "high",
        }
        report = verify_facts([fact], [chunks[i]])
        if report.items[0].verdict != VERDICT_VERIFIED:
            caught += 1
    rate = (100.0 * caught / total) if total else 0.0
    print(f"  paraphrase mutations: {caught}/{total} caught ({rate:.0f}%) "
          f"[informational — not a hard guarantee]")
    # Sanity floor only: the machinery ran on a real suite.
    assert total >= 8


def test_claim_inversion_is_NOT_caught_documents_the_gap():
    """DOCUMENTED LIMITATION: the deterministic verifier checks quote-in-
    chunk, not claim-entailment. So flipping the claim's meaning while
    keeping a genuine verbatim quote still VERIFIES. This test PASSES when
    the gap exists — it is the executable spec for why Sprint 4 adds a
    cross-family entailment judge. If a future change makes this fail
    (i.e. the inversion gets caught), that's an improvement and the test
    should be updated."""
    # Real quote, but claim asserts the OPPOSITE of what the quote supports.
    chunk = _Chunk(body=BASE_CASES[3][0])  # "$480k behind ... $250k ... withdraw"
    fact = {
        "id": "inv1",
        "claim": "CrossCountry is fully paid up with no arrears",  # opposite
        "source_chunk_id": 1,
        "verbatim_quote": "they are $480k behind in payments to CrossCountry",
        "confidence": "high",
    }
    report = verify_facts([fact], [chunk])
    assert report.items[0].verdict == VERDICT_VERIFIED, (
        "claim inversion was caught — the entailment gap may be closed; "
        "if so, update this test to reflect the new guarantee."
    )
    print("  claim-inversion gap confirmed (Sprint 4 entailment judge target)")


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
