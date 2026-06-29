import config.settings  # noqa
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from api.views import _has_original, _read_original, _locate_on_disk, _gridfs_file_doc
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name); db=m.db
docs=db["documents"]
def test(q,label):
    d=docs.find_one(q)
    if not d: print(label,"-> no doc"); return
    sha=(d.get("custody") or {}).get("sha256")
    disk=_locate_on_disk(d); gfs=bool(_gridfs_file_doc(db,sha))
    ho=_has_original(db,d)
    print(f"{label}: {d['_id']} type={d.get('source_type')} has_original={ho} (disk={bool(disk)}, gridfs={gfs})")
    if ho:
        r=_read_original(db,d)
        print("   read bytes:",(len(r[0]) if r else None),"fname:",(r[1] if r else None))
test({"source_type":"title_report","custody.source_files":{"$exists":True}},"title")
test({"_id":{"$regex":"^doc_p5"}},"discovery_p5")
test({"source_type":"generic_document"},"generic")
m.close()
