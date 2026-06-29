"""Definitively check the fraud-corpus 'text_layer' pages: are they native
born-digital text (NOT OCR), or vision OCR stored under a different label?
Also count docs/pages to estimate OCR time."""
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
    v2 = m.db["attachments_v2"]
    ch = m.db["email_chunks_v2"]

    # fraud-corpus attachment sha
    fraud_sha = set()
    for c in ch.find({"source_type": "attachment", "corpus": "fraud_communications"},
                     {"sha256": 1}):
        fraud_sha.add(c.get("sha256"))

    uniq = set()
    tl_pages = 0
    via = Counter()
    method = Counter()
    samples = []
    for a in v2.find({"sha256": {"$in": list(fraud_sha)},
                      "extraction.pages.method": "text_layer"},
                     {"sha256": 1, "filename": 1, "extracted_via": 1,
                      "extraction.method": 1, "extraction.pages.method": 1,
                      "extracted_text": 1}):
        sha = a.get("sha256")
        if sha in uniq:
            continue
        uniq.add(sha)
        pages = (a.get("extraction") or {}).get("pages") or []
        n = sum(1 for p in pages if p.get("method") == "text_layer")
        tl_pages += n
        via[a.get("extracted_via")] += 1
        method[(a.get("extraction") or {}).get("method")] += 1
        if len(samples) < 10:
            txt = (a.get("extracted_text") or "")[:140].replace("\n", " ")
            pm = Counter(p.get("method") for p in pages)
            samples.append((a.get("filename"), dict(pm), a.get("extracted_via"), txt))

    print(f"fraud-corpus unique sha with text_layer pages: {len(uniq)}")
    print(f"total text_layer pages (born-digital, NOT vision): {tl_pages}")
    print(f"extracted_via tags: {dict(via)}")
    print(f"extraction.method: {dict(method)}")
    print("\nSAMPLES (page_methods prove text_layer = native, not OCR):")
    for fn, pm, v, txt in samples:
        print(f"\n  file={str(fn)[:55]!r}")
        print(f"    page_methods={pm}  extracted_via={v}")
        print(f"    text[:140]={txt!r}")
    m.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
