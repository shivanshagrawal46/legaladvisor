# 04 · Build Manifest — Sprint 2-remaining → Sprint 8 (the "nothing missed" checklist)

**Status:** Living execution tracker. Every feature from `02_PHASE_3_PLAN_IN_DEPTH.md` + `03_VISION_AND_NORTH_STAR.md` + all conversation decisions is listed here with a checkbox. I build against this and check items off. If it is not in this file, it was missed — so this file must stay complete.

Legend: `[ ]` to build · `[~]` partial/exists · `[x]` done & verified

---

## A · Locked decisions (from the user, Jun 15 2026)

- **Entity sides:** Mango Tree = **ours** (`our_side`) · GMR = **third-party investor** (`third_party`) · Directional = **David's** (`david_network`) · Washington = **Brian / co-victim** (`co_victim`) · IPA / Island Properties & Associates / IPA Realty = David's · address-coded LLCs (house#+street) = David's.
- **Privilege:** audience = our lawyers + trustee (our side) only; David's material = adverse-party admissions. Two privilege states matter: `privileged` (ours) and everything usable. Clean mode still built (structural), but audience is inside the circle.
- **Eval:** no external answer key — I author my own Q&A test sets and self-verify (Sprint 6).
- **Frontend:** build the **real, world-class spreadsheet UI now**. UI/UX must be exceptional. Frontend is a first-class deliverable.
- **Core mandate:** never miss any file/detail for a query; everything interlinked; multiple layers of AI analysis + review; best detailed case analysis.
- **Model routing:** reasoning = `claude-opus-4-8` @ effort `xhigh`; cheap/volume = `claude-sonnet-4-6`. Embeddings = `voyage-4-large`. Rerank = `rerank-2.5`.

---

## B · Current state (done & verified)

- [x] All source docs ingested + OCR'd + deduped (237 title, 73 insurance, 1 equity, 1 agreement, 16 litigation = 328 docs, ~15,047 pages)
- [x] `documents/` collection populated with per-type fields
- [x] Canonical **property** consolidation → 180 hubs (`consolidate_properties.py`)
- [x] David LLC flagging (Excel seed + address-coded pattern)
- [x] Chunk + contextual summary (Sonnet 4.6) + embed (voyage-4-large) for ALL 328 docs → 9,552 chunks in `email_chunks_v2`; integrity audit PASS
- [x] Existing engine: v1 retriever, v2 hybrid (5 channels + RRF + rerank), v3 tool-use agent (9 tools), deterministic verifier, structured-answer pipeline

---

## C · Codebase extension map (where each thing plugs in)

- Entities/relationships: scripts write to `entities/` + `relationships/`; **no shared `src/` module yet** → create `src/graph/` for resolution + edges + fan-out.
- Retrieval: `src/rag/v2/hybrid_search.py` (channels), `orchestrator.py` (pipeline), `reranker.py`. Collection `email_chunks_v2`, index `email_chunks_v2_vector` (1024-dim cosine).
- Agent: `src/rag/v3/agent.py` (`AgentRunner.run`), tools in `src/rag/v3/tools.py` (`build_tool_specs`), prompts `src/rag/v3/prompts.py`.
- Verifier: `src/rag/v2/verifier.py` (`verify_facts`), structured output `src/rag/v2/structured_answer.py`.
- Settings: `config/settings.py` (all flags). Evidence vocab: `src/rag/evidence_schema.py`.
- Entry: `api/rag_singleton.make_chat()` → `src/rag/chat.py::LegalAdvisorChat.ask`; CLI `scripts/run_query.py`; WS `api/websocket_chat.py`.
- **Gap to fix:** email/attachment chunks have NO `entity_refs`; only Phase-3 doc chunks do. Retrieval does not fan out by entity yet. `addr_core` duplicated in two scripts → unify in `src/graph/normalize.py`.

---

## D · Sprint 2 — remaining

- [ ] **Grounded field extraction** — typed facts per doc (chain of title, deeds, mortgages, liens, satisfactions, lis pendens, monetary_facts) each with **verbatim quote + page** → `documents/`. Schema-constrained tool-use (Sonnet), unverifiable → review queue.
- [ ] **Lawyer-corpus tag backfill** — stamp pre-Phase-3 PST emails+attachments: `corpus=legal_correspondence`, `privilege_status=privileged`, `evidentiary_class=privileged_work_product`, `custody{}`. Idempotent.
- [ ] **Chunk-level corpus/privilege tagging** — flow `corpus` + `privilege_status` + `matter_id` onto every `email_chunks_v2` chunk (cheap `update_many`, no re-embed). Powers Clean-mode + corpus-filtered retrieval.
- [~] **Redaction-aware extraction** — `[REDACTED_*]` tags + `has_redactions` + redacted-field list on docs (title OCR partial; formalize + apply to court/DA docs).
- [~] **Per-source-type extraction schemas** — formalize deed/mortgage, LLC formation, DA/court schemas (title/insurance/equity/agreement/litigation done).
- [ ] **Temporal normalization** — all dates → ISO + `date_kind` tag (document/effective/recording/filing/execution).
- [ ] Quality gates: `needs_review` when missing date/entity/low-confidence; obs metrics.

## E · Sprint 3 — entity resolution + linkage graph + fan-out

- [x] ① Canonical **property** consolidation (done)
- [x] **Shared graph module** `src/graph/` — `schema.py` (sides, kinds, 16 edge types, authority scores, date kinds) + `normalize.py` (consolidated norm_name/addr/addr_core/parcel/llc_matches_address); 8/8 unit tests pass (`tests/test_graph_normalize.py`).
- [x] **Apply locked entity-side decisions** — `scripts/apply_entity_sides.py`: 156 david_network, Mango Tree=our_side, GMR=third_party, Brian Detmer + Washington New Realty=co_victim; 22 multi-party entities flagged `needs_split`. (27 Washington Realty stays David's per user.)
- [ ] ② **People resolution** — canonical person entities (David + team, our team, Brian), aliases keyed on email/signature; blocking → multi-signal scoring → thresholds → review queue → union-find; idempotent.
- [~] ② **LLC resolution** — keyed on state filing #/EIN; classify non-address-coded entities per decisions.
- [ ] **`bank` entities** — create kind=bank from lenders (equity `lender`, mortgages) — currently only string fields.
- [ ] ③ **Full relationship edge set** — `GRANTOR_OF, GRANTEE_OF, OWNS, MEMBER_OF, BORROWER_OF, HAS_LIEN, HAS_MORTGAGE, HAS_INSURANCE, ABOUT_PROPERTY, REFERENCES, SATISFIES, ATTACHED_TO, FILED_IN, SENT_EMAIL`. Add `source_chunk_id` + `confidence` to edge schema (currently missing).
- [ ] **Bitemporal edges** — `as_of` + `until` on ownership/control edges.
- [ ] **Coreference pass** — resolve "he", "the property", "the Seller", "Id." during extraction.
- [ ] **Redaction-aware resolution** — redacted span = "unknown", never sever a link.
- [ ] **Backfill entity_refs onto ALL chunks** — email + David corpus chunks (NER + addr_core + resolve_owner_entity), not just doc chunks. (Critical: today email chunks have no graph linkage.)
- [ ] **New agent tools** — `search_entity_cluster` (default), `list_documents_for_entity`, `graph_query` (multi-hop), `compare_documents`. Register in `build_tool_specs`; demote old tools to fallback.
- [ ] **Entity-anchored fan-out retrieval** — resolve query mentions → canonical IDs → union over `entity_refs.*` across all source types; rank hybrid × authority × recency × entity-match; then rerank.
- [ ] **Alias & legal-synonym query expansion** — entity aliases + lien↔encumbrance, grantor↔seller, mortgage↔deed of trust.
- [ ] **Agent prompt rewrite** — entity routing, cross-source synthesis, authority hierarchy, privilege mode.
- [ ] **Alias-learning loop** — confirmed merges teach the resolver.

## F · Sprint 4 — authority + contradiction + supersession + fraud brain

- [ ] **Authority scores wired into reranker** — court order 1.25 > deed/mortgage/satisfaction 1.20 > lien/lis_pendens/da 1.18 > title/closing 1.15 > insurance 1.10 > contract/op-agmt 1.08 > bank/wire/tax 1.06 > llc 1.05 > email_attachment 1.00 > email_body 0.95 > draft/notes 0.85.
- [ ] **Contradiction detection** — fact clusters per (predicate + entity); flag numeric/date/identity/status/**omission** divergence; mark operative side + admissions.
- [ ] **Anachronism / backdating check** — doc execution date vs LLC formation/incorporation date → Critical Corporate Anachronism.
- [ ] **Redaction-aware detection** — redacted field excluded from omission AND contradiction flags (no false-positive fraud).
- [ ] **Supersession lineage** — latest title/instrument operative; preserve history; surface draft↔executed diff.
- [ ] **Property dossier (materialized view)** — per property: latest title status, insurance in force, liens, mortgages, equity, latest deed, contradictions; refresh on new docs. Powers fast answers + the grid (no live agent).
- [ ] **Fraudulent-conveyance rule pack (UFTA/NY-DCL)** — per transfer: (a) transfer date vs claim/judgment date, (b) insider grantee (David-network), (c) consideration vs market value (equity), (d) insolvency where inferable → voidable-transfer candidate finding with full citations. Deterministic, no LLM in rule test.
- [ ] **Persistent findings ledger (`findings/`)** — every detector + agent discovery: evidence chain (`source_doc_ids`, quotes), confidence, `confirmed/rejected/pending` status; surfaced on future queries touching the entity.
- [ ] **Omission/silence detection** — record-proven fact David never mentioned = evidence (contradiction type).
- [ ] **Adversarial entity obfuscation** — shells/nominees via behavioral edges (controls email + bank), not just formation paper.

## G · Sprint 5 — legal work-product

- [ ] **Event store (`events/`)** — every dated fact = one indexed row `{event_type, date, date_kind, entity_ids[], property_id, doc_id, source_quote, amount?}`; written at ingestion + by S4 detectors.
- [ ] **Timeline / chronology builder** — reads `events/` (per-property / whole-case / flow-of-funds); LLM only narrates an already-correct, already-cited sequence.
- [ ] **Evidence-packet export** — Bates/exhibit-cited bundles (FRCP 26); source file → SHA → page → quote.
- [ ] **Flow-of-funds tracing** — wires + equity + bank records → money-movement view across entities.
- [ ] **Privilege-aware answering** — Analysis mode (sees all, labeled) vs Clean mode (privileged excluded at retrieval layer).
- [ ] **Mode-scoped cache & memory isolation** — Clean sessions never reuse Analysis cache/memory; cache keys include mode.
- [ ] **Confidence + provenance footer** on every answer (what used, which corpus, privileged?, verified/flagged).

## H · Sprint 6 — eval, observability, hardening

- [ ] **Self-authored private eval set** (~50 queries → expected sources, I build + self-verify).
- [ ] **Metrics** — Recall@10, MRR, Faithfulness (≈1.0), contradiction recall, timeline accuracy, zero-privileged-leakage check; nightly.
- [ ] **Ingest/admin dashboard** — $ spent, needs-review queue, entity-merge queue, classifier confidence.

## I · Sprint 7 — retrieval & precision (LOCKED, no experiments)

- [ ] **LLM-as-reranker** — keep Voyage rerank-2.5 base + Opus/Sonnet final scoring pass on top ~40 (NOT ColBERT).
- [ ] **3-tier contextual chunking** — `[Doc] + [Section] + [Chunk]` prefixes (NOT late chunking). Adds `context_doc`/`context_section`/`context_chunk`.
- [ ] **Keep voyage-4-large** (do NOT switch to voyage-law-2).
- [ ] **Query decomposition** — split multi-part questions; retrieve per sub-question; synthesize.
- [ ] **Sufficiency / self-reflection check** — "what would make this incomplete? have I checked every linked source?" before answering.
- [ ] **Robust numeric/date normalization** — $1.45M ↔ 1,450,000.00; sharpens contradiction detection.
- [ ] **Recall-tuned candidate pools** — wide net (generous numCandidates/top-k), low minScore floor; rerank hard.
- [ ] **Evidence-pack sizing tuned by eval** — not blindly inflated (avoid lost-in-the-middle).

## J · Sprint 8 — hardening, completeness & portfolio UX

- [ ] **Post-generation entity validation** — validate every person/property/LLC name in the answer against the canonical graph → zero invented entities.
- [ ] **Faithfulness gate + bounded adversarial loop** — fail-grounding doesn't ship; Defense-Critic ("you are David's defense attorney — find the gap"); one bounded re-plan → ship or downgrade+flag.
- [ ] **Golden-answer regression tests** — lock known-correct answers; no silent regression.
- [ ] **Negative-evidence / completeness reporting** — system states what it does NOT have.
- [ ] **OCR-confidence surfacing** — facts on low-confidence OCR pages marked, never silently hardened.
- [ ] **Full audit / provenance export** — one click: source file → SHA → page → quote (court-ready).
- [ ] **Spreadsheet-grid portfolio UI (world-class UX)** — rows=properties, cols=questions, cells=cited answers. **Cached materialized view + async map-reduce, NEVER live agent.** Standard cols = instant dossier reads; ad-hoc cols = scoped async map-reduce cached by `(property_id, question_hash, doc_set_version)`. Chat box = full agent.
- [ ] **Cross-encoder for grey-zone entity merges** (0.70–0.85) — raise auto-resolve, shrink review queue.

## K · Cross-cutting (every sprint)

- [ ] Switch reasoning model to `claude-opus-4-8` @ effort `xhigh` (validate vs eval); Sonnet 4.6 for cheap tasks.
- [ ] Idempotent + resumable + **per-sprint integrity/accuracy audit** (the "nothing missed" guarantee).
- [ ] Conversation memory in v3 agent; `minScore` floor; settings drift killed.
- [ ] Chain of custody (SHA-256 + page provenance) preserved on every new artifact.
- [ ] Human-in-the-loop review queue for uncertain merges/facts — never silently guessed.

## L · Deliberately DEFERRED (do NOT build — recorded so they're not "missed")

- Deception-edge / semantic lineage (covered by contradiction + export).
- Merkle-tree derivation chain (covered by SHA-256 + provenance).
- Topological graph-density reranking (tuning-sensitive; Sprint 9 only if eval shows need).
- Domain fine-tuning (replaced by prompt engineering + few-shot + verifier).
- `voyage-law-2` switch (older model; no foundation gamble).
- ColBERT reranker; late chunking (trust/reliability).

---

## M · Execution protocol

1. Build sprint-in-order (2-remaining → 3 → 4 → 5 → 6 → 7 → 8); within a sprint, dependency order.
2. After each sprint: run an automated audit + a self-authored Q&A test battery; report PASS/FAIL with numbers.
3. Pause only for the genuine decisions (now resolved in §A) or new ambiguity that risks legal correctness.
4. Keep every script idempotent + resumable; never lose data on crash.
5. Update this manifest's checkboxes as items complete.
