"""Confirm where the remaining 'text_layer' (born-digital native text) pages
live: the legacy fraud corpus (by design) vs the newly-added legal corpus
(which must be 100% frontier vision)."""
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

    # sha -> corpus (from the chunk that represents it)
    sha_corpus = {}
    for c in ch.find({"source_type": "attachment"},
                     {"sha256": 1, "corpus": 1}):
        sha = c.get("sha256")
        if sha not in sha_corpus:
            sha_corpus[sha] = c.get("corpus") or "(none)"

    by_corpus_pages = Counter()
    by_corpus_atts = Counter()
    legal_samples = []
    for a in av2.find({"extraction.pages.method": "text_layer"},
                      {"sha256": 1, "filename": 1,
                       "extraction.pages.method": 1}):
        n = sum(1 for p in (a.get("extraction") or {}).get("pages") or []
                if p.get("method") == "text_layer")
        if n == 0:
            continue
        corp = sha_corpus.get(a.get("sha256"), "(not-chunked/noise)")
        by_corpus_pages[corp] += n
        by_corpus_atts[corp] += 1
        if corp == "legal_correspondence" and len(legal_samples) < 20:
            legal_samples.append((a.get("filename"), n))

    print("text_layer pages by corpus:")
    for k, v in by_corpus_pages.most_common():
        print(f"  {k:<24} pages={v:<6} attachments={by_corpus_atts[k]}")
    if legal_samples:
        print("\nLEGAL-corpus text_layer samples (THESE WOULD VIOLATE force-vision):")
        for fn, n in legal_samples:
            print(f"  {n}x  {str(fn)[:60]}")
    else:
        print("\nNo text_layer pages in legal_correspondence corpus.")
    m.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
