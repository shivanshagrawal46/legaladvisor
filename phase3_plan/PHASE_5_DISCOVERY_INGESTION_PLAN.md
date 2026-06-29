# Phase 5 — Discovery / Litigation / Financial Ingestion · AUTONOMOUS RUNBOOK

**Mission:** ingest every NON-EMAIL document from the four `E:` matter folders with
**total completeness** (no file missed), **zero duplication** (no content stored
twice), **best-possible linkage** (every source tied to property/entity/case/money),
full **OCR → grounded facts → chunk → contextual summary → embedding**, a
**money graph**, and **tests + audits after every step**. Designed to run
**unattended ~9–10h** after a single "GO".

---

## 0. LOCKED DECISIONS (do not re-ask)
1. **Folders (only these 4):** `E:\00 - IPA Litigation`, `E:\2. Shared with Boris`, `E:\DA`, `E:\Discovery_docs_mt`. Ignore all other `E:` folders/zips at root.
2. **Skip ALL emails by type, everywhere:** `.msg`, `.eml`. **Skip the `Gmail AA_Fund … Jan 16 2021.pst` (1.08 GB).** Never ingested even if the folders still physically contain them.
3. **Ignore the 4 stray `.msg` in `Received from Lynn`** (handled by rule 2).
4. **Keep DA `09. Bills` PDFs** (real invoices) — only the `.msg` in it are skipped.
5. **Dedup by EXACT content (SHA-256) only** — never filename/size. New hash ⇒ ingest. Existing hash ⇒ do NOT re-store bytes/chunks, but RECORD a new `occurrence` (path/property/category/matter). No duplicates, no misses.
6. **Privilege = ALL FOUR PRIVILEGED for now** (safest); reclassify later. Nothing from this batch is clean-mode/shareable until reclassified.
7. **Bates:** assign our own sequential, matter-prefixed (`MT-IPA-000001…`), persisted, idempotent.
8. **Money graph:** FULL reconciliation (cheque ↔ wire ↔ settlement ↔ rent ↔ property).
9. **Archives inside the 4 folders** (`Settlement sheets with email.rar`, two `MANGOTREE-*.zip`): unpack, ingest the **documents** inside (skip any emails), SHA-deduped. *(Assumed YES for completeness; flagged in P0 report — if the run finds them email-only, it skips.)*
10. **In-scope types:** `.pdf .xlsx .xls .docx .doc .csv .rtf .jpg .jpeg .png` (+ docs unpacked from archives).
11. **OCR POLICY — FRONTIER ONLY, NO EXCEPTIONS (most important):**
    - **Every page of every scanned/image document is OCR'd by a frontier vision model.**
    - **Primary: Claude Vision (Sonnet 4.6).** **Fallback (only if Claude fails/blocks): GPT-5 Vision.**
    - **NO born-digital text-layer extraction.** Even if a PDF has an embedded text layer, it is OVERRIDDEN by frontier vision OCR.
    - **NO RapidOCR / no local OCR / no "rescue" engine** anywhere in this batch.
    - **NO page skipped.** A page is not "done" until it has a frontier-vision result (Claude or GPT-5). 0 misses.
    - Native parsing applies ONLY to true structured spreadsheets (`.xlsx/.xls/.csv` cell-parse) and word docs — never to PDFs/images.
    - Per-page method must be `claude_vision` or `openai_vision` ONLY. Any `text_layer`, `ocr`(rapid), `failed`, `empty` ⇒ re-OCR until frontier; audited at Gate D and P7.4.

---

## 1. CANONICAL DESIGN

### Corpora / matter
| Folder | matter_id | corpus | privilege (now) |
|---|---|---|---|
| 00 - IPA Litigation | `ipa_litigation` | `litigation_records` | privileged |
| 2. Shared with Boris | `shared_with_boris` | `attorney_work_product` | privileged |
| DA | `da_response` | `da_production` | privileged |
| Discovery_docs_mt | `discovery_mt` | `discovery_production` | privileged |

### Folder-path parser → structured signals (the linkage engine)
Derive + store per file: **property** (normalized address → canonical `property_id`),
**doc_category** (from DA 17-bucket + Discovery sections), **year/date**, **check#(s)**
(`4621-4624`), **amount** (`$27284.50`), **party hint** (`Received from Lynn`,
`Ed Ross`, `David DeRosa`), **LLC** (`1183G,LLC`, `19DE,LLC`…).

### source_type taxonomy
`cheque`, `wire_confirmation`, `bank_statement`, `settlement_sheet`,
`service_agreement`, `closing_document`, `projection_sheet`, `deed`, `mortgage`,
`bill_invoice`, `rent_record`, `rent_schedule_xls`, `title_report`, `affidavit`,
`otsc_filing`, `litigation_filing`, `total_view_report`, `tax_record`,
`llc_record`, `property_summary_xls`, `generic_document`.

### Evidentiary spine on every chunk/doc
`corpus`, `matter_id`, `privilege_status`, `evidentiary_class`,
`custody{source_file_path, sha256, page}`, `bates`, `doc_category`,
`property_ids`, `entity_ids`, `entity_refs`, `entity_sides`, `touches_david`,
`occurrences[]` (EVERY folder location of this content).

### Money-record schema
`money_records`: type(cheque|wire|settlement_line|bill|rent), payer, payee,
amount_numeric, amount_written, date, memo, instrument_no (cheque#), bank,
account, source_sha, source_page, property_id, confidence, source_quote, bates.
`money_links`: links by (amount±, date±, party) with confidence + rationale.

### THE PIPELINE (every in-scope, NEW-content file runs ALL 10 stages)
1. **Ingest & store** bytes to GridFS; record sha256, size, path, matter.
2. **Extract / OCR (FRONTIER ONLY)** — every scanned/image page → **Claude Vision Sonnet 4.6**, fallback **GPT-5 Vision**. NO born-digital text layer, NO RapidOCR, NO skipped page. MICR/handwriting-aware for cheques; redaction-aware. Excel/CSV/Word use structured parse (never PDFs/images).
3. **Grounded facts** — typed facts per source_type, each with verifier-checked verbatim `source_quote`.
4. **Chunk** — 1000 tokens / 200 overlap, with a document header.
5. **Contextual summary** — per-chunk situating summary via Sonnet 4.6 (prompt-cached), prepended before embedding.
6. **Embed** — voyage-4-large (1024-d) into `email_chunks_v2`.
7. **Evidentiary spine** — stamp corpus/matter/privilege/evidentiary_class/custody/Bates/doc_category.
8. **Entity & property linkage** — link entity_ids/entity_refs/property_ids by alias/address/parcel/account/case#/check#; entity_sides + touches_david.
9. **Downstream refresh** — fold into dossiers/events/timeline/money-graph/detectors (single orchestrator).
10. **Coverage verify** — confirm the file reached every stage; record status.

For EXISTING-content files: skip 1–9, only append `occurrence` + merge any new path-derived linkage onto the existing record.

### STAGED EXECUTION MODEL (locked — per Shivansh's decision)
The 10 stages are executed in **batched stages across ALL 4 folders**, NOT end-to-end per file:
- **STAGE 1 = build the data layer first:** stages 1–3 + 8(path-based) for EVERY new document in all 4 folders → store bytes + **frontier OCR text** + custody + matter + path-linkage in the document store. Dedup by SHA. **Nothing is chunked yet.** End with the **OCR/STORE PASS gate** (completeness + no-dup + frontier-only OCR, 0 misses).
- **STAGE 2 = build the retrieval layer:** read the clean, deduped, OCR'd store → stages 4–6 (chunk 1000/200 → contextual summary Sonnet 4.6 → embed voyage-4-large) for everything at once.
- **STAGE 3 = intelligence + linkage:** money graph, content-based entity/property/case linkage, entity_sides, downstream refresh.
Rationale: matches our proven email/fraud pipeline; OCR (slow/expensive) is verified complete before any embedding; chunk/summary params can change without re-OCR.

---

## 2. TODO — granular, with TEST/AUDIT GATE after every phase

### P0 — Inventory, hashing & dedup map (READ-ONLY)
- [ ] P0.1 Enumerate all 4 folders; manifest row per file (path, ext, size, mtime).
- [ ] P0.2 Classify: in-scope doc / excluded-email / archive; record exclusion reasons.
- [ ] P0.3 SHA-256 every in-scope file.
- [ ] P0.4 Internal dedup: group by sha (keep ALL occurrence paths).
- [ ] P0.5 Cross-check each sha vs existing DB (attachments_v2 + email_chunks_v2 + documents.custody) → `new` vs `already_in_db`.
- [ ] P0.6 Unpack archives to staging; hash + add members to manifest (recurse); skip email members.
- [ ] P0.7 Write `_phase5_manifest.json` + **Inventory & Dedup Report**.
- [ ] **GATE A (test):** counts reconcile (in_scope + emails + archives = total walked); manifest row count == in_scope; no unreadable/zero-byte surprises; sample 20 path-parses correct.

### P1 — Schema & linkage design (code; no ingest)
- [ ] P1.1 Corpora/matter/privilege constants per folder.
- [ ] P1.2 Folder-path parser (property, category, year, date, check#, amount, party, LLC) + **unit tests** on real sample paths.
- [ ] P1.3 source_type classifier (path + filename + content sniff) + tests.
- [ ] P1.4 Address→canonical `property_id` resolver (reuse consolidate_properties; variant handling) + tests.
- [ ] P1.5 Bates allocator (persistent, idempotent) + test (re-run reuses ranges).
- [ ] P1.6 money_records / money_links schema + indexes.
- [ ] **GATE B (test):** parser/classifier/resolver unit tests all pass; Bates idempotency proven; property resolver hit-rate report on the manifest (flag unresolved for review, don't block).

### P2 — Ingestion harness (idempotent, resumable, spend-guarded)
- [ ] P2.1 `ingest_document(path)` running stages 1–10; carries matter/property/category/privilege.
- [ ] P2.2 **SHA gate:** existing ⇒ append occurrence only; new ⇒ full pipeline.
- [ ] P2.3 **Frontier-only OCR** (Claude Sonnet 4.6 → GPT-5 fallback); force-vision EVERY page, override any born-digital text layer, NO RapidOCR, NO skip; cheque/handwriting/MICR; image preproc; redaction-aware.
- [ ] P2.4 Excel/CSV structured parser → one labelled record per row/property (cell-grounded).
- [ ] P2.5 Grounded facts w/ verbatim quote (verifier-checked).
- [ ] P2.6 Chunk (1000/200) + contextual summary (Sonnet 4.6) + embed (voyage-4-large).
- [ ] P2.7 Spine + Bates + custody stamping.
- [ ] P2.8 Per-file checkpoint (resume), spend guard, low-confidence flagging, error log.
- [ ] P2.9 **Dry-run** on 25 mixed files (pdf scan, born-digital pdf, xlsx, docx, jpg cheque) → verify EVERY field populates; OCR text non-empty; embeddings 1024-d; Bates assigned.
- [ ] **GATE C (test):** dry-run 25/25 fully populated; re-run the same 25 ⇒ 0 duplicates (idempotency proven); spend guard active.

### P3 — STAGE 1: store + FRONTIER OCR + dedup + path-linkage (NO chunking yet)
Build the complete deduped OCR'd document store, folder by folder. Each new-content
file: store bytes (GridFS) → **frontier OCR every page (Claude Sonnet 4.6 → GPT-5 fallback; no born-digital, no RapidOCR, no skip)** → store extracted_text + per-page method + custody + matter + path-derived linkage. Existing sha ⇒ occurrence + linkage only.
- [ ] P3.1 **DA** store+OCR (smallest, structured): 14 properties × categories; record `(none)` buckets as gap evidence; keep `09. Bills` PDFs.
- [ ] P3.2 **DA mini-audit:** every new sha stored once; OCR frontier-only + 0 misses; path-linkage present.
- [ ] P3.3 **Shared with Boris** store+OCR: deeds/mortgages, affidavits, OTSC exhibits, title-report pages, financing evaluators, job ledgers (xls structured), rent summaries.
- [ ] P3.4 **Boris mini-audit.**
- [ ] P3.5 **IPA Litigation** store+OCR: unpack `.rar`/`.zip` (docs only); Total View Reports, county records, per-LLC folders, settlement reconciliation, tax search reports, property docs.
- [ ] P3.6 **IPA mini-audit.**
- [ ] P3.7 **Discovery_docs_mt** store+OCR (largest): service agreements, property docs, **settlement sheets (07-08)**, payments to/from MT, **checks 2014–2020**, checks/wires received (rent). Batched runs + checkpoints.
- [ ] P3.8 **Discovery mini-audit.**
- [ ] **GATE D — OCR/STORE PASS (HARD GATE, before any chunking):** every in-scope manifest sha is stored OR already-in-DB with occurrence (0 missed); each content stored once (no-dup); **EVERY page method ∈ {claude_vision, openai_vision}, 0 text_layer/rapid/failed/empty/skipped**; path-linkage populated. Must PASS before Stage 2.

### P3B — STAGE 2: chunk + contextual summary + embed (all folders, batch)
Reads only the clean, deduped, OCR'd store from Stage 1.
- [ ] P3B.1 Chunk every new document (1000 tokens / 200 overlap) with document header.
- [ ] P3B.2 Contextual summary per chunk (Sonnet 4.6, prompt-cached).
- [ ] P3B.3 Embed (voyage-4-large, 1024-d) into `email_chunks_v2`; delete-then-insert per sha (idempotent).
- [ ] P3B.4 Stamp evidentiary spine + Bates + custody on chunks.
- [ ] **GATE D2 (test):** every stored doc has chunks; chunk_index contiguous; total_chunks consistent; all embeddings 1024-d; 0 duplicate chunks; re-run = 0 new dupes.

### P4 — Financial money graph (full reconciliation)
- [ ] P4.1 Cheque extraction → money_records (payer/payee/amount×2/date/memo/cheque#/bank); folder check# cross-check.
- [ ] P4.2 Wire + rent-wire extraction (amounts cross-checked vs folder-name amounts).
- [ ] P4.3 Settlement-sheet line items (price, payoffs, commissions, disbursements).
- [ ] P4.4 Bank/payment-ledger extraction (Payments to/from MangoTree).
- [ ] P4.5 Reconciliation engine: cheque ↔ wire ↔ settlement ↔ rent ↔ property by amount/date/party; confidence-scored; unmatched → review queue.
- [ ] P4.6 Feed money events into properties/deeds + voidable-transfer detectors.
- [ ] **GATE E (test):** spot-check 30 cheques: extracted amount == folder/amount where present; reconciliation totals balance; low-confidence flagged not asserted; 0 fabricated amounts (every record has a source_quote).

### P5 — Linkage & enrichment ("nothing hides")
- [ ] P5.1 Property linkage for every chunk (path + content; reconcile conflicts).
- [ ] P5.2 Entity linkage (people, LLCs, banks, cases) by alias/address/parcel/account/case#.
- [ ] P5.3 entity_sides + touches_david; authority scores by source_type.
- [ ] P5.4 Case/matter linkage (OTSC, Brian Schuman, lawsuit papers → case nodes).
- [ ] P5.5 Cross-source linkage: same property across DA/Boris/IPA/Discovery joined into one timeline.
- [ ] P5.6 Single orchestrated downstream refresh (dossiers→events→timeline→detectors) + post-refresh integrity audit.
- [ ] **GATE F (test):** entity/property link-rate report; 0 chunks with no matter/corpus; duplicate-entity/property audit (X.2) clean or queued; refresh did not rebuild retired duplicates.

### P6 — Retrieval depth & completeness
- [ ] P6.1 Verify every new chunk self-describing (doc+section+entity+dates+parcel+corpus/privilege).
- [ ] P6.2 Per-property completeness manifest (present vs missing doc types, incl. DA `(none)` gaps).
- [ ] P6.3 Confirm neighbor/parent expansion + entity fan-out reach new sources.
- [ ] P6.4 Index checks (corpus, privilege, matter, property_id, source_type, bates, sha256).
- [ ] P6.5 Retrieval smoke eval: sample questions per folder (e.g., "checks to Carucci Renovations", "227 West Neck settlement disbursements", "Boris affidavit exhibits") return grounded, cited, correct-privilege results.
- [ ] **GATE G (test):** smoke-eval answers grounded + cited; privilege posture correct (no privileged leak to clean mode).

### P7 — Final verification & PASS CERTIFICATE
- [ ] P7.1 **Completeness:** every in-scope manifest sha is stored OR confirmed-already-in-DB with a recorded occurrence — **0 missed**.
- [ ] P7.2 **No-dup:** each content sha stored exactly once; occurrences ≥ physical copies; 0 duplicate chunks.
- [ ] P7.3 **Linkage:** every chunk has matter/corpus/privilege/(property or explained); 0 orphans; contiguous chunk_index; consistent total_chunks; valid 1024-d embeddings.
- [ ] P7.4 **OCR (frontier-only proof):** EVERY page method ∈ {`claude_vision`, `openai_vision`}; **0** `text_layer` / `ocr`(rapid) / `failed` / `empty`; 0 skipped pages; method tally + per-doc page coverage.
- [ ] P7.5 **Money:** reconciliation totals + unmatched-queue report.
- [ ] P7.6 **Privilege:** 0 privileged chunks clean-mode visible.
- [ ] P7.7 **Bates:** contiguous, unique, persisted.
- [ ] P7.8 Emit **PHASE-5 PASS CERTIFICATE** with all counts + a written run report (what was ingested, deduped, linked, money-reconciled, anything queued for human review).

### X — Cross-cutting (throughout, autonomous)
- [ ] X.1 Single orchestrated refresh after each batch (no partial-stale views).
- [ ] X.2 Standing duplicate-property/entity audit.
- [ ] X.3 Resumable checkpoints + spend guard on every batch (cost ceiling configurable).
- [ ] X.4 Chain of custody (sha + page + path) + privilege on EVERY artifact.
- [ ] X.5 Idempotency everywhere: re-running any step never duplicates or loses data.
- [ ] X.6 Structured run log + per-phase report files; on any hard error, checkpoint and continue other files, collect failures into a `_phase5_failures.json` for review (never silently drop).

---

## 3. AUTONOMOUS EXECUTION ORDER (when you say GO)
P0 → GATE A → P1 → GATE B → P2 → GATE C →
**STAGE 1:** P3 store+frontier-OCR+dedup (DA→Boris→IPA→Discovery, mini-audit each) → **GATE D = OCR/STORE PASS (hard gate)** →
**STAGE 2:** P3B chunk + contextual summary + embed (all) → GATE D2 →
**STAGE 3:** P4 money graph → GATE E → P5 linkage → GATE F → P6 retrieval → GATE G →
P7 (PASS CERTIFICATE + run report).

**Operating rules while you sleep:**
- Never skip a file to "save time"; never dedup by name; never assert an unverified money amount.
- **OCR is frontier-only:** every scanned page through Claude Sonnet 4.6 (GPT-5 fallback); NEVER use a born-digital text layer or RapidOCR; never leave a page un-OCR'd.
- On failure: checkpoint, log to `_phase5_failures.json`, continue; surface in the morning report.
- Respect spend guard; if hit, pause that stage, keep a resume point, continue non-OCR work, report.
- Produce a per-phase report file and a final **morning summary**: counts, new vs dup, money reconciled, gaps found, anything needing your decision.

## 4. MORNING DELIVERABLE
- PHASE-5 PASS CERTIFICATE (P7) + run report.
- Per-property completeness manifest.
- Money-graph summary + unmatched-items review queue.
- `_phase5_failures.json` (if any) + recommended fixes.
