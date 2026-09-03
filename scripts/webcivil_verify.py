"""Final acceptance check for the WebCivil/NYSCEF ingest.

Confirms every downloaded PDF made it through OCR -> chunk -> contextual
summary -> voyage-4-large embedding, and that the chunks are actually
retrievable from the live vector index.
"""
from __future__ import annotations

import sys
from pathlib import Path

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

ROOT = Path(r"E:\WEBCIVIL")
CHUNKS = "email_chunks_v2"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main() -> int:
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    docs, chunks = m.db["documents"], m.db[CHUNKS]
    q = {"instrument_subtype": "nyscef_efiled"}
    fails = []

    on_disk = {p.name for p in ROOT.rglob("*.pdf")}
    stored = {(d.get("custody") or {}).get("source_files", [None])[0]
              for d in docs.find(q, {"custody.source_files": 1})}
    missing = on_disk - stored
    print(f"1. every PDF ingested            : {len(on_disk) - len(missing)}/{len(on_disk)}")
    if missing:
        fails.append(f"{len(missing)} PDFs never ingested")
        for n in list(missing)[:5]:
            print("     MISSING:", n)

    n_docs = docs.count_documents(q)
    n_chunked = docs.count_documents({**q, "chunked_at": {"$exists": True}})
    print(f"2. every doc chunked+embedded    : {n_chunked}/{n_docs}")
    if n_chunked != n_docs:
        fails.append("some documents were never chunked")

    n_fail_pages = docs.count_documents({**q, "ocr_failed_pages": {"$gt": 0}})
    print(f"3. docs with untranscribed pages : {n_fail_pages}")
    if n_fail_pages:
        fails.append(f"{n_fail_pages} docs have untranscribed pages")

    ids = [d["_id"] for d in docs.find(q, {"_id": 1})]
    n_ch = chunks.count_documents({"document_id": {"$in": ids}})
    n_emb = chunks.count_documents({"document_id": {"$in": ids},
                                    "embedding_model": "voyage-4-large",
                                    "embedding.0": {"$exists": True}})
    n_ctx = chunks.count_documents({"document_id": {"$in": ids},
                                    "context": {"$nin": ["", None]}})
    print(f"4. chunks with voyage-4-large vec: {n_emb}/{n_ch}")
    print(f"5. chunks with contextual summary: {n_ctx}/{n_ch}")
    if n_emb != n_ch:
        fails.append("some chunks have no embedding")
    if n_ctx != n_ch:
        fails.append(f"{n_ch - n_ctx} chunks have no contextual summary")

    one = chunks.find_one({"document_id": {"$in": ids}})
    dim = len(one.get("embedding") or []) if one else 0
    print(f"6. embedding dimension           : {dim}")
    if dim != 1024:
        fails.append(f"unexpected embedding dim {dim}")

    # Live retrieval against the Atlas vector index.
    print("\n7. live vector search for 'IPA Asset Management fraudulent conveyance':")
    try:
        from src.rag.embedder import VoyageEmbedder
        emb = VoyageEmbedder(s.voyage_api_key, model="voyage-4-large")
        vec = emb.embed_query("IPA Asset Management fraudulent conveyance of property")
        hits = list(chunks.aggregate([
            {"$vectorSearch": {"index": "email_chunks_v2_vector",
                               "path": "embedding", "queryVector": vec,
                               "numCandidates": 400, "limit": 5,
                               "filter": {"source_type": {"$eq": "court_record"}}}},
            {"$project": {"case_number": 1, "document_title": 1, "context": 1,
                          "document_id": 1,
                          "score": {"$meta": "vectorSearchScore"}}},
        ]))
        if not hits:
            fails.append("vector search returned nothing")
        for h in hits:
            d = docs.find_one({"_id": h["document_id"]},
                              {"case_number": 1, "document_title": 1})
            tag = "NYSCEF" if str(h["document_id"]).startswith("doc_webcivil_") else "other"
            print(f"   [{tag}] {h['score']:.4f} {(d or {}).get('case_number','?'):<14} "
                  f"{str((d or {}).get('document_title',''))[:34]:<34} "
                  f"{(h.get('context') or '')[:70]}")
    except Exception as exc:  # noqa: BLE001
        print("   vector search failed:", str(exc)[:200])
        fails.append("vector search failed")

    print("\n" + "=" * 64)
    if fails:
        print("ISSUES:")
        for f in fails:
            print("  -", f)
    else:
        print("ALL CHECKS PASSED — corpus is complete and retrievable.")
    m.close()
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
