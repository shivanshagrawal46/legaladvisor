import os, json
import config.settings  # noqa
from collections import Counter
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name)
docs=m.db["documents"]
roots=Counter(); samples=[]
for d in docs.find({"source_type":"title_report","extraction_method.ocr":{"$gt":0}},
                   {"custody.source_files":1}):
    for f in ((d.get("custody") or {}).get("source_files") or []):
        if isinstance(f,dict):
            p=f.get("source_path") or f.get("path") or f.get("name") or ""
        else:
            p=str(f)
        if p:
            if len(samples)<5: samples.append(p)
            parts=p.replace("/","\\").split("\\")
            roots[parts[0] if parts else "?"]+=1
print("source_files path roots:",dict(roots))
print("samples:")
for sp in samples: print("  ",repr(sp),"exists=",os.path.exists(sp))
m.close()
