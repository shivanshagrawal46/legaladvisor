"""Deep analysis: WHAT are the chunks with no entity link, and are we missing
real entity mentions (recall gap) or are they genuinely entity-free?"""
import re
from collections import Counter
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
ch = m.db["email_chunks_v2"]

total = ch.estimated_document_count()
linked = ch.count_documents({"entity_ids.0": {"$exists": True}})
unlinked_q = {"$or": [{"entity_ids": {"$exists": False}}, {"entity_ids": {"$size": 0}}]}
unlinked = ch.count_documents(unlinked_q)
print(f"total={total} linked={linked} ({100*linked/total:.1f}%) unlinked={unlinked} ({100*unlinked/total:.1f}%)")

print("\n=== unlinked by source_type ===")
c = Counter()
for d in ch.find(unlinked_q, {"source_type": 1, "doc_source_type": 1}):
    c[d.get("doc_source_type") or d.get("source_type") or "?"] += 1
for k, v in c.most_common():
    print(f"  {k}: {v}")

# Heuristic recall check: among unlinked, how many contain an address-like or
# LLC-like token we MIGHT be missing?
addr_re = re.compile(r"\b\d{1,5}\s+[A-Z][a-zA-Z]{2,}")
llc_re = re.compile(r"\b[A-Z0-9][A-Za-z0-9&.,'\- ]{2,40}\bLLC\b")
maybe_addr = maybe_llc = 0
samples = []
import itertools
for d in itertools.islice(ch.find(unlinked_q, {"body": 1, "text": 1, "source_type": 1}), 4000):
    t = (d.get("body") or d.get("text") or "")
    a = bool(addr_re.search(t))
    l = bool(llc_re.search(t))
    maybe_addr += int(a)
    maybe_llc += int(l)
    if (a or l) and len(samples) < 12:
        snip = re.sub(r"\s+", " ", t)[:160]
        samples.append((d.get("source_type"), a, l, snip))
print(f"\n=== recall probe on 4000 unlinked: addr-like={maybe_addr} llc-like={maybe_llc} ===")
for st, a, l, snip in samples:
    print(f"  [{st} addr={a} llc={l}] {snip}")
m.close()
