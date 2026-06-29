"""Force-vision OCR every born-digital ('text_layer') page in the LAWYER
(legal_correspondence) corpus. Born-digital text layers proved unreliable
(~89% content miss) so policy is: every page through Claude->GPT-5 vision.

Reads GridFS, re-extracts with ocr_min_chars=10M (forces vision on every
page), updates attachments_v2 in place (tag extracted_via='reocr_borndigital_v1').
Idempotent: only touches rows that still carry a text_layer page.
"""
from __future__ import annotations
import gc
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
TARGET_CORPUS = "legal_correspondence"


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
    s = Settings.load()
    mongo = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    from src.extractor.claude_ocr import init_spend_guard
    init_spend_guard(500.0)  # cost no object per user
    try:
        mongo.ping()
        v2 = mongo.db[V2]
        ch = mongo.db["email_chunks_v2"]

        # sha -> corpus (representative attachment chunk)
        logger.info("building sha->corpus map ...")
        sha_corpus = {}
        for c in ch.find({"source_type": "attachment"}, {"sha256": 1, "corpus": 1}):
            sha = c.get("sha256")
            if sha not in sha_corpus:
                sha_corpus[sha] = c.get("corpus") or "(none)"

        # unique born-digital sha in the legal corpus
        groups = {}
        for a in v2.find({"extraction.pages.method": "text_layer"},
                         {"sha256": 1, "filename": 1, "gridfs_id": 1}):
            sha = a.get("sha256")
            if sha_corpus.get(sha) != TARGET_CORPUS:
                continue
            if sha not in groups:
                groups[sha] = (a.get("filename") or "doc.pdf", a.get("gridfs_id"))
        logger.info(f"born-digital legal sha to force-vision: {len(groups)}")

        fixed = 0
        still_tl = 0
        total = len(groups)
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
                    data, ocr_fn,
                    ocr_lang=s.ocr_lang, ocr_min_chars=10_000_000,  # force vision
                    ocr_dpi=s.ocr_dpi, enable_ocr=True,
                    vision_enabled=True, vision_model=s.ocr_vision_model,
                    vision_min_pages=1, vision_dpi=s.ocr_vision_dpi,
                    vision_concurrency=s.ocr_vision_max_concurrency,
                )
            finally:
                del data
                gc.collect()
            elapsed = time.time() - t1

            page_methods = sorted({p.method for p in result.pages})
            has_tl = any(p.method == "text_layer" for p in result.pages)
            if result.text and not has_tl:
                v2.update_many({"sha256": sha}, {"$set": {
                    "extracted_text": result.text,
                    "extraction": _extraction_doc(result, elapsed),
                    "extracted_via": "reocr_borndigital_v1",
                    "extracted_at": datetime.now(timezone.utc),
                }})
                fixed += 1
            else:
                still_tl += 1
                logger.warning(f"  kept previous {fn[:40]!r} methods={page_methods}")

            if i % 20 == 0 or i == total:
                rate = i / (time.time() - t0)
                eta = (total - i) / rate / 60 if rate else 0
                logger.info(f"  [{i}/{total}] fixed={fixed} kept={still_tl} "
                            f"last={fn[:34]!r} pages={len(result.pages)} "
                            f"rate={rate:.2f}/s eta={eta:.1f}m")

        logger.info(f"\nDONE: force-visioned {fixed}/{total} born-digital legal docs "
                    f"({still_tl} kept previous).")
        return 0
    finally:
        mongo.close()


if __name__ == "__main__":
    raise SystemExit(main())
