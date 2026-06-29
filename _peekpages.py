import config.settings  # noqa
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name)
docs=m.db["documents"]
d=docs.find_one({"_id":"doc_tr_687694_0c5e2213"},{"pages":1})
pgs=d["pages"]
print("element type:",type(pgs[0]).__name__)
if isinstance(pgs[0],dict):
    print("page0 keys:",sorted(pgs[0].keys()))
    for p in pgs:
        meth=p.get("method") or p.get("ocr_method")
        if meth not in ("claude_vision",):
            print("  NONFRONTIER page:",{k:(v if k!='text' else f'<{len(v or "")} chars>') for k,v in p.items()})
else:
    print("sample:",repr(pgs[0])[:300])
# how is extracted_text reconstructed? check join
m.close()
