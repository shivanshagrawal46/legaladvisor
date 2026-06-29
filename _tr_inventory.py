"""Inventory E:\\missing title reports: hash every file, dedup vs DB,
map each address folder to a property entity. Read-only."""
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from scripts.ingest_titles_full import norm_address, addr_core
from scripts.ingest_insurance import build_prop_index

ROOT = Path(r"E:\missing title reports")
DOC_EXTS = {".pdf", ".tif", ".tiff", ".jpg", ".jpeg", ".png", ".docx", ".doc"}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
docs = m.db["documents"]
ents = m.db["entities"]

# existing fingerprints
db_shas = set()
for d in docs.find({}, {"custody.sha256": 1}):
    sh = (d.get("custody") or {}).get("sha256")
    if sh:
        db_shas.add(sh)
print(f"existing DB doc SHAs: {len(db_shas)}")

prop_idx = build_prop_index(ents)
print(f"property index keys: {len(prop_idx)}")

folders = sorted([p for p in ROOT.iterdir() if p.is_dir()])
print(f"property folders in missing-title-reports: {len(folders)}")

total_files = total_docs = new_docs = dup_docs = 0
matched_folders = unmatched_folders = 0
report = []
for fld in folders:
    files = [p for p in fld.rglob("*") if p.is_file()]
    docfiles = [p for p in files if p.suffix.lower() in DOC_EXTS]
    total_files += len(files)
    total_docs += len(docfiles)
    # match folder address to property entity
    ac = addr_core(norm_address(fld.name))
    pid = prop_idx.get(ac)
    if pid:
        matched_folders += 1
    else:
        unmatched_folders += 1
    fnew = fdup = 0
    fdetails = []
    for p in docfiles:
        try:
            sh = sha256_file(p)
        except Exception as e:  # noqa: BLE001
            fdetails.append({"file": p.name, "error": str(e)[:60]})
            continue
        is_new = sh not in db_shas
        if is_new:
            new_docs += 1
            fnew += 1
        else:
            dup_docs += 1
            fdup += 1
        fdetails.append({"file": str(p.relative_to(ROOT)), "sha": sh[:12], "new": is_new})
    report.append({"folder": fld.name, "addr_core": ac, "property_id": pid,
                   "n_docfiles": len(docfiles), "new": fnew, "dup": fdup,
                   "files": fdetails})

print("=" * 60)
print(f"total files          : {total_files}")
print(f"total doc files      : {total_docs}")
print(f"NEW (not in DB)      : {new_docs}")
print(f"already in DB (dup)  : {dup_docs}")
print(f"folders matched->prop: {matched_folders}")
print(f"folders UNMATCHED    : {unmatched_folders}")

Path("_tr_inventory.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("wrote _tr_inventory.json")
# show unmatched folders (need address fix)
print("\n--- UNMATCHED folders (no property entity via addr_core) ---")
for r in report:
    if not r["property_id"]:
        print(f"  [{r['n_docfiles']} files] {r['folder']}  (core='{r['addr_core']}')")
m.close()
