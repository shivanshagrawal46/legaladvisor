# 01 · Current State — What We Have Through Phase 2

**Project:** Mango Tree Legal RAG — Fraud Investigation Evidence Platform
**Owner:** Rakesh Sir's team (Mango Tree)
**Status of this document:** Living reference. Describes the system **as it exists today**, before Phase 3 begins.
**Purpose:** So both of us always know exactly what we already have, what is strong, and what is weak — and nothing is assumed.

---

## 0 · Who we are & what this system is for

We (Mango Tree, Rakesh Sir's team) are **victims of a fraud committed by David and his team.** A trustee has been appointed in the David matter, and recovery of our money depends on giving that trustee **complete, accurate, timeline-correct, provable information.**

This system exists to make sure **no piece of information is ever missed** — that the AI (Claude Opus) and the user receive every relevant detail about any property, person, amount, or event, with correct timeline and verifiable citations. It does what no human can: hold and connect the entire evidence record in memory.

Phase 1 and Phase 2 are **done**. This file documents them honestly.

---

## 1 · Phase 1 — PST ingestion (DONE)

- Source: `Gmail Lawsuit Exportes Email.pst` (~1.3 GB) — the emails and attachments **shared with our attorneys** about the case.
- Parser: `src/parser/pst_parser.py` using `libratom` / `libpff`.
- Extracted per email: subject (+ normalized), plain/HTML/RTF body, headers, sender/recipients, dates (normalized to UTC), threading headers (Message-ID, In-Reply-To, References), attachments (streamed in 4 MB chunks, 50 MB cap).
- **Confirmed corpus size in repo docs: ~1,918 emails ingested** (PHASE2_RUNBOOK.md). Vision-OCR pass covered ~1,699 attachments.
- Output collections: `emails`, `attachments`, `attachment_files.*` (GridFS), `folders`, `ingestion_runs`, `ingestion_errors`.

**Note:** all MIME parsing and character-encoding decoding happened here too — the PST library did it invisibly. The complexity was always present; it was absorbed by the tool.

---

## 2 · Phase 2 — The current RAG system (DONE)

This is a genuinely strong v1. Every parameter below is confirmed from the code.

### 2.1 Extraction & OCR
- **Facade:** `src/extractor/extractor.py` routes by file type (pdf, docx, xlsx, images, txt/csv, etc.).
- **PDF:** `src/extractor/pdf.py` — text-layer first (PyMuPDF); if a page has < 80 chars it goes to OCR.
- **Claude Vision OCR:** `src/extractor/claude_ocr.py` — model **`claude-sonnet-4-6`** (NOT a random OCR), 180 DPI, temperature 0, transcribe-verbatim system prompt, 16-way concurrency, sliding-window rate limiter, **$200 spend guard**, retries with backoff. Confidence recorded as 0.97.
- **RapidOCR** (`src/extractor/ocr.py`): fast fallback for tiny single-page images (PP-OCR v4 ONNX).
- **Rescue tier** (`src/extractor/rescue.py`): `.doc`/`.xls` via MS COM, `.htm`, `.eml` (stdlib `email`), audio via Whisper, magic-byte sniffing, MAPI blob string-mining. **This already parses `.eml` — important for Phase 3.**

### 2.2 Chunking
- `src/rag/chunker.py` — structural **paragraph → sentence → hard-split** packer (never cuts mid-sentence unless forced).
- **Live corpus chunk size: 1000 tokens / 200 overlap** (constants in `scripts/build_email_chunks_v2.py`). Confirmed.
- Every chunk carries a structured header embedded in the text:
  - Email: `[Email — date | from | to | subject]`
  - Attachment: `[Attachment — filename | date | parent email | p. N]`
- Attachment chunks track `page_start` / `page_end`.

### 2.3 Contextual summaries
- `src/rag/v2/contextual_summary.py` — model **`claude-sonnet-4-6`**, 50–100 token context per chunk capturing doc type, date, parties, addresses, relationship to the whole doc.
- Uses **Anthropic prompt caching** (ephemeral) so the document is paid for once per batch.
- Combined as: `[Context] <summary>\n\n[Header]\n\n<body>` → this composite is what gets embedded.

### 2.4 Embedding
- `src/rag/embedder.py` — **`voyage-4-large`**, **1024 dims**, token-budget-aware batching, sliding-window rate limiter, retries.
- Stored on the `embedding` field of each chunk along with `embedding_model` + `created_at`.

### 2.5 The build pipeline — `scripts/build_email_chunks_v2.py`
- **SHA-256 deduplication**: each unique file's content chunked/summarized/embedded **once**.
- **`occurrences[]` fan-out**: records every email that carried that identical content.
- **PRIMARY mirror**: earliest occurrence's metadata copied to top-level fields for cheap filtering/sorting.
- **`latest_date`**: most recent appearance.
- Idempotent + resumable. Two `source_type` values today: `attachment`, `email_body`.
- Collection: **`email_chunks_v2`** (the live RAG corpus).

### 2.6 Retrieval — `src/rag/v2/orchestrator.py` (v2)
A mature multi-channel hybrid pipeline:
1. Query signal extraction (money, dates, filenames, case numbers).
2. Query rewriting + **HyDE** + 2–3 alternate phrasings (`claude-sonnet-4-6`).
3. **5 retrieval channels**: vector (`$vectorSearch`), BM25 (`$text`), exact-phrase, body-regex (literal `$`/comma/hyphen safety net), filename.
4. **Reciprocal Rank Fusion** (k=60).
5. Re-scoring: recency decay × authority (filename-regex tiers) × keyword match.
6. Diversification, temporal diversification, adaptive-K.
7. **Voyage `rerank-2.5`** reranker.
8. Full-document mode + parent-document expansion.
9. Interleaved ordering ("lost in the middle" mitigation).
10. Hard evidence cap at 100K tokens.
- Atlas vector index: `email_chunks_v2_vector` with 17 filter paths.

### 2.7 Agent — `src/rag/v3/agent.py` (v3)
- **Claude Opus 4.6** ReAct loop (PLAN → ACT → OBSERVE → SUBMIT).
- 9 tools: `search`, `search_by_filename`, `search_timeframe`, `fetch_full_document`, `find_quote`, `find_latest_version`, `compare_versions`, `verify_claim`, `submit_final_answer`.
- BudgetTracker (30 tool calls / 3M tokens / 1200s wall clock).
- **Anthropic prompt caching** on system prompt, tools, and seed chunks.
- Streaming force-finalize for large closing answers.
- **3-tier graceful degradation**: agent → verified one-shot → plain Opus.
- Full reasoning trace logged to `agent_trace_log`.

### 2.8 Verifier — `src/rag/v2/verifier.py`
- **OCR-tolerant, two-gate** citation verification:
  - **Critical-token gate**: every `$amount`, date, percent, big number in a quote MUST appear in the cited chunk (prevents `$405k` matching `$450k`).
  - **Fuzzy gate**: `rapidfuzz partial_ratio` ≥ 85.
- Re-extract retry pass; prose patched to repair stale numbers; outcomes logged to `verification_log`.

### 2.9 API / memory
- `server.py` (FastAPI) + `api/websocket_chat.py` (streaming chat, JWT auth, `_json_safe` datetime handling).
- Sessions in `chat_sessions` (durable) + `SummaryMemory` (rolling Sonnet-compacted history).

---

## 3 · What's GOOD (our real strengths)

- ✅ **Best-in-class OCR** — Claude Sonnet 4.6 Vision with budget + rate guards. Not a generic OCR.
- ✅ **Strong chunking** — structural 1000/200 with provenance headers, not naive splitting.
- ✅ **Contextual retrieval** — per-chunk LLM context with prompt caching (an advanced technique).
- ✅ **Mature hybrid retrieval** — 5 channels + RRF + rerank already **exceeds** the "dense + BM25" baseline most production systems stop at.
- ✅ **Source-type-agnostic schema** — SHA dedup + `occurrences[]` + PRIMARY mirror is ready to absorb new document types **without a rebuild**.
- ✅ **Agentic reasoning** — Opus 4.6 ReAct loop with caching and graceful fallback, on par with Harvey's "agentic search."
- ✅ **Evidence-anchored verification** — two-gate OCR-tolerant verifier is unusually disciplined; the foundation of trustworthiness.
- ✅ **Idempotent, resumable pipelines** — safe to re-run, the rock under everything.

## 4 · What's BAD / gaps (honest weaknesses)

From the deep code audit:

- ❌ **Only 2 source types** (`attachment`, `email_body`). No concept of title report, deed, insurance, LLC, court filing.
- ❌ **No document-level layer** — structured facts (recording date, parties, amounts, sections) live implicitly inside chunk text, not as queryable fields.
- ❌ **No entity layer** — no canonical IDs for people, properties, LLCs, cases. "David" across 3 emails ≠ linked today.
- ❌ **No knowledge graph** — no cross-document relationships (owns, grantor, member, lien).
- ❌ **No corpus / privilege / custody tagging** — cannot yet distinguish privileged lawyer email from David's admissions.
- ❌ **v3 agent ignores conversation memory** — multi-turn follow-ups lose context. (Biggest UX bug.)
- ❌ **No `minScore` floor** on vector search — low-relevance noise enters the candidate pool.
- ❌ **Chunk-size drift** — `Settings` says 500/100 while the live corpus is 1000/200; a wrong re-run could corrupt shape.
- ❌ **Fake streaming** — the "typewriter" is post-hoc word splitting, not real token streaming; long agent runs look like a frozen spinner.
- ❌ **No contradiction detection, no timeline builder, no evidence export** — the legal-superpower features don't exist yet.
- ❌ **No corpus-specific eval set** — accuracy is asserted, not measured.
- ❌ **Hardcoded user allowlist** + cosmetic `/api/health` model mismatch.

---

## 5 · Data we currently have (pre-Phase 3)

| Corpus | Content | Status |
|---|---|---|
| Lawyer correspondence | Emails + attachments **shared with our attorneys** | Ingested (~1,918 emails) |

**Everything else (David's emails, title reports, insurance, LLC, equity Excel, litigation updates) is NOT yet in the system. That is Phase 3.**

---

## 6 · One-line summary

> We have a strong, accurate single-corpus RAG system (emails + attachments) with excellent OCR, hybrid retrieval, an agent, and a verifier — but it has no concept of document types, entities, relationships, privilege, timeline weighting, or contradiction detection. Phase 3 turns this engine into a multi-source, fully-linked, trustee-ready evidence platform.
