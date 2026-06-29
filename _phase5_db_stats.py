"""Full database statistics for the CEO report (read-only)."""
from __future__ import annotations
from collections import Counter

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper


def ext_to_type(ext: str) -> str:
    ext = (ext or "").lower().lstrip(".")
    if ext in ("pdf",):
        return "PDF"
    if ext in ("xlsx", "xls", "xlsm", "csv"):
        return "Excel/CSV"
    if ext in ("docx", "doc", "rtf"):
        return "Word"
    if ext in ("jpg", "jpeg", "png", "gif", "bmp", "tif", "tiff", "webp"):
        return "Image"
    if ext in ("mp3", "wav", "m4a", "aac", "ogg", "flac"):
        return "Audio"
    if ext in ("msg", "eml"):
        return "Email-file"
    if ext in ("txt", "log", "md", "html", "htm"):
        return "Text/HTML"
    if ext in ("zip", "rar", "7z"):
        return "Archive"
    return f"Other({ext})" if ext else "Other(none)"


def method_to_type(method) -> str:
    if not isinstance(method, str):
        method = ""
    method = method.lower()
    if method.startswith("pdf"):
        return "PDF"
    if method in ("xlsx", "xls", "xlrd", "excel_com"):
        return "Excel/CSV"
    if method in ("docx", "word_com"):
        return "Word"
    if method in ("image_vision", "image_ocr"):
        return "Image"
    if method in ("raw_text", "raw"):
        return "Text/HTML"
    return f"Other({method})"


def main() -> int:
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    db = m.db
    emails = db["emails"]
    av2 = db["attachments_v2"]
    docs = db["documents"]
    chunks = db["email_chunks_v2"]

    print("=" * 70)
    print("DATABASE STATISTICS")
    print("=" * 70)

    # ---- EMAILS ----
    n_emails = emails.count_documents({})
    n_email_body = emails.count_documents({"body_text": {"$nin": [None, ""]}})
    print(f"\n[EMAILS]")
    print(f"  emails (messages)        : {n_emails}")
    print(f"  with body text           : {n_email_body}")
    by_corpus_em = Counter()
    for d in emails.find({}, {"corpus": 1}):
        by_corpus_em[d.get("corpus") or "untagged"] += 1
    print(f"  by corpus                : {dict(by_corpus_em)}")

    # ---- ATTACHMENTS V2 (email attachments) ----
    n_av2 = av2.count_documents({})
    av2_type = Counter()
    av2_pages = 0
    av2_method = Counter()
    av2_text_chars = 0
    for a in av2.find({}, {"extension": 1, "filename": 1, "extraction": 1,
                           "extracted_via": 1, "extracted_text": 1}):
        ext = a.get("extension") or ("." + a.get("filename", "").rsplit(".", 1)[-1]
                                     if "." in a.get("filename", "") else "")
        av2_type[ext_to_type(ext)] += 1
        ex = a.get("extraction") or {}
        pgs = ex.get("pages")
        if isinstance(pgs, list):
            av2_pages += len(pgs)
            for p in pgs:
                if isinstance(p, dict):
                    av2_method[p.get("method") or "?"] += 1
        elif ex.get("page_count"):
            av2_pages += int(ex["page_count"])
        else:
            av2_pages += 1
        av2_text_chars += len(a.get("extracted_text") or "")
    print(f"\n[EMAIL ATTACHMENTS  (attachments_v2)]")
    print(f"  attachment records       : {n_av2}")
    print(f"  est. pages               : {av2_pages}")
    print(f"  by file type             : {dict(av2_type)}")
    print(f"  extracted text (chars)   : {av2_text_chars:,}")

    # ---- DOCUMENTS (phase3 records + phase5 discovery) ----
    n_docs = docs.count_documents({})
    n_p5 = docs.count_documents({"_id": {"$regex": "^doc_p5_"}})
    n_p3 = n_docs - n_p5
    doc_pages = 0
    p5_pages = 0
    doc_type = Counter()
    page_method = Counter()
    p5_by_matter = Counter()
    p5_text_chars = 0
    for d in docs.find({}, {"page_count": 1, "pages": 1, "extraction_method": 1,
                            "_id": 1, "matter_id": 1, "custody": 1, "extracted_text": 1}):
        pgs = d.get("pages")
        pc = len(pgs) if isinstance(pgs, list) and pgs else (d.get("page_count") or 1)
        doc_pages += pc
        is_p5 = str(d["_id"]).startswith("doc_p5_")
        if is_p5:
            p5_pages += pc
            p5_by_matter[d.get("matter_id") or "?"] += 1
            p5_text_chars += len(d.get("extracted_text") or "")
        doc_type[method_to_type(d.get("extraction_method"))] += 1
        if isinstance(pgs, list):
            for p in pgs:
                if isinstance(p, dict):
                    page_method[p.get("method") or "?"] += 1
    print(f"\n[DOCUMENTS  (discovery / title / insurance / litigation)]")
    print(f"  total document records   : {n_docs}")
    print(f"    - phase-5 (E: drive)    : {n_p5}")
    print(f"    - earlier (phase 2/3)   : {n_p3}")
    print(f"  total pages (all docs)    : {doc_pages}")
    print(f"  phase-5 pages so far      : {p5_pages}")
    print(f"  phase-5 text (chars)      : {p5_text_chars:,}")
    print(f"  phase-5 by matter         : {dict(p5_by_matter)}")
    print(f"  doc type (by extraction)  : {dict(doc_type)}")
    print(f"  phase-5 page-method tally : {dict(page_method)}")

    # ---- VECTOR INDEX ----
    n_chunks = chunks.count_documents({})
    n_p5_chunks = chunks.count_documents({"document_id": {"$regex": "^doc_p5_"}})
    ch_corpus = Counter()
    for d in chunks.find({}, {"corpus": 1}):
        ch_corpus[d.get("corpus") or "untagged"] += 1
    print(f"\n[VECTOR INDEX  (email_chunks_v2)]")
    print(f"  total searchable chunks   : {n_chunks}")
    print(f"    - phase-5 doc chunks    : {n_p5_chunks}")
    print(f"  by corpus                 : {dict(ch_corpus)}")

    # ---- COMBINED FILE-TYPE TOTALS ----
    print(f"\n[COMBINED FILE-TYPE TOTALS  (attachments + documents)]")
    combined = Counter(av2_type)
    combined.update(doc_type)
    for k, v in sorted(combined.items(), key=lambda x: -x[1]):
        print(f"    {k:14s}: {v}")

    # ---- KNOWLEDGE GRAPH ----
    print(f"\n[KNOWLEDGE GRAPH / INTELLIGENCE]")
    for c in ["entities", "relationships", "events", "findings",
              "property_dossier", "fact_clusters", "money_records"]:
        if c in db.list_collection_names():
            print(f"    {c:18s}: {db[c].estimated_document_count()}")

    # ---- GRAND TOTALS ----
    total_pages = av2_pages + doc_pages
    print(f"\n[GRAND TOTALS]")
    print(f"  emails (messages)         : {n_emails}")
    print(f"  attachment files          : {n_av2}")
    print(f"  standalone documents      : {n_docs}")
    print(f"  ---- OCR/extracted pages (attachments + docs): {total_pages} ----")
    print(f"  searchable vector chunks  : {n_chunks}")
    m.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
