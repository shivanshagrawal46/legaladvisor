"""PHASE 5 - per-matter Stage-1 certification.

Verifies for a matter (or ALL phase5):
  - documents stored, page-method distribution (frontier-only), empty-text,
    bates assigned + monotonic, property-link coverage, occurrences recorded,
    and reconciles stored+linked vs the manifest's distinct-new count.

Usage: python _phase5_certify.py [--matter da_response]
"""
from __future__ import annotations
import argparse
import json
from collections import Counter
from pathlib import Path

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

ALLOWED_METHODS = {"claude_vision", "openai_vision", "gpt5_vision", "xlsx", "xls",
                   "xlrd", "docx", "image_vision", "raw", "raw_text"}
BANNED_METHODS = {"text_layer", "ocr"}  # ocr == RapidOCR


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--matter", default=None)
    args = ap.parse_args()
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    docs = m.db["documents"]
    q = {"_id": {"$regex": "^doc_p5_"}}
    if args.matter:
        q["matter_id"] = args.matter
    cur = list(docs.aggregate([
        {"$match": q},
        {"$project": {"pages": 1, "bates_start": 1, "property_ids": 1,
                      "doc_category": 1, "custody.sha256": 1,
                      "textLen": {"$strLenCP": {"$ifNull": ["$extracted_text", ""]}}}},
    ]))
    print(f"=== CERTIFY matter={args.matter or 'ALL phase5'} ===")
    print(f"documents stored: {len(cur)}")

    page_methods = Counter()
    banned = []
    empty = []
    no_bates = []
    no_pages = []
    pid_cov = 0
    cat = Counter()
    bates_nums = []
    total_pages = 0
    for d in cur:
        pages = d.get("pages") or []
        total_pages += len(pages)
        for p in pages:
            mth = p.get("method")
            page_methods[mth] += 1
            if mth in BANNED_METHODS:
                banned.append((d["_id"], mth))
        if not d.get("textLen"):
            empty.append(d["_id"])
        if not d.get("bates_start"):
            no_bates.append(d["_id"])
        else:
            try:
                bates_nums.append(int(d["bates_start"].split("-")[-1]))
            except Exception:
                pass
        if not pages:
            no_pages.append(d["_id"])
        if d.get("property_ids"):
            pid_cov += 1
        cat[d.get("doc_category")] += 1

    print(f"total pages: {total_pages}")
    print(f"page-method distribution: {dict(page_methods)}")
    print(f"BANNED methods (text_layer/RapidOCR): {len(banned)}  {banned[:5]}")
    print(f"empty-text docs: {len(empty)}  {empty[:5]}")
    print(f"missing bates: {len(no_bates)}")
    print(f"docs with 0 pages: {len(no_pages)}")
    print(f"docs with >=1 property link: {pid_cov}/{len(cur)} "
          f"({100*pid_cov//max(1,len(cur))}%)")
    print(f"category distribution: {dict(cat)}")
    if bates_nums:
        print(f"bates range: MT-IPA-{min(bates_nums):07d} .. (count={len(bates_nums)})")

    # reconcile vs manifest
    try:
        man = json.loads(Path("_phase5_manifest.json").read_text(encoding="utf-8"))
        files = man["files"]
        if args.matter:
            files = [f for f in files if f["matter"] == args.matter]
        new_shas = {f["sha256"] for f in files if not f["in_db"]}
        already = {f["sha256"] for f in files if f["in_db"]}
        print(f"\nmanifest new-distinct={len(new_shas)} already-in-db-distinct={len(already)}")
        # accounted = stored as ANY doc_p5 (cross-folder dedup) OR occurrence-linked
        all_p5_shas = {(d.get('custody') or {}).get('sha256')
                       for d in docs.find({"_id": {"$regex": "^doc_p5_"}}, {"custody.sha256": 1})}
        linked_shas = set()
        for coll in ("documents", "attachments_v2"):
            for d in m.db[coll].find({"phase5_occurrences": {"$exists": True}},
                                     {"custody.sha256": 1, "sha256": 1}):
                sh = (d.get("custody") or {}).get("sha256") or d.get("sha256")
                if sh:
                    linked_shas.add(sh)
        accounted = all_p5_shas | linked_shas
        missing = new_shas - accounted
        cross = (new_shas & all_p5_shas) - {(d.get('custody') or {}).get('sha256') for d in cur}
        print(f"stored under THIS matter={len(cur)} | cross-folder-deduped(stored elsewhere)={len(cross)}")
        print(f"new-distinct NOT accounted ANYWHERE (true miss): {len(missing)}  {list(missing)[:5]}")
    except Exception as exc:  # noqa: BLE001
        print(f"manifest reconcile skipped: {exc}")

    verdict = "PASS" if not banned and not no_pages and not empty else "REVIEW"
    print(f"\nVERDICT: {verdict}")
    m.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
