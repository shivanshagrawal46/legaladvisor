"""Pre-flight before retiring duplicate doc_p5 title copies: confirm nothing
critical references them, and break down non-frontier OCR methods."""
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
        return {em: 1}
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
        "new_effective_date": 1, "extraction_method": 1, "chunked_at": 1, "custody": 1}

groups = defaultdict(list)
for d in docs.find({"source_type": "title_report"}, proj):
    groups[ident(d)].append(d)
dups = {k: v for k, v in groups.items() if len(v) > 1}

# the docs that WOULD be retired = doc_p5 copies in each dup group (survivor=non-p5)
retire_ids = []
for k, v in dups.items():
    ac, tail = k[1], [x for x in k[2:] if x not in ("", "None", None)]
    if not ac or not tail:
        continue  # weak group skipped by resolver
    p5 = [x for x in v if x["_id"].startswith("doc_p5")]
    non = [x for x in v if not x["_id"].startswith("doc_p5")]
    if non and p5:
        retire_ids.extend(x["_id"] for x in p5)
print(f"would-retire doc_p5 ids: {len(retire_ids)}")

# referential safety
mr = m.db["money_records"].count_documents({"document_id": {"$in": retire_ids}})
rels_src = m.db["relationships"].count_documents({"src": {"$in": retire_ids}})
rels_dst = m.db["relationships"].count_documents({"dst": {"$in": retire_ids}})
ev = m.db["events"].count_documents({"document_id": {"$in": retire_ids}}) if "events" in m.db.list_collection_names() else 0
print(f"money_records referencing them: {mr}")
print(f"relationships src/dst: {rels_src}/{rels_dst}")
print(f"events referencing them: {ev}")

# non-frontier method breakdown across ALL title docs
nf = Counter()
for d in docs.find({"source_type": "title_report"}, {"extraction_method": 1}):
    for kk in methods(d):
        if kk not in ("claude_vision", "openai_vision"):
            nf[kk] += 1
print(f"\nnon-frontier method occurrences across title docs: {dict(nf)}")

# survivors that are non-frontier: split text_layer (born-digital, fine) vs ocr (rapidocr, bad)
surv_methods = Counter()
for k, v in dups.items():
    non = [x for x in v if not x["_id"].startswith("doc_p5")]
    if non:
        d = non[0]
        em = methods(d)
        if not (em and all(kk in ("claude_vision", "openai_vision") for kk in em)):
            for kk in em:
                surv_methods[kk] += 1
print(f"non-frontier SURVIVOR methods: {dict(surv_methods)}")
m.close()
