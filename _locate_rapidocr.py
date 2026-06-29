"""Locate the 1,994 RapidOCR ('ocr') pages: which attachments, which corpus,
and when extracted — to determine if they're in this session's lawyer batch
(must be frontier) or the older pre-policy fraud corpus."""
from __future__ import annotations
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import Settings
from src.db.mongo import MongoClientWrapper


def main() -> int:
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    m.ping()
    av2 = m.db["attachments_v2"]
    ch = m.db["email_chunks_v2"]

    n_atts = 0
    by_month = Counter()
    by_ext = Counter()
    total_ocr_pages = 0
    sample = []
    sha_set = set()
    for a in av2.find({"extraction.pages.method": "ocr"},
                      {"_id": 1, "sha256": 1, "filename": 1, "extension": 1,
                       "extracted_at": 1, "extraction.pages.method": 1}):
        pages = (a.get("extraction") or {}).get("pages") or []
        nocr = sum(1 for p in pages if p.get("method") == "ocr")
        if nocr == 0:
            continue
        n_atts += 1
        total_ocr_pages += nocr
        sha_set.add(a.get("sha256"))
        ea = a.get("extracted_at")
        by_month[ea.strftime("%Y-%m") if ea else "(none)"] += 1
        by_ext[a.get("extension") or "(none)"] += 1
        if len(sample) < 25:
            sample.append((a.get("filename"), nocr, len(pages),
                           ea.strftime("%Y-%m-%d") if ea else "?"))

    print(f"Attachments containing >=1 RapidOCR page: {n_atts}  (unique sha={len(sha_set)})")
    print(f"Total RapidOCR pages: {total_ocr_pages}")
    print(f"By extraction month: {dict(by_month)}")
    print(f"By extension: {dict(by_ext)}")

    # corpus of the chunks for these sha
    corpus = Counter()
    for shabit in sha_set:
        c = ch.find_one({"sha256": shabit, "source_type": "attachment"}, {"corpus": 1})
        if c:
            corpus[c.get("corpus") or "(none)"] += 1
    print(f"Corpus of these attachments: {dict(corpus)}")

    print("\nSample (filename, ocr_pages, total_pages, extracted):")
    for fn, no, tp, ea in sample:
        print(f"  {ea}  ocr={no}/{tp}  {str(fn)[:60]}")
    m.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
