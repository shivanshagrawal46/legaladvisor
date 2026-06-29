import config.settings  # noqa
from collections import Counter
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name)
docs=m.db["documents"]
proj={"extraction_method":1,"page_count":1,"num_pages":1,"custody":1,"property_address":1}
def methods(d):
    em=d.get("extraction_method")
    if isinstance(em,dict): return em
    if isinstance(em,str) and em: return {em:1}
    return {}
def has_rapid(d): return any(k in ("ocr","rapidocr") for k in methods(d))
origins=Counter(); n=0
for d in docs.find({"source_type":"title_report"},proj):
    if not has_rapid(d): continue
    c=d.get("custody") or {}
    srcs=c.get("source_files") or []
    has_path=any((isinstance(f,dict) and (f.get("source_path") or f.get("path"))) for f in srcs) or bool(c.get("source_path"))
    if has_path: continue
    n+=1
    origins[c.get("origin") or "?"]+=1
    if n<=22:
        print(d["_id"][:28],"| origin=",c.get("origin"),"| addr=",repr(d.get("property_address")),"| ocr_pages=",methods(d).get("ocr",0))
print("UNMATCHED_COUNT:",n,"origins:",dict(origins),flush=True)
m.close()
