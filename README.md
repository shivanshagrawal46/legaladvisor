# PST Email RAG — Phase 1: Ingestion

Extracts every email + attachment from an Outlook PST file into MongoDB Atlas
in a clean, structured, query-ready format. Phase 1 of a larger
RAG-with-Claude pipeline for legal/fraud-case email analysis.

## What gets stored

| Collection | Contents |
|---|---|
| `emails` | One document per message (subject, headers, parsed addresses, cleaned body, raw bodies, thread keys, folder, dates, importance, headers) |
| `attachments` | Metadata per file (filename, content type, size, SHA-256, GridFS ref) |
| `attachment_files.*` | Binary attachment blobs (GridFS bucket) |
| `folders` | Distinct PST folder paths with email counts |
| `ingestion_runs` | Per-run audit log (PST sha256, totals, status) |
| `ingestion_errors` | Per-message errors with stack traces |

The `body_text` field is the **cleaned** version (HTML stripped, signatures
+ quoted reply chains + "Sent from my iPhone" + standard footers removed).
The original is preserved in `body_text_raw` and `body_html`.

## Setup

### 1. Install Python dependencies
```powershell
python -m pip install -r requirements.txt
```

### 2. Configure `.env`
Copy and fill in:
```powershell
Copy-Item .env.example .env
```

Required values:
- `MONGO_URI` — your MongoDB Atlas SRV connection string
- `MONGO_DB_NAME` — defaults to `fraud_emails`
- `PST_FILE_PATH` — defaults to `Gmail Lawsuit Exportes Email.pst`

### 3. (Optional) Smoke-test without touching MongoDB
```powershell
python ingest.py --dry-run --limit 20
```

### 4. Run the full ingestion
```powershell
python ingest.py
```

To re-run from scratch (drops emails/attachments first):
```powershell
python ingest.py --reset
```

## Project layout
```
outlook_attachments/
├── ingest.py                  # CLI entry point
├── config/
│   └── settings.py            # .env loader
├── src/
│   ├── parser/                # libratom-based PST walker
│   ├── cleaner/               # HTML strip + signature/quote/footer removal
│   ├── db/                    # MongoDB client, repositories, schemas
│   ├── pipeline/              # End-to-end ingestion orchestrator
│   └── utils/                 # logger, hashing, address parsing
├── logs/
└── requirements.txt
```

## Design notes

- **Idempotent**: re-running on the same PST does not duplicate data
  (`pst_entry_id` is unique per message).
- **GridFS for attachments** — handles files >16MB transparently;
  binaries never inflate the email document size.
- **Both raw and cleaned bodies stored** — cleaned for retrieval, raw kept
  for verification when answering legal questions.
- **Per-message error isolation** — one bad email never aborts the run.
- **Indexes** — created automatically; cover the access patterns we'll need
  in later phases (sender, recipient, date, folder, thread, content hash,
  full-text on subject + body).

Phase 2 will add embeddings + retrieval + Claude chat on top of these
collections — without needing to reparse the PST.
