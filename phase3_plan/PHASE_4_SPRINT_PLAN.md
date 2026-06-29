# Phase 4 — Forensic Intelligence & Completeness · Sprint Plan

**Mission for Phase 4:** move the system from *"answers questions accurately"* to
*"proves coverage, traces money, flags what's missing, and asks the right
questions back."* Every document fully linked, cited, custody-stamped, and
court-ready; nothing missed around any query.

Legend: `[ ]` todo · `[~]` in progress · `[x]` done & verified
Each step: **build → test → mark**.

---

## STANDARD INGESTION PIPELINE (every email AND every document runs ALL of these)
No source is "done" until it has passed every stage below. This is the same
pipeline as `chunk_embed_documents.py` / the email pipeline, applied uniformly.

1. **Ingest & dedup** — load source; dedup (`internet_message_id`/`content_hash` for email, `sha256` for docs/attachments) so nothing is re-ingested or duplicated.
2. **Extract / OCR** — text extraction; Claude-Vision OCR for scans (+ rescue pass for failed pages); structured cell-parse for Excel.
3. **Grounded fact extraction** — typed facts per source_type, each with a verbatim `source_quote` (verifier-checked); redaction-aware.
4. **Chunk** — split into retrieval chunks (current 1000/200) with a document header.
5. **Contextual summary** — per-chunk situating summary via **Sonnet 4.6** (prompt-cached) prepended before embedding.
6. **Embed** — **voyage-4-large** (1024-dim) into `email_chunks_v2` (the live vector index).
7. **Evidentiary spine** — stamp `corpus`, `privilege_status`, `evidentiary_class`, `custody{source_file, sha256, pages}`, `matter_id`, Bates (when produced).
8. **Entity linkage** — backfill `entity_ids` / `entity_refs` (people, LLCs, properties, cases) by alias/address/parcel/account; stamp `entity_sides` + `touches_david`.
9. **Downstream refresh** — fold into dossiers, events, timeline, money graph, detectors (the orchestrated refresh, X.1).
10. **Verify coverage** — completeness audit confirms the source + every attachment reached every stage.

> Wherever a sprint step says "extraction," "parser," or "ingest," it means **all 10 stages above** — extraction → chunking → contextual summary → embedding → spine → linkage → refresh → coverage-check.

---

## SPRINT 1 — Email API + "nothing missed" proof
**Goal:** live email ingestion + a provable guarantee that no email or attachment is missing.

- [ ] 1.1 Gmail OAuth (read-only) + secure token storage + auto-refresh.
- [ ] 1.2 `ingest_one_email()` — wrap the existing pipeline as ONE idempotent function: dedup (`internet_message_id` + `content_hash`) → parse → chunk → contextual summary → embed → privilege + entity tag → link.
- [ ] 1.3 **Bidirectional backfill of all emails NOT in the corpus — BOTH ends of the timeline:**
      (a) **OLDER than our current earliest** — the **`Boris_lawsuit`** Gmail folder/label, which holds earlier emails predating our earliest ingested message;
      (b) **NEWER than our current latest** — **May 26 → present**.
      Pull by Gmail **label + date range**; dedup by `internet_message_id`/`content_hash` so nothing already held is re-ingested; every message runs the full 10-stage pipeline (incl. attachments).
- [ ] 1.4 Scheduled poller (Gmail History API + stored cursor) → auto-ingest new mail; persist sync cursor durably.
- [ ] 1.5 **Email completeness audit** — reconcile source vs corpus across the FULL timeline (earliest `Boris_lawsuit` email → present), on `internet_message_id`; report + backfill any gap at either end.
- [ ] 1.6 **Attachment completeness audit** — every attachment listed vs extracted vs embedded; re-extract failures via the OCR rescue pass.
- [ ] 1.7 **Completeness certificate** per date range ("N emails, M attachments, 0 unaccounted").

## SPRINT 2 — Document onboarding + linkage
**Goal:** bring in all new document families, fully linked to existing data.

- [ ] 2.1 Canonical schema per new `source_type`: more title reports, **DA filings**, **deeds/transfers to David**, **more insurances**, **rent schedule**, **insurance Excel (to 2021)**, **IPA litigation**, **shared-with-Boris** set.
- [ ] 2.2 Structured/Excel parsers (rent schedule, insurance-to-2021) → one labelled record per property (cell-by-cell, like the equity schedule).
- [ ] 2.3 Scanned-doc OCR + grounded extraction (DA, litigation, deeds), **redaction-aware** (redacted field = withheld, never an omission/fraud signal).
- [ ] 2.4 Entity/property linkage by parcel / address / name / case-number against the canonical graph.
- [ ] 2.5 **Duplicate-property/entity scan + merge (recurring)**; harden `consolidate_properties` for cross-format parcels (SCTM vs tax-map) and street variants (Pkwy/Parkway).
- [ ] 2.6 Downstream refresh (dossiers/events/detectors) + integrity audit after each batch.

## SPRINT 3 — Financial intelligence / money graph
**Goal:** make flow-of-funds court-grade (the current weak spot).

- [ ] 3.1 **Cheque** extraction (payer, payee, amount, date, memo, cheque #); low-confidence flagged, never asserted.
- [ ] 3.2 **Bank statement** transaction extraction + account → entity mapping.
- [ ] 3.3 **2007–08 settlement sheets** — line-item extraction (price, payoffs, commissions, disbursements).
- [ ] 3.4 **Money graph + reconciliation** — link cheque ↔ bank line ↔ settlement disbursement by amount/date/party.
- [ ] 3.5 Feed money events into properties/deeds and the **voidable-transfer detectors**.
- [ ] 3.6 **Bates assignment** for discovery to be produced.

## SPRINT 4 — Proactive forensic intelligence (the "asks humans questions" upgrade)
**Goal:** the system surfaces leads and asks back when data is missing — like a human investigator.

- [ ] 4.1 **Per-property coverage engine** — what's checked vs missing (title? latest update? liens? equity? insurance? findings?).
- [ ] 4.2 **Proactive leads engine** — scans for red flags + **data-gap questions** ("David's email mentions a sale of X, but no matching deed is linked — request it?").
- [ ] 4.3 Broadened **contradiction/omission** detection (equity vs title, stated vs recorded price, disclosure omissions, transfer-before-formation).
- [ ] 4.4 **Operative-record clarity** — latest vs superseded, open vs satisfied, executed vs draft.
- [ ] 4.5 Wire into chat + a **"Leads / Open questions" panel** so the system hands questions back to the team.

## SPRINT 5 — Retrieval depth, accuracy & court-readiness
**Goal:** guarantee no query misses surrounding info; prove accuracy; finalize court output.

- [ ] 5.1 **Best-retrieval storage pass:** every chunk self-describing (doc + section + entity + dates + parcel + corpus/privilege); verify indexes; confirm neighbor/parent expansion; eval-gate 3-tier chunking; build a **per-entity completeness index** (manifest of what's linked).
- [ ] 5.2 **Independent (attorney-authored) eval set** + **one-command regression gate** (grounding %, hallucinations, missed-source, privilege-leak, duplicate-entity counts) run before every deploy.
- [ ] 5.3 **Court-export maturity** — Bates/exhibit numbers, source-quote tables, custody/SHA appendix, finding status.
- [ ] 5.4 **Human-review queues** — uncertain sides, possible duplicates, low-confidence OCR, unmatched bank transactions, ambiguous transfers.
- [ ] 5.5 **Observability dashboard** — coverage %, gaps, leads, eval scores, privilege posture.

---

## CROSS-CUTTING (run throughout, start day one)
- [ ] X.1 **Single orchestrated "refresh after ingest"** pipeline (dossiers → events → detectors → entity graph) + post-refresh integrity audit — so materialized views are never partially stale/inconsistent. *(Fixes the class of bug where `build_dossier` rebuilt retired duplicates.)*
- [ ] X.2 **Standing duplicate-entity/property audit** (recurring, not one-off) — duplicates split evidence; biggest data-quality risk as volume grows.
- [ ] X.3 **Regression gate live from the start** — until it exists, every change risks a silent regression (the clean-mode privilege leak was latent until manually tested).
- [ ] X.4 **OCR spend guard + rescue pass + low-confidence flagging** baked into every scanned-doc batch (cheques + old settlement sheets are the main cost/failure source).
- [ ] X.5 Chain of custody (SHA-256 + page) + privilege classification on EVERY new artifact.

---

## Retrieval-completeness principle (Sprint 5.1, the "no query misses info" guarantee)
- Every chunk is **self-describing** — carries its document context, section, linked entities, dates, parcel, and corpus/privilege.
- **Neighbor + parent expansion** so a fact split across a chunk boundary is never lost. *(done in Phase 3)*
- **Entity fan-out** so a query about a property pulls EVERY linked source even with no shared words. *(done)*
- **Completeness reporting** so if something isn't found, the system says so rather than silently missing it.
- **Per-entity completeness index** (new) — a stored manifest per property/entity of what's linked, so retrieval can confirm it pulled from every available source type.

---

## Known flaws this plan closes (carried from Phase 3 review)
1. Materialized-view refresh is fragile + manual → **X.1**.
2. Duplicate entities/properties are systemic (60 Central Pkwy/Parkway was one of likely several) → **2.5 / X.2**.
3. No automated regression net (privilege leak was latent) → **X.3 / 5.2**.
4. Self-authored eval only — not externally defensible → **5.2**.
5. Bates/exhibit discipline absent for produced discovery → **3.6 / 5.3**.
6. Property "side" is owner-derived but not stored (shows "—") → derive+store in **2.x**.
7. Flow-of-funds weak because cheque/bank data wasn't ingested → **Sprint 3**.

---

## Recommended order & parallelism
**1 → 2 → 3 → 4 → 5.** Completeness + clean ingestion first (can't analyze what isn't proven present), then the money graph (biggest forensic leap), then proactive intelligence, then accuracy/court-readiness hardening. **Start X.1, X.2, X.3 in parallel from day one** — they protect everything built on top.
