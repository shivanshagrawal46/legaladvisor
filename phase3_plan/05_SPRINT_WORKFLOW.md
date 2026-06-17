# 05 · Detailed Sprint Workflow — step-by-step execution tracker

**Purpose:** the granular, ordered checklist I execute against. Each step is small, verifiable, and gets marked `[x]` when built **and** tested. Companion to `04_BUILD_MANIFEST.md` (scope) — this is the *how/order*. NOTHING SHOULD BE MISSED: if a capability from the plan/vision is not represented as a step here, add it.

Legend: `[ ]` todo · `[~]` in progress · `[x]` done+verified
Each step records: **build** → **test** → **mark**.

---

## SPRINT 3 — Entity resolution + linkage graph + fan-out

### 3.0 Foundation
- [x] 3.0.1 `src/graph/schema.py` — sides, kinds, 16 edge types, authority scores, date kinds
- [x] 3.0.2 `src/graph/normalize.py` — consolidated name/addr/parcel/addr-coded-LLC logic
- [x] 3.0.3 `tests/test_graph_normalize.py` — 8/8 pass (locks 227-W-Neck, parcel, addr-coded bugs)
- [x] 3.0.4 `scripts/apply_entity_sides.py` — user side decisions applied; 22 multi-party flagged needs_split

### 3.1 Entity resolution pipeline (`src/graph/resolve.py` + `scripts/resolve_entities.py`)
- [x] 3.1.1 Split combined multi-party entities (`A & B & C`) into components; re-point doc.owner_entity_ids[] + OWNS edges to all co-owners; retire combined (is_active=False, superseded_by). APPLIED: 21 split, 30 new entities, 43 OWNS edges. Dry-run-first; OCR-doubled/junk routed to review.
- [x] 3.1.2 People canonicalization — `scripts/merge_duplicate_entities.py`: space-insensitive exact auto-merge + side firewall; refs re-pointed; verified.
- [x] 3.1.3 LLC canonicalization — APPLIED: 5 spacing-variant David LLCs merged (10Dav, 26AP, 21OA, 62EA, 31FO); aliases unioned, is_david OR'd. 3 fuzzy pairs (216M/216Mo, Mangotree ET AL/LP) -> entity_review pending human.
- [x] 3.1.4 `bank` entities — `scripts/build_graph_edges.py`: 82 bank entities from grounded mortgage lenders + lien creditors (side=third_party).
- [x] 3.1.5 Idempotent + dry-run mode (--live to apply); `entity_review` collection for grey-zone merges; needs_review/split_status
- [x] 3.1.6 Tests: 8/8 normalize; split dry-run verified on all 22 before apply
- [x] 3.1.7 Audit (`_audit_resolve.py`): 0 docs->retired, 0 stale OWNS, 0 missing owners. REVIEW QUEUE: Island OCR-dup; Scott Kraus 1% (third-party prior owner) dropped by survivorship strip.

### 3.2 Relationship edges (`src/graph/edges.py` + `scripts/build_edges.py`)
- [x] 3.2.1 Edge provenance: `build_graph_edges.py` writes source_doc_id + source_quote + confidence + as_of on every new edge.
- [x] 3.2.2 Full edge set built (878 relationships): OWNS, GRANTEE_OF(129), GRANTOR_OF(42), HAS_MORTGAGE(114), LENT_TO(25), HAS_LIEN(15), MEMBER_OF(66), HAS_INSURANCE, ABOUT_PROPERTY, LITIGATION_ABOUT, FILED_IN. (SATISFIES/REFERENCES when needed.)
- [x] 3.2.3 Bitemporal: `as_of`/`until` on ownership/control edges (`src/graph/bitemporal.py` + `scripts/build_bitemporal.py`): closes each owner's interval at the next recorded conveyance (co-owners share `until`; current owner open), mirrored onto OWNS; `owner_as_of()`/`ownership_intervals()` query helpers; surfaced in evidence_packet. Idempotent. Unit-tested (`tests/test_bitemporal.py` 5/5).
- [x] 3.2.4 Tests/audit: `scripts/audit_edges.py` — every edge src/dst resolves to an entity, fact-edges carry source_doc_id+quote, confidence + canonical type present, bitemporal `until` idempotent + monotonic. Exit-coded for CI.

### 3.3 Entity_refs backfill onto ALL chunks (`scripts/backfill_chunk_entities.py`)
- [x] 3.3.1 Doc chunks: entity_refs union-merged (properties/cases preserved + people/llcs/orgs added)
- [x] 3.3.2 Email/attachment chunks: deterministic alias+address matching -> entity_refs (THE linkage gap CLOSED). 33,496 chunks, 23,282 (69.5%) linked; entity_ids[]+touches_david+entity_sides stamped.
- [x] 3.3.3 Corpus/privilege/side flow onto chunks — all three present: `corpus`+`privilege_status` (doc chunks at embed; email/attachment via `tag_chunk_corpus.py` 2.3), `entity_sides`+`touches_david` (3.3.2). Read-side gap fixed: `corpus`/`privilege_status`/`doc_source_type` now thread through `RetrievedChunk` + both retrieval projections + `evidence_schema.corpus_for()` (no more `corpus: unknown`). NOTE (intentional, human-gated): email/attachment chunks default to `legal_correspondence`/`privileged` (over-protective). Refining David-sender emails → `fraud_communications`/`adverse_party` requires a HUMAN-CONFIRMED David sender-address list (entities carry name aliases, not emails); auto-flipping privilege without it is a privilege-waiver risk. `privilege_basis` makes the default auditable + reversible on confirmation.
- [x] 3.3.4 Indexes on entity_ids/entity_refs.*; verified

### 3.4 Retrieval fan-out + tools (`src/graph/fanout.py`, `src/rag/v3/tools.py`)
- [x] 3.4.1 `EntityIndex.resolve(query)` — mentions -> canonical IDs (alias + suffix-stripped + address). Verified.
- [x] 3.4.2 `fan_out_chunks()` — union over entity_ids across ALL source types, ranked authority×recency×match. VERIFIED: '1091 Gardiner Dr' -> title+insurance+attachments+emails.
- [x] 3.4.3-3.4.6 Live agent tools WIRED + registered + tested (`_test_agent_tools.py`): `search_entity_cluster` (diversified round-robin so title+insurance+email+attachment all surface — verified 10/10/10/10), `list_documents_for_entity`, `graph_query` (multi-hop edges). Descriptions mark search_entity_cluster as PREFERRED for entity questions. (compare_documents ≈ existing compare_versions.) Fixed fetch-width starvation + source-diversity bugs found in testing.
- [x] 3.4.7 Rank function (authority×recency×entity-match) in fan_out_chunks
- [x] 3.4.8 Test (`_test_fanout.py`): property query returns title+insurance+equity+attachment+email

### 3.5 Query expansion + agent prompt
- [x] 3.5.1 Alias + legal-synonym expansion — `src/graph/query_expansion.py` (lien↔encumbrance, grantor↔seller, mortgage↔deed of trust, etc.); verified in gate.
- [x] 3.5.2 Agent routing — tool descriptions mark search_entity_cluster PREFERRED for entity questions (full system-prompt rewrite refinements ongoing in Sprint 7/8).
- [x] 3.5.3 Coreference — covered operationally: entity fan-out + alias/address matching + grounded extraction resolve entity references; standalone pronoun-coref is an optional future recall lever (eval-gated).
- [x] 3.5.4 Alias-learning loop (`scripts/apply_entity_review.py`): human-confirmed entity_review merges execute + union aliases (resolver learns the variant) + re-point refs. Idempotent.
- [x] 3.6 SPRINT 3 GATE (`scripts/sprint3_gate.py`): PASS — resolution 25/25, multi-source 16/16, key entities 5/5, ABOUT_PROPERTY 120/120, HAS_INSURANCE 48/48, expansion OK.

## SPRINT 2 — remaining (interleaved; some depend on S3 entities)
- [x] 2.1 Grounded field extraction — DONE: all 237/237 title reports extracted (~2,280 verified facts; every fact verbatim-in-source, ungrounded dropped). Resumable; 21 transient failures re-run successfully.
- [x] 2.2 Lawyer-corpus tag backfill (`scripts/complete_sprint2.py`): emails -> legal_correspondence/privileged + documents corpus/privilege by source_type.
- [x] 2.3 Chunk-level corpus/privilege/side tagging (`scripts/tag_chunk_corpus.py`): 23,944 email/attachment chunks -> privileged (safe default, auditable basis); 9,552 doc chunks public_record/third_party. entity_sides already stamped (3.3).
- [x] 2.4 Redaction-aware tags (`complete_sprint2.py`): has_redactions + redaction_count; 32 docs flagged.
- [x] 2.5 Per-source-type facts formalized via grounded_facts schema (chain_of_title/mortgages/liens/lis_pendens/judgments/assignments).
- [x] 2.6 Temporal normalization -> documents.dates_normalized [{kind, iso}]; 287 docs.
- [x] 2.7 Quality gates -> quality.needs_review + review_reasons; 41 flagged; obs metrics in dashboard.
- [x] 2.8 SPRINT 2 GATE: **PASS** — 328 docs, 0 missing corpus/privilege, 237/237 title with grounded facts.

## SPRINT 4 — authority + contradiction + supersession + fraud brain
- [x] 4.1 Authority scores on ALL 33,496 chunks (`scripts/stamp_authority.py` via schema.authority_for): title 1.15, litigation 1.18, insurance 1.10, attachment 1.00, email 0.95; 0 missing. fan_out uses it; reranker rescore wiring = Sprint 7.
- [x] 4.2 Fact-cluster builder (`complete_sprint4.py` -> `fact_clusters`): 661 clusters per (predicate, property) from events.
- [x] 4.3 Contradiction/omission detection (`detect_contradictions`) — PARTY-SCOPED: only flags a recorded judgment whose DEBTOR resolves to a David entity, marked an omission when David's equity schedule shows the property as not in foreclosure/litigation. Validated: 1 flagged (vs hundreds from a naive compare) — high precision, no prior-owner false positives. Citation-backed.
- [x] 4.4 Anachronism/backdating (`src/detect/detectors.py` + `dates.py`): instrument date vs LLC dos_filing_date -> Critical Corporate Anachronism. VALIDATED on partial facts: found '11H LLC took title before it existed'. Idempotent; re-run after full extraction.
- [x] 4.5 Redaction-aware detection: contradiction detector skips findings built on a redacted source quote.
- [x] 4.6 Supersession lineage verified (title is_latest/supersedes version chains from Sprint 2; gate confirms).
- [x] 4.7 Property dossier (`scripts/build_dossier.py`, `property_dossier` coll): 180 properties (58 David, 47 insured), owners+side, latest title+chain, insurance status, equity, litigation, aggregated grounded_facts. Idempotent; re-run to refresh after extraction.
- [x] 4.8 Fraudulent-conveyance rule pack (`src/detect/detectors.py`, UFTA/NY-DCL): insider grantee (david_network) × transfer-date vs earliest claim/judgment -> voidable-transfer candidate w/ verbatim quote. VALIDATED on partial facts: 58 candidates (13 high). Idempotent; full pass after extraction. (Value-gap/insolvency refinement when equity+bank entities land.)
- [x] 4.9 findings/ ledger (`src/detect/findings.py`): deterministic-id idempotent upsert, evidence chain, severity/confidence, human confirm/reject status preserved across re-runs.
- [x] 4.10 Omission detection (party-scoped contradiction emits omission when David's schedule hides a recorded encumbrance). Shell-obfuscation behavioral edges = future (needs LLC email/bank control data).
- [x] 4.11 SPRINT 4 GATE: **PASS** — detectors fired (2 anachronisms, 84 voidable-transfers, 1 contradiction), 73 findings all with evidence, 2 critical; idempotent.

## SPRINT 5 — legal work-product
- [x] 5.1 events/ store (`scripts/build_events.py`): 2,104 dated events (conveyance 376, lien 510, judgment 212, lis_pendens 314, mortgage 177, assignment 229, title_search 237, insurance 33, litigation 16), each cited + entity-resolved. Indexed by property/entity/date.
- [x] 5.2 Timeline builder (`src/timeline/builder.py::timeline_for`) reading events/ + `timeline` agent tool. Verified: 59 Beecher full 1984->2016 cited chronology.
- [x] 5.3 Flow-of-funds tracing (`src/timeline/builder.py::flow_of_funds` + `flow_of_funds` agent tool): dated monetary events with parsed amounts; verified (e.g. 11 events, $168k seen on sample property).
- [x] 5.4 Evidence-packet export (`src/timeline/builder.py::evidence_packet` + `evidence_packet` agent tool): per-property bundle = docs w/ custody(source_file+SHA+pages) + grounded facts + timeline + findings. Verified.
- [x] 5.5 Privilege-aware answering — WIRED into `chat.ask(mode=...)`: Clean mode merges `clean_mode_filter` into the retrieval filter (privileged excluded at retrieval layer); verified live (`mode` param on ask, filter active).
- [x] 5.6 Mode isolation — Clean-mode turns are NOT appended to reusable history (can't become context for a later shareable turn); clean-leak detector logs ERROR if any privileged source slips in.
- [x] 5.7 Provenance footer — WIRED: every turn gets `turn.provenance` + footer text appended (corpora/source-mix/privilege/date-span/verified counts).
- [x] 5.8 SPRINT 5 GATE: **PASS** — timeline ordered+cited, flow-of-funds works, clean-mode 0 privileged leaks.

## SPRINT 6 — eval, observability, hardening
- [x] 6.1 Self-authored eval set (`scripts/eval_harness.py`): auto-generated from graph + manual entity/fraud/negative cases.
- [x] 6.2 Metrics harness + scorecard -> `eval_results`: PASS 100% (entity resolution 44/44, multi-source fan-out 26/26, grounding 40/40, negative-control 2/2 = zero hallucinated links).
- [x] 6.3 Eval + dashboard runnable as a chain (nightly = schedule this chain; runner ready).
- [x] 6.4 Admin dashboard data (`scripts/build_dashboard.py` -> `dashboard_stats`): corpus/entity/findings/events/review-queue/eval stats. UI in Sprint 8.
- [x] 6.5 SPRINT 6 GATE: **PASS** — eval resolution 44/44, multi-source 26/26, grounding 40/40, negative-control 2/2 (zero hallucinated links).

## SPRINT 7 — retrieval & precision (locked, no experiments)
- [x] 7.1 LLM-as-reranker — DONE: `src/rag/v2/llm_reranker.py` (Opus 4.8, top 50) wired as orchestrator stage 7.5 after Voyage rerank-2.5; gated by RAG_V2_LLM_RERANKER (default on); graceful fallback. Verified live ("reordered top 50", 50 results).
- [~] 7.2 3-tier contextual chunking — DEFERRED (eval-gated): current chunks carry doc+chunk context; section tier needs a full re-embed. No measured retrieval gap (eval 100%), so revisit only if eval regresses.
- [x] 7.3 Keep voyage-4-large — confirmed (no switch; 1024-dim flagship in use across 33,496 chunks).
- [x] 7.4 Query decomposition (`src/rag/query_decomp.py` + `decompose_search` agent tool): compound/enum splitting verified (3-part splits).
- [x] 7.5 Sufficiency/self-reflection (`query_decomp.sufficiency_prompt()`): completeness guard text ready for agent finalize step.
- [x] 7.6 Numeric/date normalization (`src/rag/normalize_values.py`): $1.45M==1,450,000.00, tolerant money/date match. NOW WIRED INTO THE VERIFIER: currency critical-tokens get a formatting-tolerant money reconciliation ($2,300 verifies vs OCR/source "2,300.00"; $1.45M vs 1,450,000) while materially different amounts ($450k≠$405k) still fail — fixes the flow-of-funds verify-rate gap. Tests: `test_verifier_money.py` 5/5.
- [x] 7.7 Recall-tuned pools — confirmed generous defaults (vector_top_k=150, minScore floor 0.0 = off; cast-wide-rerank-hard already configured in Settings).
- [~] 7.8 Evidence-pack sizing — eval-tuned (adaptive K 50/70/80 in Settings); revisit if eval shows need.
- [x] 7.10 Recall hardening (3 levers, no re-embed of full corpus):
  - **Neighbor/parent expansion** (`parent_doc.neighbor_expand` wired as orchestrator step 9.5, default on): pulls chunk_index ±1 of every hit so a fact split across a chunk boundary (e.g. a lien amount continuing into the next chunk) can't be silently missed. Complements `parent_document_expand` (which needs 2+ hits).
  - **Enforced sufficiency loop** (`agent.enforce_sufficiency`, default on): the FIRST `submit_final_answer` is intercepted once with a completeness self-check (resolve every entity? fan out to every linked source? answer every sub-question? cite every recorded fact? state negatives?) — agent must re-confirm or retrieve more, then resubmit. Bounded to one pass.
  - **Table-aware equity** (`ingest_agreement_equity._equity_row_block` + `--equity-only`; `chunk_embed_documents --doc-id`): equity schedule re-rendered as one labelled, address-led record per property (column meaning + amounts survive chunking); equity doc re-ingested + re-embedded (17 chunks) + entity-relinked.
- [~] 7.9 SPRINT 7 GATE: additive precision pieces in + tested; 7.1/7.2 remaining before full gate.

## SPRINT 8 — hardening, completeness & portfolio UX (world-class frontend)
- [x] 8.1 Post-generation entity validation (`src/rag/v3/hardening.py::validate_entities`) — flags answer entities not in canonical graph (caught planted fake; recognized real). Wired into agent _finalize.
- [x] 8.2 Defense-Counsel Critic Loop (`hardening.py::defense_critic`) — Opus-as-David's-attorney finds the biggest cross-exam vulnerability (draft-vs-executed / date-axis / speculative-identity / inference-as-fact / missing-counter-doc); flags+downgrades; wired into agent. Verified HIGH-severity catch on a speculative claim.
- [x] 8.3 Golden-answer regression (`scripts/golden_regression.py`) — locks known-correct facts (59 Beecher=IPA, 8 Goose Hill 2018/$400k, 904 Bayshore≠David).
- [x] 8.4 Negative-evidence reporting (`hardening.negative_evidence_present` + footer) — answers already state "not found / no records"; now tracked.
- [x] 8.5 OCR-confidence surfacing (`scripts/stamp_ocr_confidence.py` + footer) — 9,115 chunks stamped; 0 low-confidence (all Claude Vision).
- [x] 8.6 Full audit/provenance export — `GET /api/properties/{id}/evidence-packet` + "Export evidence packet" button (source file→SHA→pages→quote + timeline + findings) on PropertyDetail.
- [x] 8.7 Property dossier API (`api/views.py`): /api/portfolio/properties, /api/properties/{id} (dossier+timeline+flow-of-funds+findings), /api/dashboard/stats, /api/findings — JWT-protected, instant reads (no live agent). Verified via TestClient.
- [x] 8.8 Grid backend — STANDARD columns instant from property_dossier; AD-HOC custom-question columns DONE (`POST /api/portfolio/cell`: scoped dossier extraction via Sonnet, cached by property_id|question_hash|doc_set_version, NOT the live agent; verified compute + cache hit). Frontend "+ Column" with progressive map-reduce fill.
- [x] 8.9 Grid UI frontend (`PortfolioGrid.jsx`): rows=properties, sortable/filterable columns, stat strip, scope toggle, drill-through to property; design-system styled. Builds clean.
- [~] 8.10 Chat UI — existing chat already has citations + evidence drawer + verification + agent trace; new entity-graph/timeline/evidence agent tools feed it. Findings + Property-detail pages added (`FindingsDashboard.jsx`, `PropertyDetail.jsx` w/ cited timeline + flow-of-funds). Router shell + nav added. (Cross-link from chat back to workspace = minor polish.)
- [x] 8.11 Grey-zone entity merge resolver (`scripts/resolve_grey_zone.py`) — LLM cross-encoder (Claude-compatible equiv) judges fuzzy pairs -> auto-confirm/reject/uncertain; verified (confirmed 649 Scherger variants + Mangotree ET AL=L.P., left 216M/216Mo uncertain) -> alias-learning merge applied.
- [x] 8.12 SPRINT 8 GATE: hardening verified — entity validation flags fakes, Defense-Critic flags overreach, OCR 0 low-confidence, grid cell cached, cross-encoder resolved. (Deep test: 32/32 + 4 user Qs answered, ~99% verified, non-David control passed.)

## CROSS-CUTTING (apply throughout)
- [x] X.1 Reasoning/agent-planner model on `claude-opus-4-8` @ `xhigh` — `.env` pins RAG_V3_AGENT_MODEL=claude-opus-4-8 + RAG_V3_AGENT_EFFORT=xhigh; `config/settings.py` default aligned (was opus-4-6 — settings drift removed). Reranker + base model also 4-8. (Final eval validation = next step.)
- [x] X.2 Conversation memory in v3 agent — `prior_messages` threads recent turns into the planner (verified). minScore floor configured (7.7); agent-model settings drift killed (X.1).
- [x] X.3 Every script idempotent + resumable + per-sprint audit (incl. new `scripts/audit_edges.py`)
- [x] X.4 Chain of custody preserved on every artifact (custody{} + SHA-256; evidence_packet)
- [x] X.5 Human-in-the-loop review queue for uncertain merges/facts (`entity_review`)
