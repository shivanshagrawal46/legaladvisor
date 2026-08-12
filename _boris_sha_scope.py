"""Write the sha256 scope file for the Boris Lawsuit label's attachments.

The OCR script resume-skips any sha256 already in attachments_v2, so we can
safely hand it the full label scope and let it process only what is missing.
Also reports the Option B dedup split: which sha256s are brand-new content
versus ones already vectorised that merely need an occurrences[] entry.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

LABEL = "__....Boris Lawsuit"
OUT = Path("_boris_shas.txt")

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
db = m.db
em, att, av2, ch = db["emails"], db["attachments"], db["attachments_v2"], db["email_chunks_v2"]

base_q = {"source.origin": "gmail_api", "gmail_labels": LABEL}
emails = list(em.find(base_q, {"_id": 1, "attachment_ids": 1}))
att_ids = [a for e in emails for a in (e.get("attachment_ids") or [])]

rows = list(att.find({"_id": {"$in": att_ids}}, {"sha256": 1}))
shas = sorted({r["sha256"] for r in rows if r.get("sha256")})

ocr_done = set(av2.distinct("sha256", {"sha256": {"$in": shas}}))
vec_done = set(ch.distinct("sha256", {"source_type": "attachment", "sha256": {"$in": shas}}))

print(f"Boris emails                     : {len(emails):,}")
print(f"attachment rows on them          : {len(att_ids):,}")
print(f"unique sha256 (Option B keys)    : {len(shas):,}")
print(f"  already OCR'd (attachments_v2) : {len(ocr_done):,}")
print(f"  NEED OCR                       : {len(shas) - len(ocr_done):,}")
print(f"  already vectorised             : {len(vec_done):,}")
print(f"  NEED chunk+embed               : {len(shas) - len(vec_done):,}")
print(f"dedup saving (rows -> unique)    : {len(att_ids) - len(shas):,} duplicate "
      f"attachment rows collapse into occurrences[]")

OUT.write_text("\n".join(shas) + "\n", encoding="utf-8")
print(f"\nwrote {len(shas):,} sha256 -> {OUT}")

m.close()
