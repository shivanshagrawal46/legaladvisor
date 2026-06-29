"""Re-extract any attachments_v2 doc from this run whose extraction.method is
'zip' (or 'tnef') so its embedded PDF/image members are re-run through the
now-force-vision archive handler. Updates rows in place.
"""
from __future__ import annotations

import gc
import io
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.extractor.rescue import rescue_extract

CUTOFF = datetime(2026, 6, 25, 10, 40, tzinfo=timezone.utc)


def main() -> int:
    s = Settings.load()
    mongo = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    from src.extractor.claude_ocr import init_spend_guard
    init_spend_guard(min(50.0, s.ocr_vision_budget_usd))
    try:
        mongo.ping()
        v2 = mongo.db["attachments_v2"]
        rows = list(v2.aggregate([
            {"$match": {"extracted_at": {"$gte": CUTOFF},
                        "extraction.method": {"$in": ["zip"]}}},
            {"$group": {"_id": "$sha256",
                        "filename": {"$first": "$filename"},
                        "gridfs_id": {"$first": "$gridfs_id"}}},
        ]))
        print(f"archive docs to re-extract: {len(rows)}")
        for r in rows:
            sha = r["_id"]; fn = r.get("filename") or "archive.zip"
            buf = io.BytesIO()
            mongo.gridfs.download_to_stream(r["gridfs_id"], buf)
            data = buf.getvalue()
            try:
                res = rescue_extract(data, fn)
            finally:
                del data; gc.collect()
            methods = sorted({p.method for p in res.pages})
            print(f"  {fn[:40]:<40} -> {res.method} pages={methods} chars={res.char_count}")
            if res.text:
                v2.update_many({"sha256": sha}, {"$set": {
                    "extracted_text": res.text,
                    "extraction": {
                        "method": res.method, "char_count": res.char_count,
                        "avg_ocr_confidence": res.avg_ocr_confidence,
                        "page_count": len(res.pages),
                        "pages": [{"page_no": p.page_no, "method": p.method,
                                   "ocr_confidence": p.ocr_confidence,
                                   "char_count": len(p.text), "text": p.text}
                                  for p in res.pages],
                        "extracted_at": datetime.now(timezone.utc),
                        "skipped_reason": res.skipped_reason,
                    },
                    "extracted_via": "reextract_zip_v1",
                    "extracted_at": datetime.now(timezone.utc),
                }})
        print("DONE")
        return 0
    finally:
        mongo.close()


if __name__ == "__main__":
    raise SystemExit(main())
