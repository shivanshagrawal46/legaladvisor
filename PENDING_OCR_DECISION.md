# PENDING DECISION — Born-Digital PDFs in `fraud_communications`

**Status:** OPEN — to be decided at the very end of the project.
**Logged:** 2026-06-26

## Context

The `fraud_communications` corpus contains born-digital PDF attachments whose
text was taken from the PDF's native text layer (`method = text_layer`) rather
than frontier vision OCR. They are tagged `extracted_via = vision_v2` (the
pipeline name) but the per-page method is `text_layer`, so **no Claude/GPT-5
image was ever sent for these pages.**

Total born-digital fraud docs with `text_layer` pages: **337** (1,249 pages).

| Bucket | extraction.method | Count | Decision |
|---|---|---|---|
| Pure born-digital | `pdf_text` | **310** | **DEFERRED — decide at end** |
| Mixed (some scanned pages) | `pdf_mixed` | **27** | DONE — force-visioned (Option 1) |

## Why the 310 are deferred (not done now)

A/B test on 4 sample born-digital fraud PDFs (native text vs fresh Claude
Vision on the same bytes):

- Vision produced ~2x the characters, BUT **0 new words/numbers** in 3 of 4 docs
  (only 1 token in the 4th).
- The extra characters were **layout / whitespace / table structure**, not new
  facts. Every dollar amount, address, and number was already in the native text.
- Conclusion: unlike the scanned-doc case (where native lost ~89%), these
  born-digital PDFs already have a **complete, reliable text layer**. No factual
  content is being lost.

So OCR'ing them would improve table layout/structure but recover **no missing
facts**. Decision deferred to end-of-project to weigh cost vs. uniformity.

## What to run if we decide YES (OCR the 310)

Force-vision OCR these 310 `pdf_text` fraud docs, then re-chunk + re-embed +
re-enrich + audit — same proven flow used for the lawyer corpus and the 27
mixed docs.

To select them: fraud-corpus sha where `extraction.method == 'pdf_text'` and a
page method is `text_layer`.
