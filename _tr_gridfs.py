import config.settings  # noqa
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name)
docs=m.db["documents"]
shas=[]
for d in docs.find({"source_type":"title_report","extraction_method.ocr":{"$gt":0}},{"custody":1}):
    c=d.get("custody") or {}
    if c.get("sha256"): shas.append(c["sha256"])
print("docs with sha:",len(shas))
# check attachments_v2
v2=m.db["attachments_v2"]
in_v2=v2.count_documents({"sha256":{"$in":shas}})
print("present in attachments_v2 by sha:",in_v2)
# check gridfs files collection
cols=m.db.list_collection_names()
print("has fs.files:", "fs.files" in cols, "| has gridfs:", any("files" in c for c in cols))
# does documents store raw bytes / gridfs_id?
d=docs.find_one({"source_type":"title_report","extraction_method.ocr":{"$gt":0}},{"custody":1,"gridfs_id":1,"raw_bytes":1,"source_path":1})
print("sample keys present:", {k:(d.get(k) is not None) for k in ("gridfs_id","raw_bytes")}, "custody keys:", list((d.get("custody") or {}).keys()))
m.close()
