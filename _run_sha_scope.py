"""Attachment sha256 scope for the emails inserted by specific ingestion runs.

Used instead of the Boris-label scope because this batch spans two labels
(Boris Lawsuit + plain inbox mail from Maida).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bson import ObjectId
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

RUN_IDS = sys.argv[1:] or [
    "6a93f9143950fb1060aa3cd5",   # Boris label pull
    "6a93f9479988adf4c8b17623",   # Maida inbox pull
]

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
em, att, av2 = m.db["emails"], m.db["attachments"], m.db["attachments_v2"]
ch = m.db["email_chunks_v2"]

oids = [ObjectId(r) for r in RUN_IDS]
eids = [d["_id"] for d in em.find({"ingestion_run_id": {"$in": oids}}, {"_id": 1})]
print(f"emails from these runs      : {len(eids)}")

rows = list(att.find({"email_id": {"$in": eids}},
                     {"sha256": 1, "filename": 1, "email_id": 1}))
print(f"attachment rows on them     : {len(rows)}")

shas, need_ocr, need_embed = set(), set(), set()
for r in rows:
    sha = r.get("sha256")
    if not sha:
        continue
    shas.add(sha)
    if not av2.find_one({"sha256": sha}, {"_id": 1}):
        need_ocr.add(sha)
    if not ch.find_one({"sha256": sha, "source_type": "attachment"}, {"_id": 1}):
        need_embed.add(sha)

print(f"unique sha256               : {len(shas)}")
print(f"  NEED OCR                  : {len(need_ocr)}")
print(f"  NEED chunk+embed          : {len(need_embed)}")
for r in rows:
    mark = "OCR" if r.get("sha256") in need_ocr else "  -"
    print(f"    [{mark}] {str(r.get('filename'))[:58]:60s}{str(r.get('sha256'))[:12]}")

out = Path("_run_shas.txt")
out.write_text("\n".join(sorted(shas)), encoding="utf-8")
print(f"\nwrote {len(shas)} sha256 -> {out}")
m.close()
