import config.settings  # noqa
from collections import Counter
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name); db=m.db
docs=db["documents"]
print("TOTAL documents:",docs.count_documents({}))
print("\n-- by corpus --")
for c,n in Counter(d.get("corpus") for d in docs.find({},{"corpus":1})).most_common():
    print(f"  {c!r}: {n}")
print("\n-- by custody.origin --")
for c,n in Counter((d.get("custody") or {}).get("origin") for d in docs.find({},{"custody.origin":1})).most_common():
    print(f"  {c!r}: {n}")
print("\n-- by source_type --")
for c,n in Counter(d.get("source_type") for d in docs.find({},{"source_type":1})).most_common():
    print(f"  {c!r}: {n}")
m.close()
