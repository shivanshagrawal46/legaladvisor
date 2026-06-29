import config.settings  # noqa
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from collections import Counter
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name)
docs=m.db["documents"]
q={"source_type":"title_report","custody.origin":"missing_title_reports"}
meth=Counter(); ndocs=0; bad=[]
for d in docs.find(q,{"extraction_method":1}):
    ndocs+=1; em=d.get("extraction_method") or {}
    for k,v in em.items(): meth[k]+=v
    if any(k not in ("claude_vision","openai_vision") for k in em): bad.append(d["_id"])
print("missing-title docs:",ndocs)
print("page methods:",dict(meth))
print("NON-frontier docs:",len(bad), bad[:10])
m.close()
