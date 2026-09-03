"""Final verification of the partner batch: field parity, classification,
Clean-mode posture, and live vector retrievability."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.rag.embedder import VoyageEmbedder

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
em, ch = m.db["emails"], m.db["email_chunks_v2"]

mails = list(em.find({"pst_entry_id": {"$regex": "^partners:"}}))
ids = [d["_id"] for d in mails]
chunks = list(ch.find({"email_id": {"$in": ids}, "source_type": "email_body"}))
print(f"partner emails={len(mails)}  chunks={len(chunks)}")

REQUIRED = ["matter_id", "corpus", "privilege_status", "evidentiary_class",
            "doc_authority_score", "entity_ids", "entity_refs", "context",
            "text", "embedding", "n_tokens", "chunk_index", "email_id",
            "is_ours", "party_alignment", "content_kind"]

print("\n=== 1. field parity ===")
ok = True
for c in chunks:
    missing = [f for f in REQUIRED if c.get(f) in (None, "", [])]
    tag = "OK" if not missing else "MISSING " + ",".join(missing)
    if missing:
        ok = False
    print(f"  {c.get('from_email')[:34]:36s} idx={c.get('chunk_index')} "
          f"tok={c.get('n_tokens'):<5} dim={len(c.get('embedding') or [])}  {tag}")

print("\n=== 2. chunking config (1000/200) ===")
for c in chunks:
    print(f"  {c.get('from_email')[:34]:36s} n_tokens={c.get('n_tokens')} "
          f"(<=1000 {'OK' if c.get('n_tokens') <= 1000 else 'OVER'})  "
          f"context_prepended={(c.get('text') or '').startswith('[Context]')}")

print("\n=== 3. classification ===")
for c in chunks:
    print(f"  {c.get('from_email')[:34]:36s} priv={c.get('privilege_status')} "
          f"corpus={c.get('corpus')} class={c.get('evidentiary_class')} "
          f"auth={c.get('doc_authority_score')}")
    print(f"       is_ours={c.get('is_ours')} align={c.get('party_alignment')} "
          f"role={c.get('sender_role')} kind={c.get('content_kind')} "
          f"quotes_draft={c.get('quotes_draft_letter')} adverse={c.get('adverse_source')}")

print("\n=== 4. Clean mode: not_privileged => VISIBLE in shareable output ===")
print(f"  chunks excluded by Clean mode (privilege_status='privileged'): "
      f"{ch.count_documents({'email_id': {'$in': ids}, 'privilege_status': 'privileged'})}")

print("\n=== 5. threading ===")
for d in mails:
    print(f"  {d['from']['email'][:34]:36s} thread_id={d.get('thread_id')}")
print(f"  both in one thread: "
      f"{len({d.get('thread_id') for d in mails}) == 1}")

print("\n=== 6. live vector retrieval ===")
emb = VoyageEmbedder(s.voyage_api_key, model=s.embedding_model)
queries = [
    "What feedback did MangoTree partners give on the litigation update letter?",
    "partner wants explanation of adequate protection payment and when funds distributed",
    "investors say the letter has too much legal jargon and needs plain explanation",
    "what does the $1.5 million recovery mean for me as a partner",
]
chunk_ids = {c["_id"] for c in chunks}
for q in queries:
    v = emb.embed_query(q)
    res = list(ch.aggregate([
        {"$vectorSearch": {"index": "email_chunks_v2_vector", "path": "embedding",
                           "queryVector": v, "numCandidates": 400, "limit": 8}},
        {"$project": {"from_email": 1, "subject": 1, "privilege_status": 1,
                      "score": {"$meta": "vectorSearchScore"}}},
    ]))
    rank = next((i + 1 for i, r in enumerate(res) if r["_id"] in chunk_ids), None)
    print(f"\n  Q: {q[:66]}")
    print(f"     partner chunk rank: {rank if rank else 'NOT IN TOP 8'}")
    for i, r in enumerate(res[:3], 1):
        mark = "<<<" if r["_id"] in chunk_ids else ""
        print(f"       {i}. {r.get('score'):.4f}  {str(r.get('from_email'))[:30]:32s}"
              f"{str(r.get('subject'))[:34]} {mark}")
m.close()
print(f"\nPARITY: {'PASS' if ok else 'FAIL'}")
