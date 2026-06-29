# CEO Report — Discovery Ingestion & Court-Ready Data Build
### Session: night of 2026-06-28 → morning 2026-06-29 (autonomous run)

## Executive summary

In one overnight run we closed three of the program's biggest gaps toward a
**court-ready** fraud-investigation system:

1. **Built the full money graph** — 12,640 grounded financial records (cheques,
   wires, settlement line-items) extracted and reconciled, each tied to a verbatim
   source quote for evidentiary defensibility.
2. **Completed the title-report corpus** — every report in the `missing title
   reports` source is now ingested, OCR'd to a frontier-only standard, de-duplicated,
   and chained into per-property version histories. **Zero files missing.**
3. **Shipped the interactive per-property graph** in the web app, so any property's
   financing, title chain, money flow, and documents are visible in one screen.

Two pre-existing data-quality issues were discovered and surfaced for a decision
(details at the end). Neither was introduced by this work; both have a costed,
ready-to-run remediation.

---

## What was delivered (business terms)

| Deliverable | Outcome | Why it matters |
|---|---|---|
| Money graph | 12,640 records, **100% with source quotes**, 90 cheque chains reconciled across documents | Traceable money movement — the backbone of the fraud narrative |
| Title reports | **111/111 files captured, 0 missing**; all versions chained | Complete chain of title per property; no evidentiary holes |
| Frontier OCR | **0 non-frontier pages** in the new title set | Defensible transcription quality (no error-prone legacy OCR) |
| De-duplication | 53 duplicate reports retired, every physical copy logged | "No content twice, every occurrence recorded" — audit integrity |
| Knowledge graph | 198 canonical properties, 57,844 chunks, 82% entity-linked | The AI reaches the right evidence for any property question |
| Web app | Interactive property-map page (financing, title chain, money, docs) | Investigators see a property's whole story in one view |

---

## Technical challenges & how we solved them

### 1. Financial data was free-text and inconsistent
**Challenge:** Cheques, wires and settlement sheets store amounts, payers and payees
in wildly varying layouts; naive parsing produces ungrounded, unprovable numbers.
**Solution:** Used a tool-use extraction model that returns structured records
*plus a verbatim `source_quote` for every record*. Result: 100% of the 12,640
records are grounded to the document text — defensible in court. Ran extraction as
3 parallel workers, then a single reconciliation pass that linked 90 cheque-number
groups appearing across multiple documents.

### 2. "Frontier-only OCR" had to survive an API credit outage
**Challenge:** Policy requires every title-report page to be transcribed by a
frontier vision model (Claude Sonnet 4.6, fallback GPT-5) — never the cheaper,
error-prone legacy OCR. Mid-run, the primary model's credits could exhaust and the
system would silently fall back to legacy OCR, violating the standard.
**Solution:** Re-engineered the OCR engine so credit exhaustion or a content-filter
block **re-routes the page (and the rest of the run) to GPT-5 vision**, never to
legacy OCR. Verified at the database level: **7,152 Claude pages + 98 GPT-5 pages,
0 legacy pages** across the 86 new title documents.

### 3. Hidden duplicate title reports across two corpora
**Challenge:** The same title report had been ingested twice — once via the title
pipeline and once inside the discovery-production document dump — creating duplicate
content in the search index (a violation of the no-duplication rule). These weren't
visible until field parsing was re-standardized.
**Solution:** Built an identity audit keyed on the report's true fields (order
number, effective dates, normalized address). It found **51 duplicate groups**.
We retired **53 redundant copies and 116 duplicate search-chunks**, kept the
authoritative version, and **recorded each retired file's provenance** on the
survivor — so nothing is double-counted, yet every physical copy is traceable.

### 4. "Same address, different spelling" matching
**Challenge:** "60 Central Parkway", "60 Central Pkwy" and "60 Central Park" must
resolve to one property; directionals ("S" vs "South") and word order vary.
**Solution:** A canonical address key (house number + normalized directionals +
first street word) drives all matching. This let us consolidate **543 property
signals into 198 canonical properties** and attach every title, insurance record
and money record to the correct single hub.

### 5. Throughput risk against a hard deadline
**Challenge:** Embedding the title corpus (contextual summary + vector for ~10k
chunks) ran single-threaded at ~8 minutes per large document — far too slow to
finish before morning.
**Solution:** Added hash-based sharding and ran **4 parallel workers**. Combined
with prompt caching (60M+ cached tokens → near-zero incremental cost), this cut the
job to ~2.5 hours and finished comfortably on time. Total OCR spend: **$83 of a
$500 guardrail.**

### 6. Stale links after consolidation
**Challenge:** Merging properties re-pointed documents to new canonical IDs, which
would leave previously-indexed search chunks pointing at deleted entities.
**Solution:** Re-ran a deterministic (no-LLM, idempotent) entity-linking pass over
**all 57,844 chunks**, re-deriving canonical links from text. 82% now link to at
least one entity, restoring retrieval accuracy.

### 7. Proving completeness, not just claiming it
**Challenge:** "No missing data" must be demonstrable.
**Solution:** A completeness manifest hashes every file in the source folder and
checks each against the database (as an own-document or a recorded duplicate).
Initial result: 109/111. We traced the 2 gaps to a provenance-logging bug in the
de-dup merge (the reports' content *was* present; only the file fingerprints weren't
recorded), backfilled them, and re-ran: **111/111, zero missing.**

---

## Operating discipline / judgment calls

- **Where accuracy and completeness conflicted, we chose court-ready accuracy and
  flagged the decision** rather than guess. Specifically, we declined to
  auto-create ~272 property entities from noisy cheque text (multi-property rows,
  OCR truncations, non-addresses) that would have polluted the legal graph —
  instead linking the 489 clean matches and staging the rest for a guided pass.
- All destructive steps (retiring duplicates, consolidating entities) were run
  **dry-run first, reviewed, then applied**, with referential safety checks
  (confirmed 0 money records / 0 events pointed at retired documents).

---

## Two decisions needed from you

**A. 101 legacy title documents contain ~230 pages of old, lower-quality OCR.**
These predate the frontier-only standard and aren't from last night's work. Their
original PDFs aren't on local disk, so we need the original title-reports source
folder to re-transcribe them (~$3–5, ~30 min). Until then, the *new* corpus is
100% frontier; this is the older tail.

**B. ~272 portfolio addresses appear in the money graph but aren't yet property
nodes** (≈4,867 financial records). We linked all clean matches; the remainder need
a 30-minute guided disambiguation pass (split multi-property rows, merge OCR
spelling variants) to link them safely. Tooling is staged.

---

## Current system snapshot

- Title documents: **330** | Title search-chunks: **13,378** | Total chunks: **57,844**
- Canonical properties: **198** | Property dossiers: **198** | Timeline events: **2,498**
- Money records: **12,640** (6,153 property-linked) | Reconciled cheque chains: **90**
- New title OCR spend: **$83 / $500** budget | Files missing: **0 / 111**

**Bottom line:** the money graph and the title-report chain of custody are complete
and defensible, the AI can retrieve property-level evidence end-to-end, and
investigators have a single-screen property view. Two legacy clean-up items await
your go-ahead.
