import hashlib
import config.settings  # noqa
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()
files=[r"E:\missing title reports\31 Fort Hill Dr Lloyd Harbor Ny\31 Fort Hill Dr_Update Search.pdf",
       r"E:\missing title reports\83 Ann Dr S Freeport Ny\83 S Ann Drive_Update Search 2026.pdf"]
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name)
docs=m.db["documents"]
for fp in files:
    sh=sha(fp)
    # search any doc whose custody.sha256 or source_files.sha256 or duplicate_of_files.sha256 == sh
    hit=docs.find_one({"$or":[{"custody.sha256":sh},{"custody.source_files.sha256":sh},{"duplicate_of_files.sha256":sh}]},{"_id":1})
    print(fp.split("\\")[-1], "sha=",sh[:16], "-> DB doc:", hit["_id"] if hit else "NONE")
m.close()
