import config.settings  # noqa
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name); db=m.db
ch=db["email_chunks_v2"]
done=[l.strip() for l in open("_fraud_borndigital_done_sha.txt",encoding="utf-8") if l.strip()]
done=set(done)
# a freshly re-chunked sha (in done set)
import itertools
fresh=ch.find_one({"sha256":{"$in":list(itertools.islice(done,50))},"source_type":"attachment"})
# an old attachment chunk NOT in the done set
old=ch.find_one({"source_type":"attachment","sha256":{"$nin":list(done)}})
def show(label,d):
    if not d: print(label,"-> none"); return
    print(f"\n{label}: keys={sorted(d.keys())}")
    for k in ("corpus","entity_ids","entities","authority","authority_score","evidentiary_class","privilege_status","embedding"):
        v=d.get(k)
        if k=="embedding": v=(f"<{len(v)} dims>" if isinstance(v,list) else v)
        print(f"    {k}: {v if k not in ('entity_ids','entities') else (len(v) if isinstance(v,list) else v)}")
show("FRESH (rechunked)",fresh)
show("OLD (untouched)",old)
m.close()
