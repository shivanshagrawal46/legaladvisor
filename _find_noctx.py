import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
mongo = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
try:
    ch = mongo.db["email_chunks_v2"]
    q = {"$or": [{"context": {"$exists": False}}, {"context": None}, {"context": ""}]}
    n = ch.count_documents(q)
    print("chunks missing context:", n)
    by_src = Counter()
    by_corpus = Counter()
    by_via = Counter()
    has_body = 0
    short_body = 0
    samp = []
    for c in ch.find(q, {"source_type": 1, "corpus": 1, "sha256": 1, "filename": 1,
                         "body": 1, "text": 1, "n_tokens": 1, "subject": 1}):
        by_src[c.get("source_type")] += 1
        by_corpus[c.get("corpus")] += 1
        b = (c.get("body") or c.get("text") or "")
        if b.strip():
            has_body += 1
        if len(b.strip()) < 30:
            short_body += 1
        if len(samp) < 12:
            samp.append((c.get("source_type"), c.get("corpus"),
                         (c.get("filename") or c.get("subject") or "")[:40],
                         len(b.strip()), c.get("n_tokens")))
    print("by source_type:", dict(by_src))
    print("by corpus     :", dict(by_corpus))
    print("with non-empty body:", has_body, "| body<30 chars:", short_body)
    print("samples (src, corpus, name, body_len, n_tokens):")
    for x in samp:
        print("   ", x)
finally:
    mongo.close()
