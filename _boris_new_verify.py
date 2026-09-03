"""Final verification of the 3-email Boris batch (revised brief + blackline)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tiktoken

from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.rag.embedder import VoyageEmbedder

OLD_SHA = "341b728e0fb1549b4f7638e77f9a2358fb067e3df3ea20fd05e2c00512b8bed6"

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
em, att, av2, ch = (m.db["emails"], m.db["attachments"],
                    m.db["attachments_v2"], m.db["email_chunks_v2"])
enc = tiktoken.get_encoding("cl100k_base")

gids = [ln.strip() for ln in Path("_boris_backfill_ids.csv").read_text(
    encoding="utf-8").splitlines()[1:] if ln.strip()]
eids = [d["_id"] for g in gids
        for d in [em.find_one({"$or": [{"gmail_id": g},
                                       {"pst_entry_id": "gmail:" + g}]}, {"_id": 1})] if d]
shas = sorted({a["sha256"] for a in att.find({"email_id": {"$in": eids}}, {"sha256": 1})
               if a.get("sha256")})
chunks = list(ch.find({"$or": [{"sha256": {"$in": shas}},
                               {"email_id": {"$in": eids}, "source_type": "email_body"}]}))
print(f"emails={len(eids)}  attachments={len(shas)}  chunks={len(chunks)}")

print("\n=== 1. house rule: PDFs via vision, DOCX native ===")
for sha in shas:
    a = att.find_one({"sha256": sha}, {"filename": 1})
    v2 = av2.find_one({"sha256": sha}, {"extraction": 1, "extracted_text": 1})
    meth = ((v2 or {}).get("extraction") or {}).get("method")
    fn = (a or {}).get("filename", "")
    ok = ("pdf_ocr" in str(meth)) if fn.lower().endswith(".pdf") else True
    print(f"   {fn[:48]:50s} method={str(meth):<10} chars={len(v2.get('extracted_text') or ''):>7,}  "
          f"{'OK' if ok else 'VIOLATION — pdf not vision-OCRd'}")

print("\n=== 2. field parity ===")
REQ = ["matter_id", "corpus", "privilege_status", "evidentiary_class",
       "doc_authority_score", "entity_refs", "context", "text", "embedding",
       "n_tokens", "chunk_index"]
bad = 0
for c in chunks:
    miss = [f for f in REQ if c.get(f) in (None, "", [])]
    if miss:
        bad += 1
        print(f"   {c.get('source_type')} idx={c.get('chunk_index')} MISSING {miss}")
print(f"   chunks with all required fields: {len(chunks) - bad}/{len(chunks)}")

print("\n=== 3. token cap (payload <= 1000) ===")
over = 0
for c in chunks:
    t = c.get("text") or ""
    payload = t.split("\n", 1)[-1] if t.startswith("[Context]") else t
    n = len(enc.encode(payload))
    if n > 1000:
        over += 1
        print(f"   OVER: idx={c.get('chunk_index')} payload={n}")
print(f"   chunks over cap: {over}")
print(f"   context prepended on all: "
      f"{all((c.get('text') or '').startswith('[Context]') for c in chunks)}")
print(f"   embedding dim 1024 on all: "
      f"{all(len(c.get('embedding') or []) == 1024 for c in chunks)}")

print("\n=== 4. version lineage ===")
for sha, label in [(s2, l) for s2, l in
                   [(shas[0], "new-A"), (shas[1], "new-B")] ] + [(OLD_SHA, "2 Sep")]:
    c = ch.find_one({"sha256": sha}, {"document_version": 1, "doc_authority_score": 1,
                                      "is_current_draft": 1, "is_superseded": 1,
                                      "is_redline": 1, "filename": 1})
    if c:
        print(f"   {str(c.get('filename'))[:44]:46s} auth={c.get('doc_authority_score')} "
              f"current={c.get('is_current_draft')} superseded={c.get('is_superseded')} "
              f"redline={c.get('is_redline')}")

print("\n=== 5. entity linkage ===")
for st in ("attachment", "email_body"):
    sub = [c for c in chunks if c.get("source_type") == st]
    linked = sum(1 for c in sub if c.get("entity_ids"))
    print(f"   {st:12s} {linked}/{len(sub)} linked")

print("\n=== 6. live vector retrieval ===")
emb = VoyageEmbedder(s.voyage_api_key, model=s.embedding_model)
ids = {c["_id"] for c in chunks}
for q in ["revised IPA sanctions brief blackline changes",
          "what did Heuer change in the revised draft brief",
          "CrossCountry stay relief sheriff auction 31FO adjourned"]:
    v = emb.embed_query(q)
    res = list(ch.aggregate([
        {"$vectorSearch": {"index": "email_chunks_v2_vector", "path": "embedding",
                           "queryVector": v, "numCandidates": 400, "limit": 8}},
        {"$project": {"filename": 1, "subject": 1, "is_current_draft": 1,
                      "score": {"$meta": "vectorSearchScore"}}}]))
    rank = next((i + 1 for i, r in enumerate(res) if r["_id"] in ids), None)
    print(f"\n   Q: {q[:60]}")
    print(f"      new-batch rank: {rank if rank else 'NOT IN TOP 8'}")
    for i, r in enumerate(res[:3], 1):
        mark = "<<<" if r["_id"] in ids else ""
        nm = r.get("filename") or r.get("subject")
        print(f"        {i}. {r.get('score'):.4f} {str(nm)[:44]:46s}{mark}")
m.close()
