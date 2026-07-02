import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
mongo = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
try:
    db = mongo.db
    print("COLLECTIONS:", sorted(db.list_collection_names()))
    for cn in ["attachments_v2", "documents", "email_chunks_v2"]:
        c = db[cn].find_one()
        if c:
            print(f"\n--- {cn} sample fields ---")
            print(sorted(c.keys()))
finally:
    mongo.close()
