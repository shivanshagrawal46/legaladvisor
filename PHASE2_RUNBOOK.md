# Phase 2 Runbook — RAG over the email corpus

This is the operator's guide for the Phase 2 build (text extraction +
embeddings + Claude chat). Run the steps in order; each one is idempotent
and logs progress to `logs/`.

---

## 0. Prerequisites

- Phase 1 already complete (1,918 emails ingested, attachments deduped).
- Voyage API key in `.env` as `VOYAGE_API_KEY` (already done).
- Anthropic API key in `.env` as `ANTHROPIC_API_KEY` (needed for `chat.py`,
  not needed for embedding).

---

## 1. Install dependencies

```bash
pip install -r requirements.txt
```

What's new in this install:

| Package         | Purpose                                                 |
| --------------- | ------------------------------------------------------- |
| `PyMuPDF`       | Fast born-digital PDF text extraction                   |
| `paddleocr`     | OCR for scanned PDFs / image attachments                |
| `paddlepaddle`  | Deep-learning engine PaddleOCR runs on (CPU)            |
| `python-docx`   | `.docx` text extraction                                 |
| `pillow`        | Image decoding for OCR                                  |
| `voyageai`      | Embeddings (`voyage-3`) + reranker (`rerank-2.5`)       |
| `anthropic`     | Claude Sonnet 4.5 client                                |
| `tiktoken`      | Token counting for chunk-size budgeting                 |
| `tenacity`      | Retry/backoff wrapper around API calls                  |

> **PaddleOCR's first run** will download ~50 MB of detection +
> recognition models into `~/.paddleocr/`. This happens once, on demand —
> only when an attachment actually needs OCR.

---

## 2. Extract text from every unique attachment

```bash
python scripts/extract_attachment_text.py
```

What it does:

- Groups all `attachments` rows by `sha256` so identical binaries are only
  processed once.
- For each unique binary, streams the bytes from GridFS and routes by
  extension:
    - `.pdf`  → PyMuPDF text-layer first, PaddleOCR fallback per scanned page
    - `.docx` → `python-docx` paragraphs + tables
    - `.png/.jpg/.tif/etc.` → PaddleOCR
    - `.txt/.csv/.log` → direct decode
    - `.xlsx` → openpyxl
    - others (`.zip`, `.exe`, `.doc` legacy) → skipped with reason
- Writes the result to **every** `attachments` row sharing that sha256:
  - `extracted_text` — the full plain-text
  - `extraction.method` — `pdf_text` / `pdf_ocr` / `pdf_mixed` / `docx` /
    `image_ocr` / `raw_text` / `xlsx` / `skipped`
  - `extraction.pages[]` — per-page text + OCR confidence (used for
    citation page numbers)

Useful flags:

```bash
python scripts/extract_attachment_text.py --workers 4    # more parallelism
python scripts/extract_attachment_text.py --no-ocr       # text-layer only (fast first pass)
python scripts/extract_attachment_text.py --limit 50     # smoke test on 50 unique files
python scripts/extract_attachment_text.py --force        # re-extract everything
```

Idempotent: rows that already have a non-empty `extracted_text` are
skipped unless `--force` is passed.

Expected runtime: born-digital PDFs run in ~50ms each. A scanned PDF page
takes 2–5 sec on CPU. Plan for 30–90 minutes for the full corpus,
depending on how many pages need OCR.

---

## 3. Create the Atlas Vector Search index

The Mongo PyMongo driver cannot create vector-search indexes — that's an
Atlas-only feature. Print the index definition:

```bash
python scripts/print_vector_index.py
```

Then in **Atlas → Cluster → Atlas Search → Create Search Index → JSON
Editor**:

1. Database: `fraud_emails`
2. Collection: `email_chunks`
3. Index name: `email_chunks_vector` (must match `VECTOR_INDEX_NAME` in `.env`)
4. Type: **Vector Search**
5. Paste the JSON the script printed and click *Create Search Index*.

Wait ~30–60 seconds for it to become **ACTIVE**.

> You can create the index *before* running step 4 — it's just a schema.
> Atlas will auto-index documents as they're inserted.

---

## 4. Chunk + embed every email body and attachment

```bash
python scripts/embed_corpus.py
```

What it does:

- Walks every email in date order.
- Chunks the cleaned `body_text` with the structural chunker (paragraph
  → sentence → token-window fallback). Every chunk gets a metadata
  header (sender, date, subject) prepended for retrieval recall.
- For each attachment with `extracted_text`, runs the page-aware chunker
  so chunks remember which pages they cover.
- Embeds chunks in batches of 64 with `voyage-3`,
  `input_type='document'`.
- Upserts into `email_chunks` with the full filterable metadata.
- **Idempotent:** chunks carry a `source_hash` (sha256 of cleaned
  source text). If the hash hasn't changed since last run, the email/
  attachment is skipped — re-runs cost almost nothing.

Useful flags:

```bash
python scripts/embed_corpus.py --limit 10           # smoke test (10 emails)
python scripts/embed_corpus.py --emails-only        # skip attachments
python scripts/embed_corpus.py --attachments-only   # skip email bodies
python scripts/embed_corpus.py --batch-size 32      # smaller embed batches
python scripts/embed_corpus.py --force              # re-embed everything
```

Expected runtime: ~5–10 minutes for 1,900 emails + ~1,200 attachments
(after dedup). Voyage's free tier covers this easily.

---

## 5. Chat with Claude

Single-question mode:

```bash
python chat.py "Summarise every wire-transfer instruction Boris sent in 2024"
```

REPL mode:

```bash
python chat.py
>>> What did Phil Campisi escalate about Fort Hill in March 2024?
>>> /filter date_ym=2024-03
>>> /sources
>>> /reset
>>> /quit
```

Each answer prints inline `[#N]` citations and a numbered source list at
the end (date, sender, subject, page span). Add `--full-sources` to also
preview the body text of each cited source.

Filter mini-DSL (sent to Atlas `$vectorSearch.filter`):

```bash
python chat.py --filter date_ym=2024-03 "your question"
python chat.py --filter from_email=boris@mblawfirm.com,source_type=attachment "..."
```

---

## How the system is designed (review notes)

- **Two MongoDB collections drive the chat:** `emails` (the source of
  truth) and `email_chunks` (vector-searchable chunks). Embeddings live
  ONLY on chunks — the emails collection stays lean.
- **No raw PDFs are ever sent to Claude.** Text is extracted once, stored
  on `attachments.extracted_text`, chunked once, embedded once. Claude
  only sees the top-K reranked text chunks for each question.
- **Two sources of knowledge are clearly separated** in the Claude system
  prompt: corpus (cited inline as `[#N]`) vs. legal expertise
  (uncited). Claude is also instructed to flag suspicious patterns
  proactively and to caveat OCR uncertainty.
- **OCR runs only on demand** — born-digital PDFs (the majority of the
  corpus) skip PaddleOCR entirely and use PyMuPDF's text layer for
  perfect fidelity on dollar amounts, dates, and account numbers.
- **Chunking is structural, not semantic-LLM-based.** This was a
  deliberate choice for legal evidence: paragraph-respecting chunks with
  a metadata header preserve full citation provenance and don't depend
  on an extra LLM round-trip.

---

## Troubleshooting

| Symptom                                             | Fix                                                                                |
| --------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `paddlepaddle` install fails on Windows             | `pip install paddlepaddle==2.6.1 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/` |
| First `extract_attachment_text.py` run is slow      | Normal — PaddleOCR is downloading models. Subsequent runs reuse them.              |
| `pymongo.errors.OperationFailure: $vectorSearch`    | The Atlas index isn't ACTIVE yet. Wait, then re-run.                                |
| `chat.py` says `ANTHROPIC_API_KEY is missing`        | Add the key to `.env` under `ANTHROPIC_API_KEY`.                                    |
| `voyageai.error.RateLimitError`                     | Built-in retry will handle bursts; if persistent, lower `--batch-size` to 32.       |
| Re-embed is taking forever                          | Use `--force` selectively (e.g., `--emails-only`) or run on a subset with `--limit`.|
