import config.settings  # noqa
from collections import Counter
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name); db=m.db
ch=db["email_chunks_v2"]
done=set(l.strip() for l in open("_fraud_borndigital_done_sha.txt",encoding="utf-8") if l.strip())
print("done sha:",len(done))
# surviving (old, not yet re-chunked) chunks for these sha
cur=ch.find({"sha256":{"$in":list(done)},"source_type":"attachment"},
    {"corpus":1,"privilege_status":1,"evidentiary_class":1,"from_email":1,"entity_backfill_at":1,"doc_authority_score":1})
corp=Counter(); priv=Counter(); ipellc=0; tot=0; haveauth=0; haveent=0
for c in cur:
    tot+=1
    corp[c.get("corpus") or "(none)"]+=1
    priv[c.get("privilege_status") or "(none)"]+=1
    fe=(c.get("from_email") or "").lower()
    if fe.endswith("@ipellc.net"): ipellc+=1
    if c.get("doc_authority_score") is not None: haveauth+=1
    if c.get("entity_backfill_at") is not None: haveent+=1
print("surviving chunks for these sha:",tot)
print("corpus:",dict(corp))
print("privilege:",dict(priv))
print("from ipellc.net:",ipellc,"| have authority:",haveauth,"| have entity_backfill:",haveent)
m.close()
