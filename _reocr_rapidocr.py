"""Targeted re-OCR: take every page from THIS force-vision run that fell to
RapidOCR (page.method == 'ocr') and re-run it through a frontier vision model
(Claude Sonnet 4.6 -> GPT-5), updating attachments_v2 in place.

Covers:
  - image attachments (.jpg/.png/...) that the main extractor routed straight
    to RapidOCR (the image path predates force-vision).
  - the 1 PDF page where Claude content-filtered AND GPT returned empty.

Read-only against GridFS; updates attachments_v2 rows in place (all rows that
share each sha256). Idempotent: re-running only re-touches rows still on 'ocr'.
"""
from __future__ import annotations

import gc
import io
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.extractor import extract_from_bytes
from src.extractor.rescue import re_ocr_image_via_vision
from src.utils.logger import logger

CUTOFF = datetime(2020, 1, 1, tzinfo=timezone.utc)  # widened: cover WHOLE corpus
V2 = "attachments_v2"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp"}


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
    init_spend_guard(min(50.0, s.ocr_vision_budget_usd))
    try:
        mongo.ping()
        v2 = mongo.db[V2]
        # Unique sha where this run produced a RapidOCR ('ocr') page OR a
        # born-digital 'text_layer' page (force-vision policy: NO text layer,
        # every page must go through Claude/GPT vision).
        pipeline = [
            {"$match": {"extracted_at": {"$gte": CUTOFF},
                        "extraction.pages.method": "ocr"}},
            {"$group": {"_id": "$sha256",
                        "filename": {"$first": "$filename"},
                        "gridfs_id": {"$first": "$gridfs_id"}}},
        ]
        groups = list(v2.aggregate(pipeline))
        logger.info(f"Re-OCR candidates (RapidOCR pages in this run): {len(groups)}")

        fixed = 0
        for g in groups:
            sha = g["_id"]
            fn = g.get("filename") or "attachment"
            ext = Path(fn).suffix.lower()
            try:
                data = _read_gridfs(mongo, g["gridfs_id"])
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"  gridfs read failed {fn!r}: {exc}")
                continue
            t0 = time.time()
            # Sniff magic bytes so a mangled extension (e.g. a MIME-encoded
            # ".pdf?=" name) still routes to the right handler.
            is_pdf = data[:5] == b"%PDF"
            is_img_magic = (data[:3] == b"\xff\xd8\xff"          # jpeg
                            or data[:8] == b"\x89PNG\r\n\x1a\n")  # png
            try:
                if ext in IMAGE_EXTS or (is_img_magic and not is_pdf):
                    result = re_ocr_image_via_vision(data, fn or "image.png")
                else:  # PDF (or other) -> force every page through vision
                    ocr_fn = fn if ext == ".pdf" else "document.pdf"
                    result = extract_from_bytes(
                        data, ocr_fn,
                        ocr_lang=s.ocr_lang, ocr_min_chars=10_000_000,
                        ocr_dpi=s.ocr_dpi, enable_ocr=True,
                        vision_enabled=True, vision_model=s.ocr_vision_model,
                        vision_min_pages=1, vision_dpi=s.ocr_vision_dpi,
                        vision_concurrency=s.ocr_vision_max_concurrency,
                    )
            finally:
                del data
                gc.collect()
            elapsed = time.time() - t0

            page_methods = sorted({p.method for p in result.pages})
            still_rapid = any(p.method == "ocr" for p in result.pages)
            logger.info(f"  {fn[:50]:<50} sha={sha[:12]} -> method={result.method} "
                        f"pages={page_methods} chars={result.char_count}")

            if result.text and not still_rapid:
                v2.update_many(
                    {"sha256": sha},
                    {"$set": {
                        "extracted_text": result.text,
                        "extraction": _extraction_doc(result, elapsed),
                        "extracted_via": "reocr_vision_v1",
                        "extracted_at": datetime.now(timezone.utc),
                    }},
                )
                fixed += 1
            else:
                logger.warning(f"    kept previous (still has RapidOCR/empty pages)")

        logger.info(f"\nDONE: {fixed}/{len(groups)} re-OCR'd via frontier vision.")
        return 0
    finally:
        mongo.close()


if __name__ == "__main__":
    raise SystemExit(main())
