import config.settings  # noqa
from collections import Counter
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name); db=m.db
av=db["attachments_v2"]
print("attachments_v2 total:",av.count_documents({}))
sample=av.find_one({})
print("sample keys:",sorted(sample.keys()))
print("extraction sample:",sample.get("extraction"),"| extracted_via:",sample.get("extracted_via"))
# how is corpus identified? check emails
em=db["emails"]; e=em.find_one({})
print("\nemail keys:",sorted(e.keys()))
for f in ("corpus","folder","mailbox","account","source","pst"):
    vals=Counter(x.get(f) for x in em.find({},{f:1}).limit(99999))
    if any(k is not None for k in vals): print(f"email.{f}:",dict(list(vals.items())[:8]))
m.close()
