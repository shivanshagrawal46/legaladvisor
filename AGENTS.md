# Ingestion rules for this corpus

Standing instructions from the owner. These are not defaults to re-derive each
session — they are decisions already made. Follow them without asking.

## OCR: PDFs go through vision, always

**Every PDF attachment is OCR'd by Claude Sonnet 4.6 Vision, with GPT-5 vision
as the fallback. Never accept the born-digital text layer for a PDF.**

    python -m scripts.ocr_attachments_v2 --sha-file <shas.txt> --force-vision --workers N

`--force-vision` sets the text-layer threshold impossibly high so every page is
routed to vision. Without it the extractor silently falls back to `pdf_text` for
born-digital PDFs, which violates this rule. If a PDF was already extracted the
wrong way, re-run with `--force --force-vision` to overwrite the
`attachments_v2` row.

Check the reported `methods={...}`: a PDF must show `pdf_ocr`, never `pdf_text`.

**DOCX / XLSX / TXT stay native.** Vision on a Word file would rasterise text
that is already exact. Only PDFs and images go to vision. So when a batch mixes
types, split the SHA scope: DOCX in a normal run, PDFs in a `--force-vision` run.

## Chunking and embedding

1000 tokens, 200 overlap. Contextual summary per chunk from Claude Sonnet 4.6
(hardcoded in `build_email_chunks_v2.py`), prepended into the embedded text.
Embeddings are `voyage-4-large`, 1024-d. Set `CONTEXT_BATCH_SIZE=8` — the
default of 1 makes one API call per chunk and is the bottleneck on large docs.

## Enrichment order (order matters)

1. `_boris_enrich.py` — authority score + scope keys
2. `scripts/tag_chunk_corpus.py` — corpus/privilege defaults. Only touches
   chunks with no `corpus`, so stamp any non-default classification BEFORE this
   or the blanket `privileged` default will win.
3. `python -m scripts.link_new_chunks --apply` — entity linkage.
   Use this, NOT `backfill_chunk_entities.py --sha-file`: that one scopes on
   `{"sha256": {"$in": ...}}`, and email bodies have no `sha256`, so body chunks
   are silently skipped.
4. Stamp `matter_id` — the chunker does not propagate it from the parent email
   (missing on ~44% of the corpus).

## Known gaps to work around

- The Boris sweep's `att=` column under-reports. Always confirm attachments by
  reading the raw MIME (`client.get_raw`) before concluding an email has none.
- The entity graph has no records for Schuman, Marie Holdings, Westerman LLP,
  Heuer, or Campisi, so correspondence naming them links to nothing.
- "MangoTree" resolves to `ent_prop_a_mangotree`, a *property* entity, and is
  fragmented across eight separate entities.

## Document versions

Counsel reuses filenames across revisions (`Draft Brief -- IPA Sanctions.docx`
exists at two different SHAs). When a new version lands, mark the older one
`is_superseded=True` with `superseded_by` pointing at the new SHA, and drop its
authority, so retrieval prefers the current draft.
