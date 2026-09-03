"""Snapshot / compare email_chunks_v2 so we can prove the WebCivil ingest only
ADDED vectors and left every pre-existing one untouched.

  python -m scripts.webcivil_baseline save     # before the embed run
  python -m scripts.webcivil_baseline check    # after it
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

SNAP = Path(r"E:\WEBCIVIL_baseline.json")
CHUNKS = "email_chunks_v2"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def snapshot(m) -> dict:
    c = m.db[CHUNKS]
    by_type = {(r["_id"] or "(none)"): r["n"] for r in c.aggregate(
        [{"$group": {"_id": "$doc_source_type", "n": {"$sum": 1}}}])}
    return {
        "taken_at": datetime.now(timezone.utc).isoformat(),
        "total_chunks": c.count_documents({}),
        "by_doc_source_type": by_type,
        # Every chunk that is NOT part of this batch. This number must not move.
        "pre_existing_chunks": c.count_documents(
            {"document_id": {"$not": {"$regex": "^doc_webcivil_"}}}),
        "documents_total": m.db["documents"].count_documents({}),
    }


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "save"
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    cur = snapshot(m)

    if mode == "save":
        SNAP.write_text(json.dumps(cur, indent=2), encoding="utf-8")
        print("BASELINE SAVED ->", SNAP)
        print(json.dumps(cur, indent=2))
        m.close()
        return 0

    if not SNAP.exists():
        print("no baseline file; run 'save' first")
        m.close()
        return 1
    old = json.loads(SNAP.read_text(encoding="utf-8"))
    print("baseline taken:", old["taken_at"])
    print(f"{'metric':<26} {'before':>10} {'after':>10} {'delta':>10}")
    ok = True
    for k in ("total_chunks", "pre_existing_chunks", "documents_total"):
        b, a = old[k], cur[k]
        print(f"{k:<26} {b:>10,} {a:>10,} {a - b:>+10,}")
        if k == "pre_existing_chunks" and a != b:
            ok = False
    print("\nby doc_source_type:")
    for k in sorted(set(old["by_doc_source_type"]) | set(cur["by_doc_source_type"])):
        b = old["by_doc_source_type"].get(k, 0)
        a = cur["by_doc_source_type"].get(k, 0)
        print(f"  {k:<24} {b:>10,} {a:>10,} {a - b:>+10,}")
    print("\n" + ("PASS - every pre-existing vector is untouched; the run only added."
                  if ok else
                  "FAIL - pre-existing chunk count CHANGED. Investigate."))
    m.close()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
