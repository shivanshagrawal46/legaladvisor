"""Classify how each missing-title file dedups vs DB:
  STRONG = same order#/dates (ProTitle) or order_type/dates (Prowess) + address
  WEAK   = only address-core fallback matched (RISK of collapsing distinct versions)
  NEW    = no match (will be extracted)
Uses pre-OCR text layer (same as pipeline). No API. Read-only.
"""
import json
from pathlib import Path

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from scripts.ingest_titles_full import (text_layer, prelim_meta, addr_core, norm_address,
                                        _parse_date)
from scripts.ingest_title_reports import parse_report, parse_prowess

ROOT = Path(r"E:\missing title reports")


def _addr_match(fkey: str, addr_norm: str) -> bool:
    a, b = (fkey or "").split(), (addr_norm or "").split()
    if not a or not b:
        return False
    if a[0].isdigit() or b[0].isdigit():
        if a[0] != b[0]:
            return False
    return len(set(a) & set(b)) >= 2 if (a[0].isdigit()) else len(set(a) & set(b)) >= 1
s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
docs = m.db["documents"]

# byte-new set from inventory
inv = json.load(open("_tr_inventory.json"))
sha_new_files = set()
for fld in inv:
    for f in fld["files"]:
        if f.get("new"):
            sha_new_files.add(f["file"])  # rel path under ROOT

db_addr_index = {}
for hit in docs.find({"source_type": "title_report"}, {"address_norm": 1, "is_update": 1}):
    ac = addr_core(hit.get("address_norm") or "")
    if ac:
        db_addr_index.setdefault((ac, bool(hit.get("is_update"))), hit["_id"])

pdfs = sorted([p for p in ROOT.rglob("*.pdf")])
strong = weak = new = bytedup = 0
weak_list, new_list = [], []
for p in pdfs:
    rel = str(p.relative_to(ROOT))
    text0 = text_layer(p, s)
    meta = prelim_meta(text0, p.name)
    pr = (parse_prowess(text0) if meta["vendor"] == "prowess"
          else parse_report(text0)) if meta["vendor"] else {}
    fkey = meta["fkey"]
    # strong match
    strong_hit = None
    if meta["vendor"] == "protitle" and pr.get("order_number"):
        for hit in docs.find({"source_type": "title_report", "vendor": "protitle",
                              "order_number": pr["order_number"]},
                             {"completed_date": 1, "index_date": 1, "address_norm": 1}):
            if (hit.get("completed_date") == _parse_date(pr.get("completed_date"))
                    and hit.get("index_date") == _parse_date(pr.get("index_date"))
                    and _addr_match(fkey, hit.get("address_norm") or "")):
                strong_hit = hit["_id"]; break
    elif meta["vendor"] == "prowess" and pr.get("order_type"):
        for hit in docs.find({"source_type": "title_report", "vendor": "prowess",
                              "order_type": pr["order_type"]},
                             {"search_date": 1, "old_effective_date": 1,
                              "new_effective_date": 1, "address_norm": 1}):
            if (hit.get("search_date") == _parse_date(pr.get("search_date"))
                    and hit.get("old_effective_date") == _parse_date(pr.get("old_effective_date"))
                    and hit.get("new_effective_date") == _parse_date(pr.get("new_effective_date"))
                    and _addr_match(fkey, hit.get("address_norm") or "")):
                strong_hit = hit["_id"]; break
    ac = addr_core(fkey or "")
    weak_hit = db_addr_index.get((ac, bool(meta.get("is_update")))) if ac else None
    byte_new = rel in sha_new_files

    if strong_hit:
        strong += 1
    elif weak_hit:
        weak += 1
        if byte_new:
            weak_list.append((rel, meta["vendor"], meta.get("is_update"), weak_hit))
    else:
        new += 1
        new_list.append((rel, meta["vendor"], meta.get("is_update")))
    if not byte_new:
        bytedup += 1

print(f"total pdfs                 : {len(pdfs)}")
print(f"STRONG identity match      : {strong}")
print(f"WEAK addr-only match       : {weak}")
print(f"NEW (no match->extract)    : {new}")
print(f"byte-identical to DB       : {bytedup}")
print(f"\n--- WEAK matches that are BYTE-NEW (RISK: distinct version?) : {len(weak_list)} ---")
for x in weak_list:
    print("  ", x)
print(f"\n--- NEW (definitely extract) : {len(new_list)} ---")
for x in new_list:
    print("  ", x)
m.close()
