"""Diagnose provenance of the duplicate title groups before any deletion."""
import config.settings  # noqa
from collections import Counter, defaultdict
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from scripts.ingest_titles_full import addr_core

s = Settings.load(); m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
docs = m.db["documents"]


def methods(d):
    em = d.get("extraction_method")
    if isinstance(em, dict):
        return em
    if isinstance(em, str) and em:
        return {em: int(d.get("page_count") or d.get("num_pages") or 1)}
    return {}


def acore(d):
    return addr_core(d.get("address_norm") or "")


def ident(d):
    if d.get("vendor") == "protitle":
        return ("PT", acore(d), d.get("order_number"), str(d.get("completed_date")), str(d.get("index_date")))
    return ("PW", acore(d), d.get("order_type"), str(d.get("search_date")),
            str(d.get("old_effective_date")), str(d.get("new_effective_date")))


proj = {"vendor": 1, "address_norm": 1, "order_number": 1, "completed_date": 1,
        "index_date": 1, "order_type": 1, "search_date": 1, "old_effective_date": 1,
        "new_effective_date": 1, "extraction_method": 1, "page_count": 1, "num_pages": 1,
        "chunked_at": 1, "property_ids": 1, "custody": 1, "corpus": 1, "source_type": 1}

# overall prefix / origin landscape
pref = Counter(); origin = Counter(); front = Counter()
mt86 = []
for d in docs.find({"source_type": "title_report"}, proj):
    p = "doc_p5" if d["_id"].startswith("doc_p5") else ("doc_tr" if d["_id"].startswith("doc_tr") else "other")
    pref[p] += 1
    o = (d.get("custody") or {}).get("origin") or "?"
    origin[o] += 1
    em = methods(d)
    fr = bool(em) and all(k in ("claude_vision", "openai_vision") for k in em)
    front[(p, fr)] += 1
    if o == "missing_title_reports":
        mt86.append(d["_id"][:7])
print("PREFIX:", dict(pref))
print("ORIGIN:", dict(origin))
print("FRONTIER by (prefix,is_frontier):", dict(front))
print("missing_title_reports prefixes:", Counter(mt86))

# duplicate groups detail
groups = defaultdict(list)
for d in docs.find({"source_type": "title_report"}, proj):
    groups[ident(d)].append(d)
dups = {k: v for k, v in groups.items() if len(v) > 1}
print(f"\nDUP groups={len(dups)}")
combo = Counter()
for k, v in dups.items():
    prefixes = tuple(sorted({("p5" if x["_id"].startswith("doc_p5") else "tr") for x in v}))
    origins = tuple(sorted({(x.get("custody") or {}).get("origin") or "?" for x in v}))
    combo[(prefixes, origins)] += 1
for c, n in combo.most_common():
    print(f"  {n:3d} groups  prefixes={c[0]} origins={c[1]}")

# how many of MY missing_title docs are in a dup group?
my_in_dup = 0
for k, v in dups.items():
    for x in v:
        if (x.get("custody") or {}).get("origin") == "missing_title_reports":
            my_in_dup += 1
print(f"\nMY missing-title docs inside a duplicate group: {my_in_dup}")
m.close()
