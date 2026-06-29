import collections

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
docs = m.db["documents"]

# docs whose stored source file came from phase5_staging (the unpacked archives)
stored = list(docs.find({"custody.source_files": {"$regex": "phase5_staging", "$options": "i"}},
                        {"doc_category": 1, "pages": 1, "bates_start": 1,
                         "occurrences": 1, "extraction_method": 1}))
print(f"archive docs STORED from staging: {len(stored)}")
cat = collections.Counter()
meth = collections.Counter()
for d in stored:
    cat[d.get("doc_category")] += 1
    for p in (d.get("pages") or []):
        meth[p.get("method")] += 1
print("categories:", dict(cat))
print("page methods:", dict(meth))

# occurrence-linked (content already in DB, archive path recorded on existing record)
linked = docs.count_documents({"phase5_occurrences.rel": {"$regex": "MANGOTREE|Settlement sheets", "$options": "i"}})
linked_att = m.db["attachments_v2"].count_documents({"phase5_occurrences.rel": {"$regex": "MANGOTREE|Settlement sheets", "$options": "i"}})
print(f"archive content occurrence-linked onto existing docs={linked} attachments={linked_att}")

# sample a few
print("--- samples ---")
for d in stored[:6]:
    src = (d.get("occurrences") or [{}])[0].get("rel", "")
    print(f"   {d.get('bates_start')} {d.get('doc_category'):16s} {src[:60]}")
m.close()
