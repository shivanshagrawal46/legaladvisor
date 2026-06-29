"""Audit the TRUE per-page OCR method for every title doc, from the pages[]
array (authoritative) rather than the stale doc-level extraction_method counter.
Reports how many docs / pages are actually non-frontier."""
from collections import Counter

import config.settings  # noqa
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

FRONTIER = {"claude_vision", "openai_vision"}


def main():
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    docs = m.db["documents"]
    proj = {"pages": 1, "extraction_method": 1, "page_count": 1, "ocr_repaired_at": 1}

    method_pages = Counter()      # true per-page methods (from pages[])
    counter_methods = Counter()   # doc-level counter methods
    docs_total = 0
    docs_no_pages = 0
    docs_nonfrontier_pages = 0
    nonfrontier_page_total = 0
    stale_counter_docs = 0        # counter says ocr but pages[] all frontier
    truly_nonfrontier = []        # (id, count) docs with real non-frontier pages

    for d in docs.find({"source_type": "title_report"}, proj):
        docs_total += 1
        em = d.get("extraction_method")
        if isinstance(em, dict):
            for k, v in em.items():
                counter_methods[k] += v
        elif isinstance(em, str):
            counter_methods[em] += 1

        pages = d.get("pages")
        if not isinstance(pages, list) or not pages:
            docs_no_pages += 1
            continue
        nf = 0
        for p in pages:
            meth = (p.get("method") or p.get("ocr_method") or "unknown") if isinstance(p, dict) else "unknown"
            method_pages[meth] += 1
            if meth not in FRONTIER:
                nf += 1
        if nf:
            docs_nonfrontier_pages += 1
            nonfrontier_page_total += nf
            truly_nonfrontier.append((d["_id"], nf))
        else:
            # fully frontier per pages[]; was the counter claiming ocr?
            if isinstance(em, dict) and any(k not in FRONTIER for k in em):
                stale_counter_docs += 1

    print(f"title docs total: {docs_total}  (no pages[] array: {docs_no_pages})")
    print(f"\nTRUE per-page methods (from pages[]): {dict(method_pages)}")
    print(f"doc-level counter methods (extraction_method): {dict(counter_methods)}")
    print(f"\nDocs with REAL non-frontier pages (pages[]): {docs_nonfrontier_pages} "
          f"({nonfrontier_page_total} pages)")
    print(f"Docs whose counter says non-frontier but pages[] are ALL frontier (STALE): {stale_counter_docs}")
    print("\nSample truly non-frontier docs:")
    for _id, n in sorted(truly_nonfrontier, key=lambda x: -x[1])[:30]:
        print(f"   {_id}  non_frontier_pages={n}")
    m.close()


if __name__ == "__main__":
    main()
