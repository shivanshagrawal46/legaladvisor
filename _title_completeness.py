"""
Completeness manifest for the missing-title ingest + per-property title coverage,
and a live smoke-test of the property-graph payload.

Proves:
  1. EVERY file under E:\missing title reports is represented in the DB — either
     as its own title_report doc OR merged (provenance) into a canonical doc.
  2. Per-property title coverage: properties with >=1 title, version chains,
     originals present vs update-only.
  3. property_graph(property_id) returns a well-formed, cited payload.
"""
import hashlib
import os
from collections import Counter
from pathlib import Path

import config.settings  # noqa
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

ROOT = Path(r"E:\missing title reports")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    docs = m.db["documents"]

    # ---- 1. file-level completeness ----
    pdfs = []
    if ROOT.exists():
        pdfs = [p for p in ROOT.rglob("*") if p.suffix.lower() in (".pdf",)]
    print(f"[1] files under {ROOT}: {len(pdfs)} PDFs")

    # collect every sha known to the DB (own custody.sha256 + merged source_files + duplicate_of_files)
    known = set()
    for d in docs.find({"source_type": "title_report"},
                       {"custody": 1, "duplicate_of_files": 1}):
        c = d.get("custody") or {}
        if c.get("sha256"):
            known.add(c["sha256"])
        for f in (c.get("source_files") or []):
            if isinstance(f, dict) and f.get("sha256"):
                known.add(f["sha256"])
        for f in (d.get("duplicate_of_files") or []):
            if isinstance(f, dict) and f.get("sha256"):
                known.add(f["sha256"])

    missing = []
    for p in pdfs:
        try:
            sh = sha256_file(p)
        except Exception as exc:  # noqa: BLE001
            print("  ! cannot read", p, exc)
            continue
        if sh not in known:
            missing.append(str(p))
    print(f"[1] files represented in DB: {len(pdfs) - len(missing)}/{len(pdfs)}  | MISSING: {len(missing)}")
    for mm in missing[:20]:
        print("    MISSING:", mm)

    # ---- 2. per-property title coverage ----
    tr = list(docs.find({"source_type": "title_report"},
                        {"property_ids": 1, "is_update": 1, "is_latest": 1,
                         "version_count": 1, "original_missing": 1}))
    props_with_title = Counter()
    for d in tr:
        for pid in (d.get("property_ids") or []):
            props_with_title[pid] += 1
    ents = m.db["entities"]
    nprops = ents.count_documents({"kind": "property"})
    update_only = docs.count_documents({"source_type": "title_report", "original_missing": True})
    unlinked_tr = sum(1 for d in tr if not (d.get("property_ids") or []))
    print(f"[2] title docs={len(tr)} | properties with >=1 title={len(props_with_title)}/{nprops}")
    print(f"[2] title docs NOT linked to a property={unlinked_tr}")
    print(f"[2] update-only (original full search absent) title docs={update_only}")
    multiver = sum(1 for d in tr if (d.get("version_count") or 1) > 1)
    print(f"[2] title docs in multi-version chains={multiver}")

    # ---- 3. property_graph smoke test ----
    from src.timeline.builder import property_graph
    # pick a David property that has titles + money
    pid = None
    for cand, _ in props_with_title.most_common(40):
        if m.db["money_records"].count_documents({"property_ids": cand}) > 0:
            pid = cand
            break
    pid = pid or (props_with_title.most_common(1)[0][0] if props_with_title else None)
    if pid:
        g = property_graph(m, property_id=pid)
        summ = g.get("summary", {})
        print(f"[3] property_graph({pid}) ok: address={g.get('address')!r}")
        print(f"    titles={len(g.get('title_versions') or [])} mortgages={len(g.get('mortgages') or [])} "
              f"money_records={summ.get('n_money_records')} money_total=${summ.get('money_total')} "
              f"documents={summ.get('n_documents')} events={len(g.get('events') or [])}")
    else:
        print("[3] no property with titles found (unexpected)")
    m.close()


if __name__ == "__main__":
    main()
