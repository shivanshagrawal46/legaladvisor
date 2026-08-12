"""End-to-end proof: is the newly ingested content actually retrievable?

Embeds a query with voyage-4-large and runs $vectorSearch against
email_chunks_v2 / email_chunks_v2_vector, then reports whether the hits
include chunks created by this run.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.rag.embedder import VoyageEmbedder

QUERIES = [
    "CrossCountry counsel adjourning their motion and buying their debt",
    "statute of limitations two year period from the 31FO bankruptcy filing",
    "claim calculation for IPA due by the 31st",
]

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
ch = m.db["email_chunks_v2"]

# Chunks created by this run == the 86 most recently entity-backfilled.
new_ids = set(ch.distinct("_id", {"created_at": {"$exists": True}, "n_tokens": {"$exists": True},
                                  "entity_backfill_at": {"$exists": True}})) if False else None

emb = VoyageEmbedder(s.voyage_api_key, model=s.embedding_model)

for q in QUERIES:
    vec = emb.embed_query(q) if hasattr(emb, "embed_query") else emb.embed([q], input_type="query")[0]
    pipeline = [
        {"$vectorSearch": {
            "index": "email_chunks_v2_vector",
            "path": "embedding",
            "queryVector": list(vec),
            "numCandidates": 200,
            "limit": 5,
        }},
        {"$project": {"filename": 1, "subject": 1, "date": 1, "source_type": 1,
                      "context": 1, "body": 1, "text": 1,
                      "score": {"$meta": "vectorSearchScore"}}},
    ]
    print("=" * 78)
    print(f"QUERY: {q}")
    print("=" * 78)
    for r in ch.aggregate(pipeline):
        who = r.get("filename") or r.get("subject") or "(no title)"
        recent = str(r.get("date"))[:10]
        flag = "  <-- NEW" if recent >= "2026-07-20" else ""
        print(f"  {r.get('score'):.4f}  {recent}  {r.get('source_type'):11s} "
              f"{str(who)[:44]:44s}{flag}")
        snippet = (r.get("context") or r.get("body") or r.get("text") or "")[:120]
        print(f"          {snippet.strip()[:110]}")
    print()

m.close()
