"""OPTION 1: Force-vision OCR the fraud-corpus 'pdf_mixed' attachments (docs
where some pages had native text and some were scanned images -> the genuinely
risky born-digital docs). Re-extracts every page through Claude->GPT-5 vision,
updates attachments_v2 in place (extracted_via='reocr_fraud_mixed_v1').
Idempotent: only touches sha whose extraction.method == 'pdf_mixed'.
Prints the affected sha list so the re-chunk step can target them."""
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
TARGET_CORPUS = "fraud_communications"


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
    init_spend_guard(200.0)
    try:
        mongo.ping()
        v2 = mongo.db[V2]
        ch = mongo.db["email_chunks_v2"]

        logger.info("building fraud-corpus sha set ...")
        fraud_sha = {c["sha256"] for c in ch.find(
            {"source_type": "attachment", "corpus": TARGET_CORPUS},
            {"sha256": 1}) if c.get("sha256")}

        groups = {}
        for a in v2.find({"sha256": {"$in": list(fraud_sha)},
                          "extraction.method": "pdf_mixed"},
                         {"sha256": 1, "filename": 1, "gridfs_id": 1}):
            sha = a.get("sha256")
            if sha not in groups:
                groups[sha] = (a.get("filename") or "doc.pdf", a.get("gridfs_id"))
        total = len(groups)
        logger.info(f"fraud-corpus pdf_mixed sha to force-vision: {total}")

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
                    "extracted_via": "reocr_fraud_mixed_v1",
                    "extracted_at": datetime.now(timezone.utc),
                }})
                fixed += 1
                done_sha.append(sha)
            else:
                kept += 1
                logger.warning(f"  kept {fn[:40]!r} "
                               f"methods={sorted({p.method for p in result.pages})}")
            rate = i / (time.time() - t0)
            eta = (total - i) / rate / 60 if rate else 0
            logger.info(f"  [{i}/{total}] fixed={fixed} kept={kept} "
                        f"last={str(fn)[:34]!r} pages={len(result.pages)} "
                        f"{elapsed:.1f}s eta={eta:.1f}m")

        logger.info(f"\nDONE: force-visioned {fixed}/{total} fraud pdf_mixed docs "
                    f"({kept} kept).")
        Path("_fraud_mixed_done_sha.txt").write_text(
            "\n".join(done_sha), encoding="utf-8")
        logger.info(f"wrote {len(done_sha)} sha to _fraud_mixed_done_sha.txt")
        return 0
    finally:
        mongo.close()


if __name__ == "__main__":
    raise SystemExit(main())
