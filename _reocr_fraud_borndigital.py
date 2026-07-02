"""Force-vision OCR the 310 pure born-digital ('pdf_text') attachments in the
FRAUD (fraud_communications / David adverse-party) corpus — the set deferred in
PENDING_OCR_DECISION.md. Every page goes through Claude Sonnet 4.6 -> GPT-5
vision (ocr_min_chars=10M forces vision; NEVER RapidOCR). Updates attachments_v2
in place (extracted_via='reocr_fraud_borndigital_v1'). Idempotent: only touches
fraud-corpus sha whose extraction.method == 'pdf_text'. Writes the affected sha
list so the re-chunk step can target them.

Usage:
  python _reocr_fraud_borndigital.py            # full run
  python _reocr_fraud_borndigital.py --shard k/N # parallel worker
"""
from __future__ import annotations
import argparse
import gc
import hashlib
import io
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.extractor import extract_from_bytes
from src.utils.logger import logger

V2 = "attachments_v2"
TARGET_CORPUS = "fraud_communications"
DONE_FILE = "_fraud_borndigital_done_sha.txt"


def _read_gridfs(mongo, gid) -> bytes:
    buf = io.BytesIO()
    mongo.gridfs.download_to_stream(gid, buf)
    return buf.getvalue()


def _extraction_doc(result, elapsed: float) -> Dict[str, Any]:
    return {
        "method": result.method,
        "char_count": result.char_count,
        "avg_ocr_confidence": result.avg_ocr_confidence,
        "page_count": len(result.pages),
        "pages": [
            {"page_no": p.page_no, "method": p.method,
             "ocr_confidence": p.ocr_confidence,
             "char_count": len(p.text), "text": p.text}
            for p in result.pages
        ],
        "extracted_at": datetime.now(timezone.utc),
        "skipped_reason": result.skipped_reason,
        "elapsed_sec": round(elapsed, 3),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", default=None, help="k/N disjoint worker by hash(sha)")
    args = ap.parse_args()
    s = Settings.load()
    mongo = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    from src.extractor.claude_ocr import init_spend_guard
    init_spend_guard(200.0)
    try:
        mongo.ping()
        v2 = mongo.db[V2]

        logger.info("building fraud-corpus email-id set ...")
        fraud_ids = {e["_id"] for e in mongo.emails.find(
            {"corpus": TARGET_CORPUS}, {"_id": 1})}
        logger.info(f"fraud emails: {len(fraud_ids)}")

        # unique pdf_text sha among fraud-corpus attachments
        groups = {}
        for a in v2.find({"extraction.method": "pdf_text"},
                         {"sha256": 1, "filename": 1, "gridfs_id": 1, "email_id": 1}):
            if a.get("email_id") not in fraud_ids:
                continue
            sha = a.get("sha256")
            if sha and sha not in groups:
                groups[sha] = (a.get("filename") or "doc.pdf", a.get("gridfs_id"))

        if args.shard:
            sk, sn = (int(x) for x in args.shard.split("/"))
            groups = {sha: v for sha, v in groups.items()
                      if int(hashlib.md5(sha.encode()).hexdigest(), 16) % sn == sk}
            logger.info(f"shard {sk}/{sn}")
        total = len(groups)
        logger.info(f"fraud pdf_text sha to force-vision: {total}")

        fixed, kept = 0, 0
        done_sha = []
        t0 = time.time()
        for i, (sha, (fn, gid)) in enumerate(groups.items(), 1):
            try:
                data = _read_gridfs(mongo, gid)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"  gridfs read failed {fn!r}: {exc}")
                continue
            t1 = time.time()
            ocr_fn = fn if str(fn).lower().endswith(".pdf") else "document.pdf"
            try:
                result = extract_from_bytes(
                    data, ocr_fn, ocr_lang=s.ocr_lang,
                    ocr_min_chars=10_000_000, ocr_dpi=s.ocr_dpi, enable_ocr=True,
                    vision_enabled=True, vision_model=s.ocr_vision_model,
                    vision_min_pages=1, vision_dpi=s.ocr_vision_dpi,
                    vision_concurrency=s.ocr_vision_max_concurrency,
                )
            finally:
                del data
                gc.collect()
            elapsed = time.time() - t1
            has_tl = any(p.method == "text_layer" for p in result.pages)
            if result.text and not has_tl:
                v2.update_many({"sha256": sha}, {"$set": {
                    "extracted_text": result.text,
                    "extraction": _extraction_doc(result, elapsed),
                    "extracted_via": "reocr_fraud_borndigital_v1",
                    "extracted_at": datetime.now(timezone.utc),
                }})
                fixed += 1
                done_sha.append(sha)
            else:
                kept += 1
                logger.warning(f"  kept {str(fn)[:40]!r} "
                               f"methods={sorted({p.method for p in result.pages})}")
            rate = i / (time.time() - t0)
            eta = (total - i) / rate / 60 if rate else 0
            logger.info(f"  [{i}/{total}] fixed={fixed} kept={kept} "
                        f"last={str(fn)[:34]!r} pages={len(result.pages)} "
                        f"{elapsed:.1f}s eta={eta:.1f}m")

        logger.info(f"\nDONE: force-visioned {fixed}/{total} fraud pdf_text docs "
                    f"({kept} kept).")
        # append (so parallel shards don't clobber)
        with open(DONE_FILE, "a", encoding="utf-8") as fh:
            for sha in done_sha:
                fh.write(sha + "\n")
        logger.info(f"appended {len(done_sha)} sha to {DONE_FILE}")
        return 0
    finally:
        mongo.close()


if __name__ == "__main__":
    raise SystemExit(main())
