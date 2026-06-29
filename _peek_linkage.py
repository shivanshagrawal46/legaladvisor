"""Peek at the linkage fields of one re-OCR'd fraud chunk + one entity-less one."""
from __future__ import annotations
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper


def show(c):
    for k in ["sha256", "email_id", "chunk_index", "total_chunks", "corpus",
              "privilege_status", "filename", "entity_ids", "entity_refs",
              "primary_property_id", "page_start", "page_end"]:
        print(f"   {k}: {c.get(k)!r}")
    occ = c.get("occurrences") or []
    print(f"   occurrences: {len(occ)} item(s)")
    if occ:
        print(f"   occ[0]: {json.dumps(occ[0], default=str)[:300]}")


def main() -> int:
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    m.ping()
    ch = m.db["email_chunks_v2"]
    shas = [ln.strip() for ln in Path("_fraud_mixed_done_sha.txt").read_text(
        encoding="utf-8").splitlines() if ln.strip()]

    print("=== a chunk WITH entity links ===")
    c1 = ch.find_one({"sha256": {"$in": shas}, "source_type": "attachment",
                      "entity_ids": {"$exists": True, "$ne": []}})
    if c1:
        show(c1)

    print("\n=== a chunk WITHOUT entity links (one of the 461) ===")
    c2 = ch.find_one({"sha256": {"$in": shas}, "source_type": "attachment",
                      "$or": [{"entity_ids": {"$exists": False}},
                              {"entity_ids": []}]})
    if c2:
        show(c2)

    print("\nemails collection name check:",
          "emails" in m.db.list_collection_names())
    m.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
