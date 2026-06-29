"""Deep-inspect the 2 re-OCR'd shas: page-level methods + char counts, and
whether the current chunks' text matches the current attachments_v2 text."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import Settings
from src.db.mongo import MongoClientWrapper

PREFIXES = {"zip(33c8)": "33c8d9696d14", "tiana(f28af4)": "f28af47ed442"}


def main() -> int:
    s = Settings.load()
    mongo = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    try:
        mongo.ping()
        v2 = mongo.db["attachments_v2"]
        ch = mongo.db["email_chunks_v2"]
        for label, pfx in PREFIXES.items():
            row = v2.find_one({"sha256": {"$regex": f"^{pfx}"}})
            if not row:
                print(f"\n{label}: NOT FOUND"); continue
            sha = row["sha256"]
            ext = row.get("extraction") or {}
            pages = ext.get("pages") or []
            from collections import Counter
            methods = Counter(p.get("method") for p in pages)
            print(f"\n=== {label}  sha={sha[:16]} fn={row.get('filename')!r}")
            print(f"  v2 method={ext.get('method')} pages={len(pages)} methods={dict(methods)}")
            print(f"  v2_text_len={len(row.get('extracted_text') or ''):,}")
            txt = row.get("extracted_text") or ""
            print(f"  v2_text_head: {txt[:300]!r}")
            # compare to a chunk
            c = ch.find_one({"sha256": sha, "source_type": "attachment"},
                            sort=[("chunk_index", 1)])
            if c:
                ctext = c.get("text") or ""
                # does the chunk body appear in current v2 text?
                core = ctext[-400:] if len(ctext) > 400 else ctext
                in_v2 = core.strip()[:120] in txt
                print(f"  first_chunk_len={len(ctext)} chunk_in_current_v2_text={in_v2}")
                print(f"  first_chunk_head: {ctext[:200]!r}")
        return 0
    finally:
        mongo.close()


if __name__ == "__main__":
    raise SystemExit(main())
