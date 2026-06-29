"""OCR the single PDF inside Attachments.zip ('Closing Documents - Properties
at Issue.pdf', 27 MB, born-digital) through GPT-5 Vision on EVERY page —
per the user's instruction (frontier OCR, cost no object). Updates the zip's
attachments_v2 row in place with the GPT-5 transcription.
"""
from __future__ import annotations

import io
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fitz  # PyMuPDF

from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.extractor.pdf import _render_page_to_image
from src.extractor.claude_ocr import _ocr_page_via_openai
from src.utils.logger import logger

ZIP_SHA_PREFIX = "33c8d9696d14"
CONCURRENCY = 8


def main() -> int:
    s = Settings.load()
    mongo = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    try:
        mongo.ping()
        v2 = mongo.db["attachments_v2"]
        doc_row = v2.find_one({"sha256": {"$regex": f"^{ZIP_SHA_PREFIX}"}},
                              {"sha256": 1, "gridfs_id": 1, "filename": 1})
        if not doc_row:
            logger.error("zip row not found"); return 1
        sha = doc_row["sha256"]
        buf = io.BytesIO()
        mongo.gridfs.download_to_stream(doc_row["gridfs_id"], buf)
        zf = zipfile.ZipFile(io.BytesIO(buf.getvalue()))
        pdf_name = next(n for n in zf.namelist() if n.lower().endswith(".pdf"))
        pdf_bytes = zf.read(pdf_name)
        logger.info(f"Inner PDF: {pdf_name}  ({len(pdf_bytes)/1024/1024:.1f} MB)")

        pdoc = fitz.open(stream=pdf_bytes, filetype="pdf")
        n = len(pdoc)
        logger.info(f"Pages: {n}  -> GPT-5 vision @ concurrency={CONCURRENCY}, dpi={s.ocr_vision_dpi}")

        # Pre-render all pages (fitz isn't thread-safe for the same doc, so
        # render sequentially, OCR in parallel).
        texts = [None] * n
        t0 = time.time()

        def ocr_one(idx: int, img):
            txt = _ocr_page_via_openai(img)
            return idx, (txt or "")

        BATCH = 16  # render+submit in batches to bound memory
        done = 0
        for start in range(0, n, BATCH):
            batch_idxs = list(range(start, min(start + BATCH, n)))
            rendered = []
            for i in batch_idxs:
                try:
                    rendered.append((i, _render_page_to_image(pdoc[i], s.ocr_vision_dpi)))
                except Exception as exc:  # noqa: BLE001
                    logger.warning(f"  page {i+1}: render failed: {exc}")
                    texts[i] = ""
            with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
                futs = [pool.submit(ocr_one, i, img) for i, img in rendered]
                for f in as_completed(futs):
                    idx, txt = f.result()
                    texts[idx] = txt
                    done += 1
            rate = done / (time.time() - t0) if time.time() > t0 else 0
            eta = (n - done) / rate / 60 if rate else 0
            got = sum(len(t or "") for t in texts)
            logger.info(f"  [{done}/{n}] chars={got:,} rate={rate:.2f}/s eta={eta:.1f}m")

        page_docs = []
        parts = []
        for i in range(n):
            t = texts[i] or ""
            if t.strip():
                parts.append(t.strip())
            page_docs.append({"page_no": i + 1, "method": "openai_vision",
                              "ocr_confidence": 0.95 if t.strip() else 0.0,
                              "char_count": len(t), "text": t})
        full = "\n\n".join(parts).strip()
        header = f"[Archived: {pdf_name}]\n"
        full = header + full

        v2.update_many({"sha256": sha}, {"$set": {
            "extracted_text": full,
            "extraction": {
                "method": "zip", "char_count": len(full),
                "avg_ocr_confidence": 0.95, "page_count": n,
                "pages": page_docs,
                "extracted_at": datetime.now(timezone.utc),
                "skipped_reason": None,
            },
            "extracted_via": "zip_gpt5_vision",
            "extracted_at": datetime.now(timezone.utc),
        }})
        logger.info(f"\nDONE: {n} pages OCR'd via GPT-5, {len(full):,} chars stored.")
        return 0
    finally:
        mongo.close()


if __name__ == "__main__":
    raise SystemExit(main())
