import io, zipfile, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
m.ping()
v2 = m.db["attachments_v2"]
d = v2.find_one({"filename": {"$regex": r"\.zip$", "$options": "i"}},
                {"gridfs_id": 1, "sha256": 1, "filename": 1})
if not d:
    print("no zip found in v2")
else:
    print("file:", d.get("filename"), "sha:", (d.get("sha256") or "")[:12])
    buf = io.BytesIO()
    m.gridfs.download_to_stream(d["gridfs_id"], buf)
    zf = zipfile.ZipFile(io.BytesIO(buf.getvalue()))
    tot_pdf_pages = 0
    for i in zf.infolist():
        if i.is_dir():
            continue
        ext = Path(i.filename).suffix.lower()
        print(f"  {round(i.file_size/1024,1):>9} KB  {ext:<6} {i.filename[:70]}")
m.close()
