# Morning Report — 2026-06-29 (overnight autonomous run)

Everything you asked for is done and verified. Two pre-existing issues were
surfaced that need your input (neither is from last night's work). Details below.

---

## 1. Money graph (Phase-5 P4) — COMPLETE

| Metric | Value |
|---|---|
| Money records extracted | **12,640** |
| Grounded (carry `source_quote`) | **12,640 (100%)** |
| With payer / payee / date | 12,640 / 12,640 / 12,640 |
| Cheque-number groups reconciled across docs | **90** |
| Distinct reconciled amounts | 3,904 |
| Linked to a canonical property | **6,153 (49%)** |
| Money-bearing docs processed | 1,237 |

- Ran as 3 parallel shards, then a single reconciliation pass.
- `amount_value` is numeric → per-property `money_total` sums correctly (verified:
  91 West Shore Road shows **$3.21M** across 28 records).

## 2. Missing title reports (`E:\missing title reports` ONLY) — COMPLETE

| Metric | Value |
|---|---|
| PDFs in folder | 111 |
| **Files represented in DB** | **111 / 111 (0 missing)** |
| New title docs ingested | 86 (78 new + 8 resumed) |
| **Non-frontier pages in the 86 docs** | **0** (7,152 Claude Sonnet-4.6 + 98 GPT-5 pages) |
| OCR spend | $83.19 / $500 budget |

- **Frontier-only guarantee met**: every page of every new title report was OCR'd by
  Claude Vision Sonnet 4.6, falling back to GPT-5 only (never RapidOCR). The
  credit-exhaustion → GPT-5 routing fix held all night.
- Address normalization applied (`60 central parkway` == `pkwy` == `park`).
- **All versions linked**: 257 title docs sit in multi-version chains
  (original → update → 2026 update). **0 update-only properties** (every titled
  property has its original full search or an embedded original).
- 138 / 198 canonical properties now carry ≥1 title report.

### Zero-duplication enforcement (your #1 rule)
- A reparse-driven identity audit found **51 content-duplicate groups** — title
  reports that existed in *both* the dedicated title corpus *and* the Phase-5
  discovery corpus (`shared_with Boris` / `ipa_litigation`).
- **Retired 53 duplicate copies + deleted 116 duplicate chunks**, keeping the
  canonical title-pipeline version and **recording every retired file's
  provenance** on the survivor. No content stored twice; every physical
  occurrence recorded.
- The 2 files the first pass missed (`31 Fort Hill Dr_Update Search.pdf`,
  `83 S Ann Drive_Update Search 2026.pdf`) were confirmed duplicates whose content
  is already in the DB; their provenance has now been backfilled → **0 missing**.

## 3. Knowledge graph + retrieval — COMPLETE

- `consolidate_properties`: **198 canonical properties**, 401 docs re-pointed,
  117 stale entities removed.
- `backfill_chunk_entities`: **57,844 chunks processed, 47,436 (82%) linked** to
  ≥1 canonical entity.
- Authority floor wired into hybrid retrieval (`temporal._authority_score` now
  honours `doc_authority_score`; title reports = 1.15).
- Dossiers rebuilt: **198**; events rebuilt: **2,498**
  (mortgage 222, lien 567, judgment 246, lis_pendens 371, assignment 268,
  conveyance 451, title_search 324, …).
- Title chunks in the live vector corpus: **13,378** (1000/200, Sonnet-4.6
  contextual summaries, voyage-4-large embeddings).

## 4. Frontend per-property graph — COMPLETE

- Backend endpoint `GET /api/properties/{id}/graph` + `property_graph()` builder.
- New interactive `PropertyGraphView.jsx` ("◆ Property map" tab, default) with
  financing-by-year, activity map, title-version chain, money graph, and
  all-documents views. `recharts` installed, production build passed.
- **Live payload smoke-test passed** (91 West Shore Road: 7 titles, 2 mortgages,
  28 money records, $3.21M, 10 docs, 52 events).
- ⚠️ Please **glance at the live UI** once — I verified the API + build, but a human
  should eyeball the rendering.

---

## TWO ITEMS THAT NEED YOUR INPUT (pre-existing, not from last night)

### A. 101 legacy title docs contain ~230 RapidOCR pages
- These are OLD title docs (from earlier title runs, **not** the missing-title
  folder) that predate the frontier-only fix. They have a mix of Claude pages +
  ~230 RapidOCR pages.
- I could not re-OCR them autonomously: their source PDFs aren't on disk, not in
  GridFS, and only 1/101 is in `attachments_v2`. The stored provenance paths are
  **relative** (`2021\...pdf`, `2022\...`) under an original title-reports root I
  don't have.
- **What I need:** point me at the original title-reports source folder (the one
  with `2021/ 2022/ 2024/ 2025/` subfolders) and I'll re-OCR those 230 pages with
  frontier vision (~$3–5, ~30 min) so 100% of title reports are frontier.

### B. ~272 portfolio addresses in the money graph aren't entity nodes yet
- The money graph references ~272 property addresses (4,867 cheque/line-item
  records) that don't exist as property entities (Newark/LI rehab portfolio:
  321 S Orange, 761 S 20th, 480/482 S 16th, 283 S 11th, …).
- I linked the 489 that matched existing properties, but I **deliberately did not
  auto-create** the 272 — the cheque `property`/`memo` text is noisy: multi-property
  rows ("321 S Orange, 283 S11th, 880 S 20th…"), OCR truncations ("321 south ora"),
  and non-addresses ("482 Fridge and stove"). Auto-creating would inject malformed
  / duplicate entities into a court-ready legal graph.
- **What I need:** ~30 min with you (or a green light) to do a guided pass —
  split multi-property rows, merge truncations, create clean entities, link the
  4,867 records. Tooling is staged (`_money_create_props.py`).

---

## Current database snapshot
- documents.title_report: **330** | title chunks: **13,378** | total chunks: **57,844**
- property entities: **198** | dossiers: **198** | events: **2,498** | relationships: 1,014
- money_records: **12,640** (6,153 property-linked)

## Suggested first 10 minutes when you wake
1. Open a property's **◆ Property map** tab in the UI and confirm it looks right.
2. Tell me the original title-reports source folder → I finish item A.
3. Green-light item B → I link the remaining ~4,867 money records to properties.
