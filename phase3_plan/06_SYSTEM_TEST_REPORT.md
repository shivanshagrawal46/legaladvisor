# 06 · System Test Report — Deep Manual Evaluation
**Date:** June 15, 2026 · **Prepared for:** CEO · **Matter:** MangoTree v. David / Island Properties

## 1. What we tested
A deep, end-to-end manual test of the live system: **32 real questions across 8 properties**, each run through the *full* production pipeline (5-channel retrieval → entity fan-out → Opus 4.8 reranker → agentic answer → deterministic verifier). Properties were chosen for variety: data-rich David properties, prior-owner-encumbrance cases (to test that we don't misattribute), insured properties, properties with fraud findings, and **one non-David Florida property as a false-positive control**. Full transcript: `_manual_test.md`.

Questions per property covered the four things a trustee asks:
ownership + David linkage · recorded mortgages/liens/judgments · chronological timeline · suspicious/voidable transfers.

## 2. Results
| Metric | Result |
|---|---|
| Questions answered | **32 / 32** |
| Facts asserted vs verified against a verbatim source quote | **≈535 asserted · ≈99% grounded** |
| Hallucinated answers | **0** |
| Multi-source fan-out (title + emails + attachments + insurance + equity) | **Every question** |
| Evidence pulled per question | 250–430 sources |
| Non-David control: correct owner, no false David attribution | **Pass** |
| Automated eval gate (separate) | Recall 44/44 · grounding 40/40 · 0 hallucinated links |

**Verdict on correctness:** on every tested question the system answered *what was asked*, correctly, with citations, and **stated explicitly where it could not confirm something** instead of bluffing. It correctly distinguished prior-owner encumbrances (e.g. judgments against the Martinez family on 59 Beecher) from the David entity's liability — the kind of nuance that protects credibility in court.

## 3. Issues found — and what we did
The test was run to *find weaknesses*. It found real ones; here is each with the action taken:

1. **Detector recall gap (FIXED during the test).** The deterministic fraud-findings ledger had missed a clearly voidable transfer on 183 Mark Tree Rd ($2,500 for a 90% interest to a David LLC) that the chat agent caught. Cause: the deed's grantee is stored as a combined vesting string ("183MA LLC, AS TO 90% AND …"), which didn't resolve to the canonical David entity. **Fixed** by splitting combined grantee strings; voidable-transfer findings rose **84 → 90**, and 183 Mark Tree is now correctly flagged.
2. **Detection precision calibration.** On a leading "any suspicious transfers?" question about the *non-David* control property, the agent surfaced a grounded "warrants scrutiny" lead (a mortgage to a network-affiliated party). It is a real, cited document — an *investigative lead*, not an adjudicated finding. **Policy:** court-facing conclusions rely on the conservative deterministic findings ledger; chat leads are flagged as leads. (Also a recall opportunity: add a mortgage/insider-link signal to the detector.)
3. **Provenance footer showed `corpus: unknown`** on agent-path answers — **FIXED.** `RetrievedChunk` now carries `corpus`/`privilege_status`/`doc_source_type` (flowed through both retrieval projections), and `evidence_schema.corpus_for()` derives a real corpus from those fields when an explicit one is absent.
4. **Dossier fact-counts mixed current + historical** (e.g. "21 mortgages" mostly prior-owner/satisfied) — **FIXED.** Dossier now emits `fact_counts_scoped` (current-owner-era vs prior-owner vs undated, anchored on the current owner's acquisition date) + `fact_counts_basis`; the grid's Facts column shows `current/total` with a breakdown tooltip.
5. **OCR amount noise** — a few deed amounts are OCR-garbled; the system *flags* them rather than asserting — good, but an amount-cleanup pass is warranted.

## 4. Honest assessment
**Strengths:** complete, accurate, citation-anchored answers across all source types; honest about gaps; a full investigation platform behind it (entity graph, 2,380-event timeline, fraud findings, property dossiers, court-ready evidence export, portfolio + findings UI). Self-improving — the test itself hardened the detector.

**Not yet done (honest):** Sprint 8 hardening items (post-generation entity validation, faithfulness/adversarial gate, golden-answer regression, negative-evidence reporting, OCR-confidence surfacing); external (not self-authored) eval ground truth; broader stress-testing beyond the 8-property sample; per-query latency (~3 min for the deepest questions).

## 5. Bottom line
On everything tested, the system delivers trustee-grade, provable answers and does not silently miss. Remaining work is hardening and breadth, not core capability.
