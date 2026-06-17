from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
d = m.db["documents"]

# discover which page-ish fields exist on a sample title report
sample = d.find_one({"source_type": "title_report"})
print("sample keys:", [k for k in sample.keys() if "page" in k.lower() or k in
      ("pages", "n_pages", "page_count", "num_pages", "ocr")])
for k in ("pages", "n_pages", "page_count", "num_pages"):
    if k in sample:
        v = sample[k]
        print(f"  field '{k}':", (len(v) if isinstance(v, list) else v))

T = ["title_report", "insurance", "equity_schedule", "service_agreement", "litigation_update"]


def doc_pages(doc):
    for k in ("page_count", "n_pages", "num_pages"):
        if isinstance(doc.get(k), int):
            return doc[k]
    if isinstance(doc.get("pages"), list):
        return len(doc["pages"])
    return None


grand = 0
missing = 0
per_type = {}
for st in T:
    tp = 0
    for doc in d.find({"source_type": st}):
        p = doc_pages(doc)
        if p is None:
            missing += 1
        else:
            tp += p
    per_type[st] = tp
    grand += tp
    print(f"{st}: {tp} pages")
print("TOTAL pages:", grand, "| docs with no page field:", missing)
m.close()
