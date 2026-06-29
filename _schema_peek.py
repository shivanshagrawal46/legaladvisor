import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
m.ping()
for coll in ["emails", "attachments_v2", "email_chunks_v2"]:
    doc = m.db[coll].find_one()
    print(f"\n=== {coll}  count={m.db[coll].estimated_document_count():,}")
    if doc:
        for k, v in doc.items():
            t = type(v).__name__
            if isinstance(v, (list,)):
                print(f"  {k}: list[{len(v)}]")
            elif isinstance(v, str):
                print(f"  {k}: str({len(v)})")
            elif isinstance(v, dict):
                print(f"  {k}: dict keys={list(v.keys())[:8]}")
            else:
                print(f"  {k}: {t} = {str(v)[:40]}")
m.close()
