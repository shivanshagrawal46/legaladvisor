"""Quantify which enrichment fields are missing on the freshly re-chunked
attachment docs (zip + rapidocr + born-digital). These tags are applied by
downstream scripts (corpus tagging, entity backfill, authority, privilege)
and must be re-run after re-chunking."""
from __future__ import annotations
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import Settings
from src.db.mongo import MongoClientWrapper

# sha that were re-extracted this session (need re-enrichment)
TAGS = ["reocr_borndigital_v1", "reocr_vision_v1", "zip_gpt5_vision"]


def main() -> int:
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    m.ping()
    av2 = m.db["attachments_v2"]
    ch = m.db["email_chunks_v2"]

    reocr_sha = set()
    for a in av2.find({"extracted_via": {"$in": TAGS}}, {"sha256": 1}):
        reocr_sha.add(a["sha256"])
    # also the zip
    for a in av2.find({"sha256": {"$regex": "^33c8d9696d14"}}, {"sha256": 1}):
        reocr_sha.add(a["sha256"])
    print(f"re-extracted sha this session: {len(reocr_sha)}")

    miss_corpus = miss_entity = miss_auth = miss_eclass = miss_priv = 0
    total = 0
    corpus_vals = Counter()
    for c in ch.find({"sha256": {"$in": list(reocr_sha)}, "source_type": "attachment"},
                     {"corpus": 1, "entity_ids": 1, "entity_refs": 1,
                      "doc_authority_score": 1, "evidentiary_class": 1,
                      "privilege_status": 1}):
        total += 1
        corpus_vals[c.get("corpus") or "(none)"] += 1
        if not c.get("corpus"):
            miss_corpus += 1
        if c.get("entity_ids") is None and c.get("entity_refs") is None:
            miss_entity += 1
        if c.get("doc_authority_score") is None:
            miss_auth += 1
        if not c.get("evidentiary_class"):
            miss_eclass += 1
        if not c.get("privilege_status"):
            miss_priv += 1

    print(f"re-chunked attachment chunks: {total}")
    print(f"  missing corpus tag        : {miss_corpus}")
    print(f"  missing entity link       : {miss_entity}")
    print(f"  missing authority score   : {miss_auth}")
    print(f"  missing evidentiary_class : {miss_eclass}")
    print(f"  missing privilege_status  : {miss_priv}")
    print(f"  corpus values: {dict(corpus_vals)}")
    m.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
