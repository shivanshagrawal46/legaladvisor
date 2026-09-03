"""End-to-end retrieval check over the WebCivil corpus.

Embeds a real question with Voyage and runs it through the Atlas vector index,
so this exercises the same path a user query takes.
"""
import argparse

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.rag.embedder import VoyageEmbedder

QUERIES = [
    "IPA Asset Management LLC service of process affidavit Suffolk County",
    "David DeRosa deed transfer of property ownership",
    "notice of foreclosure sale surplus money proceeding",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", default=None)
    args = ap.parse_args()

    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    ch = m.db["email_chunks_v2"]
    emb = VoyageEmbedder(s.voyage_api_key)

    print(f"index: {s.rag_v2_vector_index_name}\n")
    for q in ([args.query] if args.query else QUERIES):
        qv = emb.embed_query(q)
        pipe = [{"$vectorSearch": {"index": s.rag_v2_vector_index_name,
                                   "path": "embedding", "queryVector": qv,
                                   "numCandidates": 400, "limit": 4,
                                   "filter": {"source_type": "court_record"}}},
                {"$project": {"score": {"$meta": "vectorSearchScore"},
                              "case_number": 1, "document_title": 1,
                              "source_filename": 1, "touches_david": 1,
                              "entity_ids": 1, "court": 1, "text": 1}}]
        print(f'Q: "{q}"')
        for i, r in enumerate(ch.aggregate(pipe), 1):
            print(f"  {i}. score={r['score']:.4f}  {r.get('case_number')}  "
                  f"{r.get('document_title')}  david={r.get('touches_david')}  "
                  f"entities={len(r.get('entity_ids') or [])}")
            print(f"     {r.get('source_filename')}")
            print(f"     {(r.get('text') or '')[:130]}")
        print()
    m.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
