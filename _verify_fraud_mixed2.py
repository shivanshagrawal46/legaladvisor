"""Resolve the 2 soft flags: actual embedding dim + the 4 'stale text' chunks."""
from __future__ import annotations
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import Settings
from src.db.mongo import MongoClientWrapper


def norm(t: str) -> str:
    return " ".join((t or "").split()).lower()


def main() -> int:
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    m.ping()
    ch = m.db["email_chunks_v2"]
    v2 = m.db["attachments_v2"]

    shas = [ln.strip() for ln in Path("_fraud_mixed_done_sha.txt").read_text(
        encoding="utf-8").splitlines() if ln.strip()]

    # 1) actual embedding dims + models across the 27 sha
    dims = Counter()
    models = Counter()
    fields = Counter()
    for c in ch.find({"sha256": {"$in": shas}, "source_type": "attachment"},
                     {"embedding": 1, "embedding_model": 1, "raw_text": 1, "text": 1}):
        emb = c.get("embedding") or []
        dims[len(emb)] += 1
        models[c.get("embedding_model")] += 1
        fields["has_raw_text" if c.get("raw_text") else "no_raw_text"] += 1
    print("embedding dims :", dict(dims))
    print("embedding model:", dict(models))
    print("raw_text field :", dict(fields))

    # 2) re-test staleness with NORMALIZED whitespace (the real test)
    print("\nstaleness re-test (normalized whitespace):")
    truly_stale = 0
    checked = 0
    for sha in shas:
        a = v2.find_one({"sha256": sha}, {"extracted_text": 1})
        cur = norm((a or {}).get("extracted_text") or "")
        for c in ch.find({"sha256": sha, "source_type": "attachment"},
                         {"text": 1, "contextual_summary": 1, "chunk_index": 1}):
            checked += 1
            body = c.get("text") or ""
            cs = c.get("contextual_summary") or ""
            if cs and body.startswith(cs):
                body = body[len(cs):]
            body = norm(body)
            if len(body) < 40:
                continue
            mid = body[len(body)//2: len(body)//2 + 50]
            if mid and mid not in cur:
                truly_stale += 1
                print(f"  STALE? sha={sha[:10]} idx={c.get('chunk_index')} "
                      f"probe={mid!r}")
    print(f"checked={checked}  truly_stale={truly_stale}")
    m.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
