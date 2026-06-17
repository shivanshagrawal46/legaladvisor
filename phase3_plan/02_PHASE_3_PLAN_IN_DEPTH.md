# 02 · Phase 3 — The World-Class Multi-Source Legal Evidence Platform (Plan)

**Project:** Mango Tree Legal RAG — Fraud Investigation Evidence Platform
**Status of this document:** Living plan. The detailed "how" of Phase 3.
**Assumption:** I (the AI) build; you (Rakesh Sir's team) review. Estimates are in working days, grouped into sprints.

> **Goal of Phase 3:** Take the strong single-corpus engine from Phase 2 and turn it into a **multi-source, fully-linked, privilege-aware, timeline-correct, contradiction-detecting evidence platform** that can hand a trustee complete, accurate, provable information about any property, person, or amount in the David matter.

---

## 1 · The data we are adding in Phase 3

| # | Source | What it is | Corpus | Privilege |
|---|---|---|---|---|
| 1 | **AA_Fund folder** | Rakesh Sir's email conversation with **David (fraudster) + David's team** + attachments (~6,000+ emails) | `fraud_communications` | `adverse_party` (admissions) |
| 2 | **Title reports** | Original ("full search") title reports of David's properties **+ update/continuation search** for some | `property_records` | `public_record` / `third_party` |
| 3 | **Insurance evidence** | Insurance coverage David took on some properties | `insurance_records` | `third_party` |
| 4 | **Equity Excel** | Spreadsheet of David's equity in properties | `financial_records` | `third_party` |
| 5 | **New LLC docs** | LLC formation / corporate records | `corporate_records` | `public_record` |
| 6 | **Litigation updates** | Court / DA filings, case status | `court_records` | `public_record` |
| — | (existing) Lawyer correspondence | Already ingested | `legal_correspondence` | `privileged` |

**"Full search vs update search"** = title-report versioning. The original commitment is the full search; later continuation/update searches supersede it. We keep **both** and surface the **latest/operative** one while preserving the lineage (see supersession, Sprint 4).

---

## 2 · The two-corpus reality + privilege model

- **Corpus A (lawyer emails)** = attorney–client privileged + work product. **Must not leak** outside our circle.
- **Corpus B (David)** = adverse-party communications = **admissions** under FRE 801(d)(2). Our most directly usable evidence.

**Handling model (confirmed direction):**
- Tag every doc with `corpus` + `privilege_status` (default by corpus).
- **Two retrieval modes:**
  - **Analysis mode** (internal): agent sees everything; privileged passages clearly labeled.
  - **Clean mode**: privileged chunks excluded **at the retrieval layer** — structurally impossible to leak into a shareable/trustee output.
- Audience: outputs go to us + our legal team + retained experts (mostly inside the privilege circle); Clean mode protects the testifying-expert edge.
- Defer auto privilege log + export redaction until a real production obligation appears.

*(Open: confirm experts are retained through counsel; confirm privilege certainty per email. Tracked in 03_VISION.)*

---

## 3 · New data model

### 3.1 New collection: `documents/` (one row per unique file)
Structured facts about each file as a whole — the missing layer.

Key fields:
- Identity: `sha256`, `matter_id`, `filename`, `extension`, `page_count`
- **Classification:** `source_type`, `instrument_subtype`, `issuing_authority`, `is_signed`, `is_recorded`, `is_notarized`, `language`, `jurisdiction`
- **Evidentiary layer (NEW):** `corpus`, `privilege_status`, `evidentiary_class`, `custody{custodian, source_file, sha256, ingested_at, ingest_run_id}`, `bates_range`
- **Temporal:** `dates{document_date, effective_date, recording_date, filing_date, execution_date, event_date_range}`
- **Parties:** `[{role, name_raw, entity_id}]`
- **Anchors:** `property_ids[]`, `case_ids[]`, `llc_ids[]`, `instrument_numbers[]`
- **Facts:** `monetary_facts[{label, amount, currency, page}]`
- **Summaries:** `summary_one_line`, `summary_paragraph`
- **Structure:** `sections[{id, title, page_start, page_end, chunk_indices}]`
- **Ranking:** `authority_score`
- **Quality:** `quality{has_document_date, has_at_least_one_entity, extraction_confidence, classification_confidence, needs_review, review_reasons}`

### 3.2 Diffs to existing `email_chunks_v2` (chunks)
Add (existing fields untouched): `matter_id`, `document_id`, `section_id`, `corpus`, `privilege_status`, `entity_refs{people,properties,llcs,cases,banks}`, `primary_property_id`, `primary_person_id`, `primary_llc_id`, `doc_authority_score`, `doc_summary_one_line`, `doc_source_type`, `doc_date`, and **3-tier context** (`context_doc`, `context_section`, `context_chunk`). Embedded `text` becomes `[Doc] … [Section] … [Chunk] … + header + body`.

### 3.3 New collection: `entities/` (kind = person | property | case | llc | bank)
Canonical IDs + aliases. People keyed on email; properties on parcel ID + normalized address; LLCs on state filing number / EIN; cases on docket number.

### 3.4 New collection: `relationships/` (flat edge table)
Typed, dated, sourced edges: `GRANTOR_OF`, `GRANTEE_OF`, `OWNS`, `MEMBER_OF`, `BORROWER_OF`, `HAS_LIEN`, `HAS_MORTGAGE`, `HAS_INSURANCE`, `ABOUT_PROPERTY`, `REFERENCES`, `SATISFIES`, `ATTACHED_TO`, `FILED_IN`, `SENT_EMAIL`. Each edge carries `as_of` (+ optional `until`), `source_chunk_id`, `source_doc_id`, `confidence`.

### 3.5 Source taxonomy (source_type enum)
Email · property/title (title_report, deed, mortgage, satisfaction, lien, lis_pendens) · insurance (binder, policy, claim) · court (court_filing, judgment, court_order, da_filing, indictment) · corporate (llc_formation, operating_agreement, certificate_of_good_standing) · financial (bank_record, wire_confirmation, tax_record, closing_statement, equity_schedule) · general (contract, amendment, correspondence, spreadsheet, draft, attorney_notes).

### 3.6 New collections: `events/` and `findings/` (v11)
- **`events/`** — every **dated fact** becomes one event row: deed recorded, policy
  effective/cancelled, judgment entered, email sent, LLC formed, transfer made.
  Fields: `{event_type, date, date_kind, entity_ids[], property_id, doc_id,
  source_quote, amount?}`. Written at ingestion + by the Sprint-4 detectors.
  *Why:* in a fraud case the **sequence is the story** — "what did David do in
  the 60 days after the judgment?" becomes an indexed query, not an LLM
  reasoning exercise. The Sprint-5 timeline builder READS this; it is data,
  not just an output format.
- **`findings/`** — the investigation's **persistent memory**: every
  contradiction, anachronism, conveyance flag, or agent discovery stored with
  its evidence chain (`source_doc_ids`, quotes), confidence, and a human
  **confirmed / rejected / pending** status. Confirmed findings feed retrieval
  ("known issues for this property"), the property dossier, and the eval set.
  *Why:* otherwise every discovery lives and dies inside one chat answer —
  this is the difference between a search tool and an investigation platform
  that gets smarter every week.

### 3.7 Authority scores (config-driven, feed the reranker)
court_order/judgment 1.25 > recorded deed/mortgage/satisfaction 1.20 > lien/lis_pendens/da_filing 1.18 > title_report/closing 1.15 > insurance 1.10 > executed contract/operating_agreement 1.08 > bank/wire/tax 1.06 > llc_formation 1.05 > email_attachment 1.00 > email_body 0.95 > **draft/attorney_notes 0.85**.
> **Note on drafts:** low authority ≠ discard. Drafts are preserved and the **difference vs the executed version is surfaced** (drafting history is "especially revealing" evidence of intent).

---

## 4 · The ingestion pipeline (Phases 0–9, one runner per source family)

```
0 INTAKE          file walk + SHA-256 dedup (idempotent) + ingest_run row
1 EXTRACTION      reuse extractor.py + claude_ocr.py (Sonnet 4.6 Vision)
2 CLASSIFICATION  1 Sonnet call → source_type, subtype, flags, corpus default
3 METADATA        per-source-type JSON schema (tool-use) → dates, parties,
                  monetary_facts, instrument_numbers, sections, summaries
                  → write documents/ row
4 ENTITY RES.     normalize + resolve people/properties/LLCs/cases → canonical IDs
5 HIER. CHUNK     reuse chunker.py @ 1000/200, scoped to sections for long docs
6 3-TIER CONTEXT  context_doc (free) + context_section + context_chunk (cached)
7 EMBED           VoyageEmbedder (voyage-4-large; optional voyage-law-2 in S6)
8 WRITE-OUT       documents/ + chunks/ + relationships/ + entity counters (txn)
9 QUALITY GATES   needs_review if missing date/entity/low confidence; obs metrics
```
Idempotent on SHA, resumable per phase, dollar-guarded like the OCR pass.

---

## 5 · Retrieval changes (entity-anchored fan-out)

- **Silent query understanding:** extract entities + facts from the natural question (no source-type words required from the user).
- **Resolve** mentions → canonical IDs.
- **Fan-out:** one query across `entity_refs.*` unions **every linked source type** (David email + title + insurance + deed + wire + LLC + court).
- **Rank:** hybrid (existing) × `doc_authority_score` × recency × entity-match bonus, then Voyage rerank.
- **New agent tools:** `search_entity_cluster` (default), `list_documents_for_entity`, `graph_query` (multi-hop), `compare_documents`. Old tools demoted to fallbacks.
- **Agent prompt rewrite:** route by entity, synthesize across sources, respect authority hierarchy, respect privilege mode.

---

## 6 · The sprints (detailed tasks · time · deliverable)

### Sprint 0 — Foundations & plumbing · **2–3 days**
- Wire conversation memory into v3 agent (fix the biggest UX bug).
- Add `minScore` floor to vector search.
- Lift live `1000/200` + `voyage-4-large` into `Settings` (kill drift).
- Real Anthropic streaming on the agent planner.
- Add `corpus` + `privilege_status` + `custody` + `evidentiary_class` schema fields + indexes (shape only, no data).
- **Deliverable:** faster multi-turn agent + metadata spine ready for evidence.

### Sprint 1 — Ingest the David corpus (`.eml`) · **4–6 days**
- Build `ingest_eml_folder.py` mirroring the PST path (reuse library + rescue extractor for malformed mail).
- Tag `corpus="fraud_communications"`, `privilege_status="adverse_party"`, `evidentiary_class="party_admission"`.
- Rebuild conversation threads (Message-ID / In-Reply-To / References; subject+participant+time fallback).
- Run through existing pipeline (OCR → 1000/200 chunk → context → embed → `email_chunks_v2`).
- **Cross-corpus dedup**: shared attachments collapse to one chunk-set; `occurrences[]` spans both corpora.
- **Deliverable:** all ~6,000 David emails + attachments searchable, tagged as admissions, deduped. **First real value.**

### Sprint 2 — Documents layer + property/insurance/LLC/DA/equity ingestion · **5–7 days**
- New `documents/` collection + indexes.
- `ingest_documents.py` (Phases 0–3) reusing OCR/chunker/embedder.
- 7 per-source-type extraction schemas (title report, insurance, deed/mortgage, LLC, DA/court, bank, equity/spreadsheet + correspondence).
- Ingest title reports (full + update search), insurance, equity Excel, LLC, litigation updates.
- Backfill `documents/` rows for the existing + David corpora.
- **Lawyer-corpus tag backfill** — stamp the pre-Phase-3 PST emails + attachments with `corpus=legal_correspondence`, `privilege_status=privileged`, `evidentiary_class=privileged_work_product`, custody block. Makes both corpora symmetric (David already tagged at ingest). Idempotent.
- **Chunk-level corpus/privilege tagging** — flow `corpus` + `privilege_status` (+ `matter_id`) from each email/attachment ONTO its `email_chunks_v2` chunks (cheap `update_many`, no re-embed). Enables corpus-filtered retrieval and the Clean-mode privilege guard to operate directly at the chunk layer.
- **Redaction-aware extraction** — instruct Claude Vision OCR to emit explicit tags for redaction boxes (`[REDACTED]`, `[REDACTED_NAME]`, `[REDACTED_AMOUNT]`) + detect textual patterns (`XXXX`, solid blocks); set `has_redactions` + redacted-field list on the document. (Matters mainly for court/DA/third-party docs; confirm real volume once documents arrive — don't gold-plate.)
- **Deliverable:** every source type queryable with structured metadata; **"update search" / latest-version works.**

### Sprint 3 — Entity resolution + linkage graph + fan-out · **6–8 days**
- **Execution order (v11, learned from the title/insurance/equity linkage work):** ① **canonical PROPERTY consolidation first** — one node per real property keyed by `parcel-digits ∪ address-core`, merging title-created/insurance-created/equity-implied nodes, must-not-link parcel firewall, review queue for ambiguous merges; every document re-attaches to canonicals. ② people/LLC resolution. ③ relationships/fan-out. ④ **chunk + embed only AFTER consolidation** so chunks carry canonical `entity_refs` from day one (embedding first would bake un-linked metadata into the index).
- `entities/` + `relationships/` collections.
- Resolution pipeline (blocking → multi-signal scoring → thresholds → review queue → union-find), idempotent.
- **Coreference pass** (resolve "he", "the property", "the Seller", "Id.").
- **Redaction-aware resolution** — a redacted span = "unknown," NOT "absent"; never sever a cross-document link just because the linking field is blacked out (keep if other signals support it).
- Backfill entity refs across all three corpora.
- New tools `search_entity_cluster` + `graph_query`; agent prompt rewrite.
- **Alias & legal-synonym query expansion ⭐ (recall lever)** — before searching, expand the query with every known alias of the resolved entity (David → `david@aafund.com`, "Dave", "the Seller", "Managing Member") AND legal synonyms (lien↔encumbrance, grantor↔seller, mortgage↔deed of trust). Makes the lexical + semantic channels catch every variant phrasing; uses the entity graph we're already building. Clean, high-recall, low complexity.
- **Bitemporal edges** (`as_of` / `until`) so "who owned this on the date of the lie?" works.
- **Deliverable:** "anything on 520 E 81st?" → David emails + title + insurance + deed + wires + LLC + court filing in one synthesized, cited answer.

### Sprint 4 — Authority ranking + contradiction detection + supersession · **4–6 days**
- Per-source-type authority into the reranker.
- **Contradiction detection ⭐** — fact clusters per (predicate + entity); flag numeric/date/identity/status/omission divergences; mark operative side + admissions.
- **Anachronism / backdating check ⭐** — a temporal-impossibility branch of contradiction detection (uses data we already have: entity formation/incorporation dates + document/execution dates). If a document is signed on behalf of an LLC *before* that LLC legally existed (e.g., signed Nov 2023 but incorporated Feb 2024), flag a **Critical Corporate Anachronism** — exposes fabricated/backdated documents automatically. (One comparison rule inside the existing engine; no new collection or pipeline.)
- **Redaction-aware detection** — a redacted field is a distinct state ("withheld by redaction"), NOT "omitted by David". Redacted fields are excluded from omission AND contradiction flags → prevents false-positive fraud flags (e.g., a DA-redacted SSN must never read as "David hid this").
- **Supersession lineage** — title reports & re-issued docs: surface latest, preserve history, show draft↔executed differences.
- **Property dossier (materialized view)** — per property entity, precompute & cache the standard facts (latest title status, insurance in force, liens, mortgages, equity, latest deed, contradictions) at ingestion and refresh on new docs. Powers both fast single-property chat answers AND the instant-loading portfolio grid (Sprint 8) — so the grid never needs the live agent.
- **Fraudulent-conveyance rule pack ⭐ (the asset-recovery brain, v11)** — a deterministic UFTA / NY-DCL rule layer over the graph. For every property transfer in a deed chain, test: (a) **transfer date vs. when our claim/judgment arose** (litigation timeline), (b) **grantee is an insider** (David-network entity), (c) **consideration vs. market value** (equity schedule), (d) owner left insolvent/undercapitalized where inferable. Any hit → a **voidable-transfer candidate** finding with full citations (deed quote + judgment date + insider proof + value gap). *Why:* contradiction/anachronism detection finds lies; THIS finds the trustee's actual clawback weapon — and every ingredient already exists in structured form (we've already seen "conveyed after our judgment" in the equity sheet and the IPA→520E transfer). Pure rules over existing data — no new infrastructure, no LLM in the loop for the rule test itself.
- **Persistent findings ledger (v11)** — all detector output (contradictions, anachronisms, conveyance flags) writes to `findings/` (§3.6) with evidence chains + human confirm/reject review queue; from Sprint 5 onward the agent's ad-hoc discoveries persist there too. Confirmed findings are surfaced automatically on every future query touching the same entity.
- **Deliverable:** system actively surfaces fraud signals, not just documents — and **remembers** them.

### Sprint 5 — Legal work-product features · **5–7 days**
- **Event store first (v11):** populate `events/` (§3.6) at ingestion + from the Sprint-4 detectors — every dated fact (deed recorded, policy effective/cancelled, judgment entered, email sent, LLC formed, transfer) is one indexed event row with source quote. Sequence questions ("what happened in the 60 days after the judgment?") become simple date-range queries over `events/` — the LLM is removed from the most error-sensitive step.
- **Timeline / chronology builder ⭐** (cited, per-property or whole-case; flow-of-funds friendly) — **reads from `events/`**, the LLM only narrates an already-correct, already-cited sequence.
- **Evidence-packet export ⭐** (Bates/exhibit-cited bundles a trustee/expert can use; underlying data identified per FRCP 26).
- Privilege-aware answering (two modes) + optional auto privilege log.
- **Mode-scoped cache & memory isolation** — Clean-mode sessions never reuse prompt caches, conversation memory, or transient state from an Analysis-mode session (cache keys include mode; Clean sessions start fresh). Closes the implicit-leakage path so a privileged strategy can never inflect a shareable answer. (One discipline rule — NOT separate infra/"cryptographic" isolation, which is unnecessary for our audience.)
- Confidence + provenance footer on every answer.
- **Deliverable:** outputs a trustee or lawyer can put straight into a filing.

### Sprint 6 — Eval, observability, hardening · **4–6 days**
- Private eval set (~50 queries → expected sources) → nightly Recall@10 / MRR / Faithfulness. **Proves** world-class accuracy on this corpus.
- Ingest/admin dashboard ($ spent, needs-review queue, entity-merge queue, classifier confidence).
- **Deliverable:** measured, defensible, world-class accuracy.

### Sprint 7 — Retrieval & precision (LOCKED decisions, no experiments) · **4–6 days**
> **Decision rationale (Jun 2026):** the system will be tested/judged by a third party. When trust is on the line we choose **proven + explainable + reliable** over **frontier + maybe-better-but-risky**. No A/B experiments in this sprint — every component is one we can defend under scrutiny.
- **Reranker → LLM-as-reranker** (NOT ColBERT): keep Voyage `rerank-2.5` as base + add an Opus/Sonnet final scoring pass on the top ~40. *Why:* zero new infra, fully explainable ranking; ColBERT's separate token-vector index = more failure points with no benefit at our scale.
- **Chunking → 3-tier contextual chunking** (NOT late chunking): `[Doc] + [Section] + [Chunk]` prefixes — proven, transparent, inspectable. Late chunking is research-frontier and depends on unverified embedding-model internals; rejected for trust reasons.
- **Embeddings → KEEP `voyage-4-large`** (do NOT switch to `voyage-law-2`): law-2 is legal-tuned but *older*; its "+6–10%" is vs general models of its era, **not** vs voyage-4-large (newer flagship). Switching forces a full re-embed and could regress. Changing the foundation on a guess is the highest-risk move to trust → rejected.
- **Query decomposition** (Hebbia ISD style) — split complex multi-part questions, retrieve per sub-question, synthesize.
- **Sufficiency / self-reflection check** — agent asks "what would make this incomplete? have I checked every linked source?" before answering. (Best guard against missing info.)
- **Robust numeric/date normalization** — money/date parsing so "$1.45M" / "1,450,000.00" reconcile (sharpens contradiction detection).
- **Recall-tuned candidate pools** — cast a WIDE net at the retrieval stage (generous `numCandidates` / top-k before rerank) and keep the `minScore` floor LOW; let the reranker handle precision. Principle: **cast wide, rerank hard** — high recall AND high precision, not a trade.
- **Evidence-pack sizing tuned by eval (NOT inflated blindly)** — today ~50–70 reranked chunks reach the model, which is already generous. Do **not** flood the context to 150+: "lost in the middle" *reduces* fact accuracy and raises cost. Let the Sprint 6 eval set find the optimal count; rely on reranking + interleaving for quality and on fan-out + agent iteration for completeness — not on a giant flat dump.
- All changes validated against the Sprint 6 eval set → the tester sees **measured proof**, not claims.
- **Deliverable:** higher precision using only reliable, explainable components — nothing experimental that could embarrass us under scrutiny.

### Sprint 8 — Hardening, completeness & portfolio UX · **6–8 days**
- **Post-generation entity validation** — the Claude-compatible equivalent of KG-Trie / constrained decoding. (True constrained decoding needs self-hosted open-weights models; the Anthropic API can't do logit-level control. So instead: after Opus answers, validate every person/property/LLC name against the canonical entity list; flag/correct anything not in the graph → zero invented entities.)
- **Faithfulness gate + bounded adversarial loop ⭐** — an answer failing grounding does not ship; it's flagged. On top of grounding, a **Defense-Critic** pass runs the answer + citations against a "you are David's defense attorney — find the gap" prompt (*is this executed or just a draft? effective date vs recording date? is the identity match speculative?*). Flow:
  - Critic finds a **closeable** gap → **exactly ONE bounded re-plan**: the agent re-retrieves to close that specific gap → re-check.
  - Gap closed → ship. Gap remains → **downgrade confidence + explicitly flag the vulnerability**.
  - **Sequential, not parallel** (the critique depends on the answer, so parallel adds nothing). **One re-plan attempt only** — captures ~90% of a full red-team loop's value while staying bounded/predictable/explainable; reuses the agent's existing retrieval + budget + the verifier's retry pattern (no separate critic-agent subsystem, no unbounded ping-pong).
  - Upgrades the gate from "is each fact grounded?" to "would this survive cross-examination?"
- **Golden-answer regression tests** — lock known-correct answers so no future change silently regresses them.
- **Negative-evidence / completeness reporting ⭐** — system states what it does NOT have ("no title report on file for Property X; no 2022 insurance found"). For a trustee, knowing gaps matters as much as knowing facts.
- **OCR-confidence surfacing** — facts resting on low-confidence OCR pages are marked, never silently hardened.
- **Full audit / provenance export** — one click yields the complete chain (source file → SHA → page → quote) for any fact, court-ready.
- **Spreadsheet-grid UI** (Hebbia-Matrix style) — rows = properties, columns = questions, cells = cited answers; portfolio-wide comparison.
  - **CRITICAL execution rule (do NOT power cells with the live v3 ReAct agent):** the grid is a **cached materialized view + async map-reduce**, never a real-time agent loop. Naive wiring (rows × columns × full agent) = millions of tokens, rate-limit 429s, timeouts.
    - **Standard columns** (latest title status, insurance in force, lien present, equity amount, open mortgage) = **instant reads** of the precomputed **property dossier** (see Sprint 4) — zero live LLM.
    - **Ad-hoc columns** = **scoped async map-reduce**: per property, retrieve cached linked chunks + ONE scoped extraction call (not a planning loop) → reduce → cache each cell by `(property_id, question_hash, doc_set_version)`; progressive fill; recompute only when underlying docs change.
    - The full ReAct agent stays for the **chat box only** (deep single-question investigations).
- **Cross-encoder for grey-zone entity merges** (0.70–0.85 band) — raises auto-resolve rate, shrinks the review queue.
- **Deliverable:** zero invented entities, guaranteed-grounded answers, gap-aware completeness, court-ready provenance, portfolio view.

> **On domain fine-tuning:** deliberately NOT pursued (massive cost/data/risk). Substituted with strong prompt engineering + few-shot exemplars + the structured system prompt + the verifier — ~95% of the benefit at ~5% of the cost.

> **Model strategy (right model per task — "model routing"):** Use **`claude-opus-4-8`** (released 2026-05-28; verified available, same price as 4.6 at $5/$25, 1M context) for the work where reasoning decides correctness — **agent reasoning, final synthesis, contradiction/anachronism analysis, and the adversarial gate**. Keep **Claude Sonnet 4.6** for high-volume cheap tasks (Vision OCR, contextual summaries, classification, metadata extraction) to control cost. Switching the reasoning model is a **one-line `Settings`/env change** (`RAG_V3_AGENT_MODEL` / `CLAUDE_MODEL`: `claude-opus-4-6` → `claude-opus-4-8`), validated against the eval set — low risk, no cost penalty.
> - **Why 4.8 specifically helps us:** the window is the same 1M as 4.6, but **long-context recall is dramatically flatter** — needle-in-haystack recall at 200k tokens is ~95% (vs ~64% on 4.7). The model actually *uses* every chunk instead of skimming the middle → directly serves "never miss." Also ~4× less likely to let a flaw pass, fewer output tokens, "most honest model yet." Tier-4 + $1,000 budget + 90% prompt-cache savings → cost is a non-issue.
> - **Consequence for evidence-pack sizing:** 4.8's flat long-context recall means the earlier "lost in the middle" penalty is largely gone up to 200k — so we have real headroom to be more generous with the initial chunk pack IF the eval shows it helps (still eval-tuned, not blind).
> - **Effort / adaptive-thinking strategy (ONE global level = `xhigh`):** Opus 4.8 uses `thinking: {type:"adaptive"}` + an `effort` level. We set **`effort: xhigh` globally** on the reasoning model (`claude-opus-4-8`). Rationale: our system is fundamentally agentic (v3 ReAct loop) and `xhigh` is Anthropic's recommended level for agentic/long-horizon work — near-max reasoning depth **without** `max`'s documented overthinking + diminishing-returns risk. (`high` is the floor; `max` is for isolated hardest tasks, not a global default.) Enable adaptive thinking (skips deep thinking on trivial turns → saves tokens); set large `max_tokens` (~64k start) so thinking has room. Revisit `max` only if the Sprint 6 eval proves it beats `xhigh` on our real queries. Cheap tasks run on Sonnet 4.6 regardless.

> **Considered & deliberately deferred (kept lean — robust, not messy):**
> - **Deception-edge / semantic lineage** — already covered by contradiction detection + evidence export; a separate "deception ledger" concept adds surface area without new robustness.
> - **Merkle-tree derivation chain** — already covered by SHA-256 per file + page-level provenance + verbatim verification + retained original files; a tree rollup is machinery for a marginal gain.
> - **Topological graph-density reranking** — tuning-sensitive, can bury a lone smoking-gun chunk, needs A/B; collides with the "reliable over experimental" rule. Revisit in a future measured-enhancements pass (Sprint 9) only if eval shows a need.

---

## 7 · The hard technical challenges (and how we make them rock-solid)

| Sprint | Hard problem (technical term) | How we make it rock-solid |
|---|---|---|
| 1 | MIME parsing / charset transcoding | Decoding cascade (reuse rescue extractor); never crash; keep both plain+HTML |
| 1 | Email threading (JWZ) | Headers first; subject+participant+time fallback |
| 1 | Content-addressable dedup (SHA-256) | One chunk-set + `occurrences[]`; cross-corpus collapse |
| 1 | Near-duplicate / quoted-reply (MinHash) | Strip quoted history before chunking |
| 1 | OCR at scale (rate limit, backoff, spend guard, idempotency) | Reuse existing guards; SHA-keyed resume |
| 2 | Structured information extraction (schema-constrained tool-use) | JSON-schema-validated outputs + confidence |
| 2 | Extraction hallucination (grounding / faithfulness) | Verbatim span + page required; unverifiable → reject → review queue |
| 2 | Long-document "lost in the middle" | Section-scoped extraction + prompt caching |
| 2 | Temporal normalization (multi-axis dates) | Normalize to ISO + tag date kind |
| 3 | Entity resolution / record linkage | Blocking + multi-signal scoring + thresholds + review queue |
| 3 | Transitive merge cascade (union-find) | Conservative thresholds + must-not-link firewalls (e.g., different parcel IDs) |
| 3 | Coreference / anaphora resolution | LLM coref pass during extraction |
| 3 | Knowledge-graph w/ provenance + bitemporal | `as_of`/`until` + `source_chunk_id` on every edge |
| 4 | Contradiction vs legitimate supersession | Use source types + dates + amendment edges to distinguish |

**The throughline:** idempotency (re-runnable), grounding (every fact traceable to a verbatim source), conservative thresholds + human review (never silently guess on identity or facts).

---

## 8 · Timeline summary

- **Usable David corpus:** ~2 weeks (Sprint 0 + 1)
- **Full multi-source + linkage:** ~4 weeks (through Sprint 3)
- **Fraud signals + legal work-product + measured accuracy:** ~6.5–8 weeks (through Sprint 6)
- **Absolute-complete system (every accuracy lever, completeness, portfolio UX):** ~8–9.5 weeks (through Sprint 8)

### Changelog
- **v11 (Jun 11, 2026 — post-ingestion review, all source types now stored):** Added the three end-state upgrades chosen after re-auditing the whole plan against the live corpus: **(1) Fraudulent-conveyance rule pack** (Sprint 4) — deterministic UFTA/NY-DCL voidable-transfer tests over deed chains × judgment timeline × insider status × equity values; the trustee's clawback weapon, pure rules over data we already hold. **(2) Persistent findings ledger** (`findings/`, §3.6; Sprint 4) — detector + agent discoveries persist with evidence chains and human review status; the investigation accumulates instead of re-deriving. **(3) Event store** (`events/`, §3.6; Sprint 5) — every dated fact is an indexed event row; the timeline builder narrates an already-correct sequence instead of reasoning it out. Also recorded the Sprint-3 execution order learned from the title/insurance/equity linkage work: **canonical property consolidation FIRST** (parcel-digits ∪ address-core, must-not-link firewalls), people/LLC resolution second, relationships third, **chunk+embed AFTER consolidation** so chunks carry canonical entity_refs from day one.
- **v10:** Upgraded the Sprint 8 adversarial check from single-pass to a **bounded adversarial loop**: Defense-Critic pass → **one** bounded re-plan to close a found gap → ship or downgrade/flag. Sequential (not parallel), capped at one retry — reuses existing agent budget + verifier retry; avoids unbounded-loop mess.
- **v9:** Simplified effort to ONE global level = **`xhigh`** (Anthropic's recommended level for agentic work; near-max reasoning without `max`'s overthinking/diminishing-returns risk). Revisit `max` only if eval proves it wins.
- **v8:** Added **effort / adaptive-thinking strategy** for Opus 4.8 (per-task). Superseded by v9 (single global level).
- **v7:** Verified & adopted **`claude-opus-4-8`** for the reasoning layer (released 2026-05-28, same $5/$25 price as 4.6, 1M context, much flatter long-context recall ~95% @200k). Flip env in Sprint 0. Keep Sonnet 4.6 for cheap tasks. Noted 4.8's flat recall gives headroom for a larger evidence pack (still eval-tuned).
- **v6:** Recall levers finalized: **alias & legal-synonym query expansion** (Sprint 3), **recall-tuned wide-net pools** + **eval-tuned evidence-pack sizing** (Sprint 7). Added **model-routing strategy** (most-capable Opus for reasoning; Sonnet for cheap tasks; latest-Opus upgrade is a one-line config change validated by eval).
- **v5:** Folded in 3 lean, additive enhancements (no sprint/schema disruption): **anachronism/backdating check** (Sprint 4), **mode-scoped cache & memory isolation** (Sprint 5), **adversarial check inside the faithfulness gate** (Sprint 8). Recorded **considered & deferred**: deception-edge, Merkle tree, graph-density rerank (kept lean — robust, not messy).
- **v4:** Added **redaction-aware handling** across Sprint 2 (tag redaction boxes at extraction), Sprint 3 (redacted = "unknown" not "absent"; don't sever links), Sprint 4 (redacted ≠ omitted → no false-positive fraud flags). Added **portfolio-grid execution rule** (cached materialized view + async map-reduce, never live agent) in Sprint 8 + **property dossier** precompute in Sprint 4.
- **v3:** Sprint 7 locked to single best choices (no A/B), because the system will be judged by a third party and trust requires proven+explainable components: **LLM-as-reranker** (not ColBERT), **3-tier contextual chunking** (not late chunking), **keep voyage-4-large** (not voyage-law-2 — no foundation gamble). Sprint 7 trimmed to 4–6 days.
- **v2:** Added Sprint 7 + Sprint 8. Folded in: query decomposition, sufficiency check, post-generation entity validation (Claude-compatible KG-Trie equivalent), faithfulness gate, golden-answer regression, negative-evidence reporting, OCR-confidence surfacing, audit export, spreadsheet-grid UI, cross-encoder entity merges. Earlier enrichments retained: draft-preservation, coreference, bitemporal edges, omission detection, flow-of-funds.

---

## 9 · Open decisions (to confirm before the relevant sprint)

1. **`.eml` export** of AA_Fund (confirm mail client → exact export steps so threading survives). `.eml` preferred; mbox/`.msg` acceptable. *(Sprint 1)*
2. **Extraction strictness** — verifier-strict vs balanced (verify dates+amounts only) vs fast-first. *(Sprint 2)*
3. **Inbound folder layout** — by source-type / by-property / by-entity / flat. *(Sprint 2)*
4. **Privilege confirmation** — experts retained through counsel? per-email privilege certainty? *(Sprint 5)*
