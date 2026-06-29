"""For the legacy RapidOCR docs not matched by basename, map their address-core
to F: files and report multiplicity, so we only auto-swap UNAMBIGUOUS matches."""
import re
from pathlib import Path
from collections import defaultdict

import config.settings  # noqa
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from scripts.ingest_titles_full import norm_address, addr_core

ROOT = Path(r"F:\Title reports")


def methods(d):
    em = d.get("extraction_method")
    if isinstance(em, dict):
        return em
    if isinstance(em, str) and em:
        return {em: 1}
    return {}


def has_rapid(d):
    return any(k in ("ocr", "rapidocr") for k in methods(d))


def fname_to_addr(name: str) -> str:
    a = name
    a = re.sub(r"\.pdf$", "", a, flags=re.I)
    a = re.sub(r"_(update\s*search|search\s*package|full\s*search).*$", "", a, flags=re.I)
    a = a.split(",")[0]  # drop city/state
    a = re.sub(r"\b\d{5}\b", "", a)
    a = a.strip(" '\"-")
    return a


def basename_index():
    idx = set()
    for p in ROOT.rglob("*.pdf"):
        idx.add(p.name.lower())
    return idx


def core_index():
    idx = defaultdict(list)
    for p in ROOT.rglob("*.pdf"):
        core = addr_core(norm_address(fname_to_addr(p.name)))
        if core:
            idx[core].append(p)
    return idx


def main():
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    docs = m.db["documents"]
    proj = {"extraction_method": 1, "page_count": 1, "custody": 1, "property_address": 1}
    bidx = basename_index()
    cidx = core_index()

    targets = []
    for d in docs.find({"source_type": "title_report"}, proj):
        if not has_rapid(d):
            continue
        c = d.get("custody") or {}
        names = []
        for f in (c.get("source_files") or []):
            if isinstance(f, dict):
                names.append((f.get("name") or Path((f.get("source_path") or "")).name))
        # matched by basename already?
        if any((n or "").lower() in bidx for n in names if n):
            continue
        targets.append(d)

    print(f"docs NOT matched by basename: {len(targets)}")
    uniq = ambig = none = 0
    for d in targets:
        core = addr_core(norm_address(fname_to_addr((d.get("property_address") or ""))))
        hits = cidx.get(core, [])
        # de-dup identical filenames across years
        rels = sorted({str(p.relative_to(ROOT)) for p in hits})
        tag = "UNIQUE" if len(rels) == 1 else ("AMBIG" if len(rels) > 1 else "NONE")
        if tag == "UNIQUE":
            uniq += 1
        elif tag == "AMBIG":
            ambig += 1
        else:
            none += 1
        print(f"  [{tag}] {d['_id'][:26]} core={core!r} addr={d.get('property_address')!r}")
        for r in rels[:6]:
            print(f"        -> {r}")
    print(f"\nUNIQUE={uniq}  AMBIG={ambig}  NONE={none}")
    m.close()


if __name__ == "__main__":
    main()
