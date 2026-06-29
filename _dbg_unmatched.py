import config.settings  # noqa
import re
from collections import Counter, defaultdict
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from scripts.ingest_titles_full import norm_address, addr_core
from scripts.ingest_insurance import build_prop_index
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name)
mr,ents=m.db["money_records"],m.db["entities"]
idx=build_prop_index(ents)
core_raw=defaultdict(Counter); core_n=Counter()
addrish=re.compile(r"^\d+\s+\S")
for r in mr.find({"property_ids":{"$size":0}},{"property":1,"memo":1}):
    txt=(r.get("property") or "").strip()
    if not txt:
        memo=(r.get("memo") or "")
        txt=re.split(r"\s*[-–|]\s*|\ba/c\b|#",memo)[0].strip()
    if not txt: continue
    ac=addr_core(norm_address(txt))
    if not ac or ac in idx: continue
    core_n[ac]+=1; core_raw[ac][txt]+=1
real=[(c,n) for c,n in core_n.most_common() if addrish.match(c)]
noise=[(c,n) for c,n in core_n.most_common() if not addrish.match(c)]
print("REAL address cores (would create entities):",len(real),"covering",sum(n for _,n in real),"records")
for c,n in real[:40]:
    print(f"  {n:4d}  {c:22s}  e.g. {core_raw[c].most_common(1)[0][0]!r}")
print("\nNOISE cores (left unlinked):",len(noise),"covering",sum(n for _,n in noise),"records")
for c,n in noise[:15]:
    print(f"  {n:4d}  {c!r}  e.g. {core_raw[c].most_common(1)[0][0]!r}")
m.close()
