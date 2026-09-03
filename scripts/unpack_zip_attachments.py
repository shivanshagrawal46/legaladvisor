"""Unpack ZIP attachments into real, individually-extractable attachments.

The extractor has no ZIP handler, so an archive lands in the corpus as an
opaque blob and everything inside it is invisible to search. This walks the
ZIPs on a given ingestion run, writes each member into GridFS as its own
attachment row (mirroring Repository.store_attachment), and links it to the
parent email so the normal OCR -> chunk -> embed path picks it up.

Members already present under the same sha256 are skipped, so re-running is
safe. The ZIP row itself is left in place as provenance but marked so it is
not treated as missing content.

  python scripts/unpack_zip_attachments.py --run-id <id>
  python scripts/unpack_zip_attachments.py --run-id <id> --apply
"""
from __future__ import annotations

import argparse
import hashlib
import io
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bson import ObjectId
from loguru import logger

from config.settings import Settings
from src.db.mongo import MongoClientWrapper

SKIP_PREFIXES = ("__MACOSX/", ".")
SKIP_SUFFIXES = (".ds_store",)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--run-id", required=True, help="ingestion_run_id to scan")
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()

    s = Settings.load()
    mongo = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    em, att = mongo.emails, mongo.db["attachments"]

    mail_ids = [d["_id"] for d in em.find(
        {"ingestion_run_id": ObjectId(args.run_id)}, {"_id": 1})]
    zips = list(att.find({"email_id": {"$in": mail_ids}, "extension": ".zip"},
                         {"filename": 1, "email_id": 1, "gridfs_id": 1,
                          "sha256": 1, "email_pst_entry_id": 1}))
    logger.info(f"zip attachments on run: {len(zips)}")

    known = set(att.distinct("sha256"))
    total_new = 0

    for z in zips:
        raw = mongo.gridfs.open_download_stream(z["gridfs_id"]).read()
        logger.info(f"\n{z.get('filename')}  ({len(raw):,} B)")
        try:
            zf = zipfile.ZipFile(io.BytesIO(raw))
        except Exception as exc:
            logger.error(f"  not a readable zip: {exc}")
            continue

        new_ids = []
        for info in zf.infolist():
            name = info.filename
            if info.is_dir() or name.startswith(SKIP_PREFIXES) \
                    or name.lower().endswith(SKIP_SUFFIXES):
                continue
            data = zf.read(info)
            if not data:
                continue
            sha = hashlib.sha256(data).hexdigest()
            base = Path(name).name
            dup = sha in known
            logger.info(f"    {'[dup]  ' if dup else '[new]  '}"
                        f"{base[:56]:58s}{len(data):>10,} B")
            if dup or not args.apply:
                continue

            gid = mongo.gridfs.upload_from_stream(
                base, data,
                metadata={"email_id": z["email_id"],
                          "sha256": sha,
                          "unpacked_from_zip": z["_id"]},
            )
            ext = ("." + base.rsplit(".", 1)[-1].lower()) if "." in base else ""
            aid = att.insert_one({
                "email_id": z["email_id"],
                "email_pst_entry_id": z.get("email_pst_entry_id"),
                "filename": base,
                "display_name": base,
                "extension": ext,
                "content_type": None,
                "size_bytes": len(data),
                "sha256": sha,
                "is_inline": False,
                "content_id": None,
                "gridfs_id": gid,
                "ingested_at": datetime.now(timezone.utc),
                "unpacked_from_zip": z["_id"],
                "zip_member_path": name,
            }).inserted_id
            known.add(sha)
            new_ids.append(aid)
            total_new += 1

        if new_ids and args.apply:
            em.update_one({"_id": z["email_id"]},
                          {"$push": {"attachment_ids": {"$each": new_ids}},
                           "$inc": {"attachment_count": len(new_ids)}})
            att.update_one({"_id": z["_id"]},
                           {"$set": {"zip_unpacked": True,
                                     "zip_member_count": len(new_ids)}})

    logger.info(f"\n{'unpacked' if args.apply else 'would unpack'} {total_new} members")
    if not args.apply:
        logger.info("report-only. re-run with --apply to write.")
    mongo.close()


if __name__ == "__main__":
    main()
