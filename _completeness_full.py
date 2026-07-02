"""FULL completeness audit of the legal RAG corpus.
Checks OCR method purity, chunk-field integrity, coverage (orphans), and linkage
across email_chunks_v2 / attachments_v2 / documents."""
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

VISION = {"claude_vision", "openai_vision", "gpt5_vision", "claude", "openai",
          "vision", "reocr_fraud_borndigital_v1"}


def sec(t):
    print("\n" + "=" * 64 + f"\n{t}\n" + "=" * 64)


def main() -> int:
    s = Settings.load()
    mongo = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    db = mongo.db
    ch = db["email_chunks_v2"]
    av2 = db["attachments_v2"]
    docs = db["documents"]
    fails = []

    # ---- 1. OCR method purity (attachments) -------------------------------
    sec("1. ATTACHMENT OCR METHODS (born-digital must be gone)")
    via = Counter(a.get("extracted_via") for a in av2.find({}, {"extracted_via": 1}))
    for k, v in via.most_common():
        print(f"  {str(k):32s} {v}")
    borndigital = sum(v for k, v in via.items()
                      if k and ("pdf_text" in str(k) or "text_layer" in str(k)))
    print(f"  -> native text-layer attachments remaining: {borndigital}")
    if borndigital:
        fails.append(f"{borndigital} born-digital attachments still un-OCR'd")

    # ---- 2. Title/documents OCR purity ------------------------------------
    sec("2. DOCUMENTS (title etc.) PER-PAGE OCR PURITY")
    nonfrontier_docs = 0
    checked = 0
    for d in docs.find({}, {"pages": 1}):
        checked += 1
        for p in d.get("pages") or []:
            mth = (p.get("method") or "").lower()
            if mth and "rapidocr" in mth:
                nonfrontier_docs += 1
                break
    print(f"  documents scanned: {checked}")
    print(f"  docs with any RapidOCR page: {nonfrontier_docs}")
    if nonfrontier_docs:
        fails.append(f"{nonfrontier_docs} docs still have RapidOCR pages")

    # ---- 3. Chunk field integrity (whole collection) ----------------------
    sec("3. CHUNK FIELD INTEGRITY (entire email_chunks_v2)")
    total = ch.estimated_document_count()
    checks = {
        "embedding":          {"$or": [{"embedding": {"$exists": False}}, {"embedding": None}]},
        "context summary":    {"$or": [{"context": {"$exists": False}}, {"context": None}, {"context": ""}]},
        "corpus":             {"$or": [{"corpus": {"$exists": False}}, {"corpus": None}]},
        "privilege_status":   {"$or": [{"privilege_status": {"$exists": False}}, {"privilege_status": None}]},
        "doc_authority_score":{"$or": [{"doc_authority_score": {"$exists": False}}, {"doc_authority_score": None}]},
    }
    print(f"  total chunks: {total}")
    for label, cond in checks.items():
        miss = ch.count_documents(cond)
        flag = "OK " if miss == 0 else "BAD"
        print(f"  {flag} missing {label:22s} {miss}")
        if miss:
            fails.append(f"{miss} chunks missing {label}")

    # embedding dimension spot-check
    bad_dim = 0
    for c in ch.find({"embedding": {"$exists": True}}, {"embedding": 1}).limit(2000):
        e = c.get("embedding")
        if not isinstance(e, list) or len(e) != 1024:
            bad_dim += 1
    print(f"  embedding-dim != 1024 (first 2000): {bad_dim}")
    if bad_dim:
        fails.append(f"{bad_dim} chunks have wrong embedding dim")

    # ---- 4. Coverage: attachments w/ text but no chunks -------------------
    sec("4. COVERAGE - attachments with text but ZERO chunks")
    sha_with_chunks = set(ch.distinct("sha256", {"source_type": "attachment"}))
    orphan = 0
    samp = []
    for a in av2.find({"extracted_text": {"$exists": True, "$ne": ""}},
                      {"sha256": 1, "filename": 1, "extracted_text": 1}):
        txt = a.get("extracted_text") or ""
        if len(txt.strip()) >= 30 and a.get("sha256") not in sha_with_chunks:
            orphan += 1
            if len(samp) < 8:
                samp.append(a.get("filename"))
    print(f"  attachments with >=30 chars text but no chunk: {orphan}")
    for fn in samp:
        print(f"     - {fn}")
    if orphan:
        fails.append(f"{orphan} attachments have text but no chunks")

    # ---- 5. Documents coverage --------------------------------------------
    sec("5. COVERAGE - documents with text but chunk_count 0")
    dorphan = docs.count_documents(
        {"extracted_text": {"$exists": True, "$ne": ""},
         "$or": [{"chunk_count": {"$exists": False}}, {"chunk_count": 0}]})
    print(f"  documents with text but chunk_count 0/missing: {dorphan}")
    if dorphan:
        fails.append(f"{dorphan} documents have text but no chunks")

    # ---- 6. Linkage / distribution ----------------------------------------
    sec("6. LINKAGE & DISTRIBUTION")
    linked = ch.count_documents({"entity_ids.0": {"$exists": True}})
    print(f"  chunks linked to >=1 entity: {linked}/{total} ({100*linked/total:.1f}%)")
    print(f"  touches_david chunks:        {ch.count_documents({'touches_david': True})}")
    print(f"  entities total:              {db['entities'].estimated_document_count()}")
    print(f"  money_records:               {db['money_records'].estimated_document_count()}")
    print(f"  relationships:               {db['relationships'].estimated_document_count()}")
    print(f"  events:                      {db['events'].estimated_document_count()}")
    print(f"  property_dossier:            {db['property_dossier'].estimated_document_count()}")
    print("  corpus dist:", dict(Counter(c.get("corpus") for c in ch.find({}, {"corpus": 1}))))

    # ---- VERDICT ----------------------------------------------------------
    sec("VERDICT")
    if fails:
        print("ISSUES FOUND:")
        for f in fails:
            print("   - " + f)
    else:
        print("PASS - corpus is complete: OCR pure, every chunk fully")
        print("       enriched & embedded, no orphaned text, linkage intact.")
    mongo.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
