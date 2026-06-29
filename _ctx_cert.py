"""Definitive proof: every phase5 doc + every chunk has a contextual summary."""
import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
docs = m.db["documents"]
ch = m.db["email_chunks_v2"]

total_docs = docs.count_documents({"_id": {"$regex": "^doc_p5_"}})
chunked_docs = docs.count_documents({"_id": {"$regex": "^doc_p5_"}, "chunked_at": {"$exists": True}})
total_chunks = ch.count_documents({"document_id": {"$regex": "^doc_p5_"}})

# chunks lacking a usable contextual summary (missing / null / empty / whitespace)
missing_field = ch.count_documents({"document_id": {"$regex": "^doc_p5_"}, "context": {"$exists": False}})
null_ctx = ch.count_documents({"document_id": {"$regex": "^doc_p5_"}, "context": None})
empty_ctx = ch.count_documents({"document_id": {"$regex": "^doc_p5_"}, "context": ""})
ws_ctx = ch.count_documents({"document_id": {"$regex": "^doc_p5_"},
                             "context": {"$regex": r"^\s*$"}})

# per-doc: any doc that has chunks but ALL of them are blank?
pipeline = [
    {"$match": {"document_id": {"$regex": "^doc_p5_"}}},
    {"$group": {"_id": "$document_id",
                "n": {"$sum": 1},
                "with_ctx": {"$sum": {"$cond": [{"$gt": [{"$strLenCP": {"$ifNull": ["$context", ""]}}, 0]}, 1, 0]}}}},
]
docs_no_ctx = 0
docs_partial = 0
for r in ch.aggregate(pipeline):
    if r["with_ctx"] == 0:
        docs_no_ctx += 1
    elif r["with_ctx"] < r["n"]:
        docs_partial += 1

print("=== PHASE-5 CONTEXTUAL SUMMARY CERTIFICATE ===")
print(f"phase5 docs total            : {total_docs}")
print(f"phase5 docs chunked          : {chunked_docs}")
print(f"phase5 chunks total          : {total_chunks}")
print("--- chunk-level context gaps ---")
print(f"missing 'context' field      : {missing_field}")
print(f"null context                 : {null_ctx}")
print(f"empty-string context         : {empty_ctx}")
print(f"whitespace-only context      : {ws_ctx}")
print("--- doc-level coverage ---")
print(f"docs with NO ctx on any chunk: {docs_no_ctx}")
print(f"docs partially missing ctx   : {docs_partial}")

ok = (total_docs == chunked_docs and missing_field == 0 and null_ctx == 0
      and empty_ctx == 0 and ws_ctx == 0 and docs_no_ctx == 0 and docs_partial == 0)
print("\nRESULT:", "PASS - every doc & every chunk has a contextual summary" if ok else "FAIL")
m.close()
