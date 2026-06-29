"""Find attachment_ids referenced by emails that have NO attachments_v2 row,
then classify them via the original `attachments` collection so we know whether
any real evidence document is being skipped at embed time.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import Settings
from src.db.mongo import MongoClientWrapper


def main() -> int:
    s = Settings.load()
    mongo = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    try:
        mongo.ping()
        v2 = mongo.db["attachments_v2"]

        referenced = set()
        for em in mongo.emails.find({}, {"attachment_ids": 1}):
            for aid in em.get("attachment_ids") or []:
                referenced.add(aid)
        print(f"Total referenced attachment_ids: {len(referenced):,}")

        v2_ids = {d["_id"] for d in v2.find({}, {"_id": 1})}
        missing = [aid for aid in referenced if aid not in v2_ids]
        print(f"Referenced but NOT in attachments_v2: {len(missing):,}")

        # Look them up in the ORIGINAL attachments collection.
        att = mongo.attachments
        rows = list(att.find({"_id": {"$in": missing}},
                             {"_id": 1, "filename": 1, "sha256": 1,
                              "gridfs_id": 1, "size_bytes": 1,
                              "extracted_text": 1}))
        found_ids = {r["_id"] for r in rows}
        dangling = [m for m in missing if m not in found_ids]

        by_ext = Counter()
        no_sha = no_gridfs = has_text = 0
        in_v2_by_sha = 0
        # set of sha already covered in v2 (so a missing _id whose sha IS in v2
        # is harmless — same content already embedded under another row)
        v2_shas = {d.get("sha256") for d in v2.find({}, {"sha256": 1})}
        examples = []
        for r in rows:
            fn = r.get("filename") or ""
            ext = Path(fn).suffix.lower() or "(none)"
            by_ext[ext] += 1
            if not r.get("sha256"):
                no_sha += 1
            elif r["sha256"] in v2_shas:
                in_v2_by_sha += 1
            if not r.get("gridfs_id"):
                no_gridfs += 1
            if (r.get("extracted_text") or "").strip():
                has_text += 1
            if len(examples) < 30:
                examples.append((fn[:55], ext, r.get("size_bytes"),
                                 bool(r.get("sha256")),
                                 r.get("sha256") in v2_shas if r.get("sha256") else False))

        print(f"\nOf the {len(missing)} missing references:")
        print(f"  dangling (no row in `attachments` at all): {len(dangling)}")
        print(f"  present in `attachments`:                  {len(rows)}")
        print(f"    - no sha256:                             {no_sha}")
        print(f"    - sha256 ALREADY embedded in v2 (dupe):  {in_v2_by_sha}")
        print(f"    - no gridfs_id:                          {no_gridfs}")
        print(f"    - already had extracted_text:            {has_text}")
        print(f"\n  By extension: {dict(by_ext)}")
        print(f"\n  Examples (filename, ext, size, has_sha, sha_in_v2):")
        for e in examples:
            print(f"    {e[0]:<55} {e[1]:<8} {str(e[2]):>10}  sha={e[3]} in_v2={e[4]}")
        return 0
    finally:
        mongo.close()


if __name__ == "__main__":
    raise SystemExit(main())
