import config.settings  # noqa
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name)
db=m.db
f=db["attachment_files.files"].find_one()
print("attachment_files.files sample keys:",sorted((f or {}).keys()))
if f: print("  metadata:",f.get("metadata"),"| filename:",f.get("filename"))
a=db["attachments_v2"].find_one()
print("attachments_v2 sample keys:",sorted((a or {}).keys()))
if a: print("  sha?:",a.get("sha256"),"| gridfs?:",a.get("gridfs_id") or a.get("file_id"),"| ct:",a.get("content_type"))
# a discovery/phase5 doc
for q in [{"_id":{"$regex":"^doc_p5"}},{"source_type":"insurance"},{"source_type":{"$ne":"title_report"}}]:
    d=db["documents"].find_one(q)
    if d:
        print("\nNON-title doc",d["_id"],"type=",d.get("source_type"))
        print("  custody:",{k:v for k,v in (d.get("custody") or {}).items() if k!='source_files'})
        print("  source_files:",(d.get("custody") or {}).get("source_files"))
        print("  has text:",bool(d.get("extracted_text")),"len:",len(d.get("extracted_text") or ""))
        for k in ("sha256","attachment_id","gridfs_id","email_id"):
            print("   field",k,":",d.get(k))
        break
m.close()
