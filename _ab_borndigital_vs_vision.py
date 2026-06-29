"""A/B test: for a few born-digital fraud-corpus PDFs, compare the CURRENT
native text_layer extraction vs a fresh force-vision OCR of the same bytes.
Quantifies how much content the native text layer is missing vs vision."""
from __future__ import annotations
import gc
import io
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.extractor import extract_from_bytes

N_DOCS = 4
WORD_RE = re.compile(r"[A-Za-z0-9$%.,/-]+")


def words(t: str):
    return [w.lower() for w in WORD_RE.findall(t or "")]


def main() -> int:
    s = Settings.load()
    mongo = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    from src.extractor.claude_ocr import init_spend_guard
    init_spend_guard(50.0)
    try:
        mongo.ping()
        v2 = mongo.db["attachments_v2"]
        ch = mongo.db["email_chunks_v2"]

        fraud_sha = {c["sha256"] for c in ch.find(
            {"source_type": "attachment", "corpus": "fraud_communications"},
            {"sha256": 1}) if c.get("sha256")}

        picks = []
        seen = set()
        # prefer small docs (1-6 pages) for speed + clear comparison
        for a in v2.find({"sha256": {"$in": list(fraud_sha)},
                          "extraction.pages.method": "text_layer"},
                         {"sha256": 1, "filename": 1, "gridfs_id": 1,
                          "extracted_text": 1, "extraction.page_count": 1}):
            sha = a.get("sha256")
            if sha in seen:
                continue
            pc = (a.get("extraction") or {}).get("page_count") or 99
            if pc < 1 or pc > 6:
                continue
            seen.add(sha)
            picks.append(a)
            if len(picks) >= N_DOCS:
                break

        print(f"Comparing {len(picks)} born-digital fraud docs:\n" + "=" * 70)
        for a in picks:
            fn = a.get("filename") or "doc.pdf"
            native = a.get("extracted_text") or ""
            buf = io.BytesIO()
            mongo.gridfs.download_to_stream(a["gridfs_id"], buf)
            data = buf.getvalue()
            ocr_fn = fn if str(fn).lower().endswith(".pdf") else "document.pdf"
            t1 = time.time()
            try:
                res = extract_from_bytes(
                    data, ocr_fn, ocr_lang=s.ocr_lang,
                    ocr_min_chars=10_000_000, ocr_dpi=s.ocr_dpi, enable_ocr=True,
                    vision_enabled=True, vision_model=s.ocr_vision_model,
                    vision_min_pages=1, vision_dpi=s.ocr_vision_dpi,
                    vision_concurrency=s.ocr_vision_max_concurrency,
                )
            finally:
                del data
                gc.collect()
            el = time.time() - t1
            vis = res.text or ""

            nw, vw = words(native), words(vis)
            ns, vs = set(nw), set(vw)
            only_vis = vs - ns           # content vision found, native missed
            only_nat = ns - vs           # content native had, vision missed
            methods = sorted({p.method for p in res.pages})

            print(f"\nFILE: {str(fn)[:60]!r}")
            print(f"  pages={len(res.pages)} vision_methods={methods} ocr_time={el:.1f}s")
            print(f"  native chars={len(native):>7,}   words={len(nw):>6,}  uniq={len(ns):>5,}")
            print(f"  vision chars={len(vis):>7,}   words={len(vw):>6,}  uniq={len(vs):>5,}")
            delta = (len(vis) - len(native)) / max(len(native), 1) * 100
            print(f"  char delta: {delta:+.1f}%   "
                  f"words ONLY in vision={len(only_vis)}   "
                  f"ONLY in native={len(only_nat)}")
            ex_v = [w for w in vw if w in only_vis][:25]
            ex_n = [w for w in nw if w in only_nat][:25]
            print(f"  e.g. ONLY-in-vision tokens: {ex_v}")
            print(f"  e.g. ONLY-in-native tokens: {ex_n}")
        print("\n" + "=" * 70)
        return 0
    finally:
        mongo.close()


if __name__ == "__main__":
    raise SystemExit(main())
