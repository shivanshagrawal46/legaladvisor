import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
mongo = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
try:
    av2 = mongo.db["attachments_v2"]
    shas = sorted({r["sha256"] for r in av2.find(
        {"extracted_via": "reocr_fraud_borndigital_v1"}, {"sha256": 1})})
    Path("_sha310.txt").write_text("\n".join(shas) + "\n", encoding="utf-8")
    print(f"wrote {len(shas)} sha -> _sha310.txt")
finally:
    mongo.close()
