"""OCR engine audit for the ingested NYSCEF corpus."""
from __future__ import annotations

import sys

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
docs = m.db["documents"]
q = {"instrument_subtype": "nyscef_efiled"}

print("total nyscef docs:", docs.count_documents(q))
print("missing engine policy:", docs.count_documents(
    {**q, "ocr_engine_policy": {"$exists": False}}))
print("docs with untranscribed pages:", docs.count_documents(
    {**q, "ocr_failed_pages": {"$gt": 0}}))

engines = {}
for d in docs.find(q, {"ocr_page_methods": 1}):
    for k, v in (d.get("ocr_page_methods") or {}).items():
        engines[k] = engines.get(k, 0) + v
print("\npages by engine across the whole corpus:")
for k, v in sorted(engines.items(), key=lambda kv: -kv[1]):
    print(f"  {k:<24} {v:,}")
bad = [k for k in engines if "rapid" in k.lower() or k == "ocr"]
print("\nRapidOCR pages:", sum(engines[k] for k in bad) if bad else 0)

print("\ntarget parties across the FULL corpus:")
rows = docs.aggregate([
    {"$match": q}, {"$unwind": "$target_parties"},
    {"$group": {"_id": "$target_parties", "cases": {"$addToSet": "$case_number"},
                "n": {"$sum": 1}}},
    {"$sort": {"n": -1}}])
seen = set()
for r in rows:
    seen.add(r["_id"])
    print(f"  {r['_id']:<38} docs={r['n']:<4} cases={sorted(r['cases'])}")
from scripts.ingest_webcivil import TARGET_PARTIES
missing = [p for p in TARGET_PARTIES if p not in seen]
print("\nNOT found anywhere:", missing or "none")

thin = list(docs.find({**q, "quality.needs_review": True},
                      {"case_number": 1, "document_title": 1, "page_count": 1,
                       "ocr_failed_pages": 1, "extracted_text": 1}))
print(f"\nflagged for review: {len(thin)}")
for d in thin[:15]:
    print(f"  {d['_id']} {d.get('case_number')} {str(d.get('document_title'))[:30]:<30} "
          f"pages={d.get('page_count')} failed={d.get('ocr_failed_pages')} "
          f"chars={len(d.get('extracted_text') or '')}")
m.close()
