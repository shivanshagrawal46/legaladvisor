"""Regenerate the contextual summary for any phase-3 chunk whose `context`
is empty (summary call had failed). Re-summarize that chunk in its document
context, rebuild the embed text, and re-embed — so the chunk is fully equal
to all the others. Safe to run while the main pipeline runs (these chunks
live in already-stamped docs, never in the pending queue)."""
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.rag.tokens import count_tokens
from src.rag.embedder import VoyageEmbedder
from src.rag.v2.contextual_summary import ContextualSummarizer

T = ["title_report", "insurance", "equity_schedule", "service_agreement", "litigation_update"]
s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
d, ch = m.db["documents"], m.db["email_chunks_v2"]
summarizer = ContextualSummarizer(s.anthropic_api_key, model="claude-sonnet-4-6")
embedder = VoyageEmbedder(s.voyage_api_key, model="voyage-4-large")

bad = list(ch.find({"source_type": {"$in": T},
                    "$or": [{"context": {"$exists": False}}, {"context": ""}]}))
print(f"chunks needing context: {len(bad)}")
fixed = 0
for c in bad:
    doc = d.find_one({"_id": c["document_id"]}, {"extracted_text": 1})
    doc_text = (doc or {}).get("extracted_text") or ""
    body = c.get("body") or ""
    summary = ""
    try:
        summary = summarizer.summarize_doc_chunks(doc_text, [body])[0]
    except Exception as exc:  # noqa: BLE001
        print(f"  {c['_id']}: summary retry failed: {str(exc)[:80]}")
    if not summary:
        print(f"  {c['_id']}: still empty, skipping")
        continue
    # rebuild embed text exactly like the main pipeline, then re-embed
    full = body
    header = c.get("text", "").split("\n\n", 1)[0] if c.get("text") else ""
    if header.startswith("[") and not body.startswith(header):
        full = f"{header}\n\n{body}"
    embed_text = f"[Context] {summary}\n\n{full}"
    vec = embedder.embed_documents([embed_text])[0]
    ch.update_one({"_id": c["_id"]}, {"$set": {
        "context": summary, "text": embed_text,
        "embedding": vec, "n_tokens": count_tokens(embed_text)}})
    fixed += 1
    print(f"  fixed {c['_id']}")

remaining = ch.count_documents({"source_type": {"$in": T},
                                "$or": [{"context": {"$exists": False}}, {"context": ""}]})
print(f"fixed={fixed} | chunks still missing context: {remaining}")
m.close()
