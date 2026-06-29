import os
import config.settings  # noqa
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name)
docs=m.db["documents"]
ids=["doc_tr_687705_285b3d62","doc_tr_687696_4ec80650","doc_tr_687703_7d9fff14","doc_tr_687699_f4f2af99"]
n_have=0; n_total=0; missing=0
for d in docs.find({"source_type":"title_report","extraction_method.ocr":{"$gt":0}},
                   {"custody":1}):
    n_total+=1
    c=d.get("custody") or {}
    paths=[]
    if c.get("source_path"): paths.append(c["source_path"])
    for f in (c.get("source_files") or []):
        if isinstance(f,dict) and f.get("source_path"): paths.append(f["source_path"])
        elif isinstance(f,dict) and f.get("path"): paths.append(f["path"])
    exists=any(os.path.exists(p) for p in paths)
    if exists: n_have+=1
    else: missing+=1
print(f"title docs with ocr pages (dict method)={n_total}")
print(f"  source file present on disk={n_have}  MISSING={missing}")
# sample paths
for d in docs.find({"source_type":"title_report","extraction_method.ocr":{"$gt":0}},{"custody":1}).limit(4):
    c=d.get("custody") or {}
    print(" path:",repr(c.get("source_path")), "exists=",os.path.exists(c.get("source_path") or ""))
m.close()
