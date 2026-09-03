"""Read-only inventory of what has been ingested from PACER."""
from __future__ import annotations

import sys

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main() -> int:
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    docs, ents, chunks = m.db["documents"], m.db["entities"], m.db["email_chunks_v2"]

    print("=== landscape: all court_record docs by (instrument_subtype, origin) ===")
    for r in docs.aggregate([
        {"$match": {"source_type": "court_record"}},
        {"$group": {"_id": {"sub": "$instrument_subtype",
                            "origin": "$custody.origin"},
                    "n": {"$sum": 1}}},
        {"$sort": {"n": -1}},
    ]):
        print(f"  {str(r['_id']['sub']):<22} {str(r['_id']['origin']):<34} {r['n']:>5}")

    print("\n=== case entities with source=pacer ===")
    roster = list(ents.find({"kind": "case", "source": "pacer"}))
    for e in roster:
        print(f"  {e['_id']}")
        print(f"      case_number : {e.get('case_number')}")
        print(f"      name        : {e.get('canonical_name')}")
        print(f"      court       : {e.get('court')}")
        print(f"      aliases     : {e.get('aliases')}")
    print(f"  -> {len(roster)} case entities")

    print("\n=== any other case entities (non-pacer), for contrast ===")
    for r in ents.aggregate([
        {"$match": {"kind": "case"}},
        {"$group": {"_id": "$source", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}},
    ]):
        print(f"  source={str(r['_id']):<20} {r['n']:>4}")

    q = {"source_type": "court_record", "custody.origin": {"$regex": "^pacer"}}
    print("\n=== PACER documents per case ===")
    rows = list(docs.aggregate([
        {"$match": q},
        {"$group": {"_id": {"num": "$case_number", "title": "$case_title",
                            "court": "$court"},
                    "n": {"$sum": 1},
                    "pages": {"$sum": "$page_count"},
                    "chunked": {"$sum": {"$cond": [
                        {"$ifNull": ["$chunked_at", False]}, 1, 0]}},
                    "nchunks": {"$sum": {"$ifNull": ["$chunk_count", 0]}},
                    "thin": {"$sum": {"$cond": [
                        {"$eq": ["$quality.needs_review", True]}, 1, 0]}},
                    "first": {"$min": "$document_date"},
                    "last": {"$max": "$document_date"}}},
        {"$sort": {"n": -1}},
    ]))
    td = tp = tc = 0
    for r in rows:
        k = r["_id"]
        print(f"\n  case_number : {k['num']}")
        print(f"  title       : {k['title']}")
        print(f"  court       : {k['court']}")
        print(f"  documents   : {r['n']}   pages={r['pages']}   thin={r['thin']}")
        print(f"  chunked     : {r['chunked']}/{r['n']}   chunks={r['nchunks']}")
        print(f"  date range  : {k and r['first']} .. {r['last']}")
        td += r["n"]
        tp += r["pages"]
        tc += r["nchunks"]
    print(f"\n  TOTAL: cases={len(rows)} documents={td} pages={tp} chunks={tc}")

    print(f"\ntotal PACER docs (origin ^pacer)         : {docs.count_documents(q)}")
    print("total bankruptcy_filing docs             : "
          f"{docs.count_documents({'instrument_subtype': 'bankruptcy_filing'})}")
    print("docs with _id prefix doc_pacer           : "
          f"{docs.count_documents({'_id': {'$regex': '^doc_pacer'}})}")
    print("chunks (instrument_subtype=bankruptcy)   : "
          f"{chunks.count_documents({'instrument_subtype': 'bankruptcy_filing'})}")

    m.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
