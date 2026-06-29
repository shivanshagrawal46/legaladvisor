"""Trace the 197 unresolved email->attachment refs / 93 fully-unresolved emails.
Determine: are these genuinely missing documents, or refs into the LEGACY
'attachments' collection whose content (by sha) is already present in
attachments_v2 (benign), or noise that was correctly skipped?
"""
from __future__ import annotations
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import Settings
from src.db.mongo import MongoClientWrapper


def main() -> int:
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    m.ping()
    emails = m.db["emails"]
    av2 = m.db["attachments_v2"]
    legacy = m.db["attachments"]
    ch = m.db["email_chunks_v2"]

    av2_ids = {a["_id"] for a in av2.find({}, {"_id": 1})}
    av2_shas = {a.get("sha256") for a in av2.find({}, {"sha256": 1})}
    av2_text_shas = {a.get("sha256") for a in av2.find(
        {"extracted_text": {"$nin": ["", None]}}, {"sha256": 1})}
    legacy_ids = {a["_id"] for a in legacy.find({}, {"_id": 1})}
    legacy_id_sha = {a["_id"]: a.get("sha256")
                     for a in legacy.find({}, {"_id": 1, "sha256": 1})}
    print(f"av2 ids={len(av2_ids)} av2 sha={len(av2_shas)} "
          f"legacy ids={len(legacy_ids)}")

    # classify every unresolved ref
    cls = Counter()
    fully_unresolved = []   # emails whose every att ref is unresolved
    sample_genuine = []
    for e in emails.find({"attachment_ids": {"$exists": True, "$ne": []}},
                         {"attachment_ids": 1, "subject": 1, "from": 1,
                          "date": 1, "folder_path": 1, "corpus": 1}):
        aids = e.get("attachment_ids") or []
        miss = [a for a in aids if a not in av2_ids]
        if not miss:
            continue
        all_miss = len(miss) == len(aids)
        for aid in miss:
            if aid in legacy_ids:
                sha = legacy_id_sha.get(aid)
                if sha in av2_text_shas:
                    cls["legacy_ref_but_sha_present_with_text"] += 1
                elif sha in av2_shas:
                    cls["legacy_ref_but_sha_present_noise"] += 1
                else:
                    cls["legacy_ref_sha_ABSENT_from_av2"] += 1
            else:
                cls["ref_not_in_legacy_or_av2"] += 1
        if all_miss:
            # is this email's content recoverable some other way?
            # check if any of its missing legacy refs have sha present
            recoverable = any(
                legacy_id_sha.get(a) in av2_text_shas for a in miss)
            fully_unresolved.append({
                "subject": (e.get("subject") or "")[:50],
                "from": e.get("from"), "date": str(e.get("date"))[:10],
                "corpus": e.get("corpus"),
                "n_miss": len(miss),
                "recoverable": recoverable,
                "miss_in_legacy": all(a in legacy_ids for a in miss),
            })

    print("\nclassification of the unresolved refs:")
    for k, v in cls.items():
        print(f"   {k}: {v}")

    print(f"\nfully-unresolved emails: {len(fully_unresolved)}")
    rec = sum(1 for x in fully_unresolved if x["recoverable"])
    print(f"   ...whose content IS present in av2 by sha (benign): {rec}")
    print(f"   ...genuinely missing content                      : "
          f"{len(fully_unresolved) - rec}")

    print("\nsample of fully-unresolved emails:")
    for x in fully_unresolved[:25]:
        print(f"   [{x['corpus']}] {x['date']} miss={x['n_miss']} "
              f"recoverable={x['recoverable']} inLegacy={x['miss_in_legacy']} "
              f"| {x['subject']!r}")

    m.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
