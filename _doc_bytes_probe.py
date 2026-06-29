import config.settings  # noqa
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name)
print("collections:",sorted(m.db.list_collection_names()))
docs=m.db["documents"]
d=docs.find_one({"source_type":"title_report"})
keys=sorted(d.keys())
print("\nsample title doc fields:",keys)
cust=d.get("custody") or {}
print("custody keys:",sorted(cust.keys()))
for k in ("gridfs_id","file_id","attachment_id","pdf_id","original_bytes","stored_pdf"):
    print("  has",k,":",k in d or k in cust)
print("source_files sample:",(cust.get("source_files") or [None])[0])
# attachments_v2?
for c in ("attachments_v2","attachments","fs.files"):
    if c in m.db.list_collection_names():
        print(c,"count:",m.db[c].count_documents({}))
m.close()
