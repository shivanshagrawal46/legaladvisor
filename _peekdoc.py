import config.settings  # noqa
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name)
docs=m.db["documents"]
d=docs.find_one({"_id":"doc_tr_687694_0c5e2213"})
print("KEYS:",sorted(d.keys()))
print("extraction_method:",d.get("extraction_method"))
print("page_count:",d.get("page_count"),"num_pages:",d.get("num_pages"))
print("has pages array:", isinstance(d.get("pages"),list), "len:", len(d.get("pages") or []))
t=d.get("extracted_text") or ""
print("text len:",len(t))
import re
# look for page markers
for pat in ["\f","--- Page","[Page","Page ","\n\n=== "]:
    print(repr(pat),"count:",t.count(pat))
print("HEAD:",repr(t[:400]))
m.close()
