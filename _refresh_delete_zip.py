"""Delete the stale attachment chunks for the zip sha so the idempotent
build re-chunks it from the fresh GPT-5 text."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import Settings
from src.db.mongo import MongoClientWrapper

ZIP_PFX = "33c8d9696d14"


def main() -> int:
    s = Settings.load()
    mongo = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    try:
        mongo.ping()
        v2 = mongo.db["attachments_v2"]
        ch = mongo.db["email_chunks_v2"]
        row = v2.find_one({"sha256": {"$regex": f"^{ZIP_PFX}"}}, {"sha256": 1})
        sha = row["sha256"]
        before = ch.count_documents({"sha256": sha, "source_type": "attachment"})
        res = ch.delete_many({"sha256": sha, "source_type": "attachment"})
        after = ch.count_documents({"sha256": sha, "source_type": "attachment"})
        print(f"zip sha={sha[:16]} chunks_before={before} deleted={res.deleted_count} after={after}")
        return 0
    finally:
        mongo.close()


if __name__ == "__main__":
    raise SystemExit(main())
