import config.settings  # noqa
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name)
docs=m.db["documents"]; ents=m.db["entities"]
tr=docs.count_documents({"source_type":"title_report"})
trp=docs.count_documents({"_id":{"$regex":"^doc_tr_"}})
pw=docs.count_documents({"_id":{"$regex":"^doc_pw_"}})
print("title_report docs:",tr," doc_tr_:",trp," doc_pw_:",pw)
props=ents.count_documents({"kind":"property"})
with_title=ents.count_documents({"kind":"property","has_title":True})
print("property entities:",props," with_title:",with_title)
# properties with title_doc_ids
import collections
have=0; cnt=collections.Counter()
for e in ents.find({"kind":"property"},{"title_doc_ids":1}):
    n=len(e.get("title_doc_ids") or [])
    if n>0: have+=1
    cnt[n]+=1
print("props with >=1 title doc:",have)
print("title-count distribution (titles->#props):",dict(sorted(cnt.items())))
m.close()
