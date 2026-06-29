import hashlib, os
from datetime import datetime, timezone
import config.settings  # noqa
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()
pairs=[
 (r"E:\missing title reports\31 Fort Hill Dr Lloyd Harbor Ny\31 Fort Hill Dr_Update Search.pdf","doc_pw_83709870d9d9cfa4"),
 (r"E:\missing title reports\83 Ann Dr S Freeport Ny\83 S Ann Drive_Update Search 2026.pdf","doc_pw_801a7fa4df1dbdc1"),
]
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name)
docs=m.db["documents"]; now=datetime.now(timezone.utc)
for fp,target in pairs:
    sh=sha(fp); sz=os.path.getsize(fp)
    occ={"sha256":sh,"source_path":fp,"path":fp,"bytes":sz,"origin":"missing_title_reports",
         "note":"byte-variant duplicate; provenance backfilled (harness merge did not persist)","recorded_at":now}
    r=docs.update_one({"_id":target},{"$addToSet":{"custody.source_files":occ,
        "duplicate_of_files":{"doc_id":None,"sha256":sh,"path":fp}}})
    print(target,"matched=",r.matched_count,"modified=",r.modified_count,"sha=",sh[:12])
m.close()
