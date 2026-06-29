import config.settings  # noqa
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from scripts.ingest_titles_full import norm_address, addr_core
from scripts.ingest_insurance import build_prop_index
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name)
docs=m.db["documents"]; ents=m.db["entities"]
idx=build_prop_index(ents)
trials={"doc_p5_98b0cd3852ad85ea":"444 Route 111 Smithtown NY",
        "doc_p5_1e2be65cf56dd1ea":"2012 21st Avenue South",
        "doc_p5_0b126de9dc2fd1ea":"2012 21st Avenue South"}
for did,addr in trials.items():
    ac=addr_core(norm_address(addr))
    hit=idx.get(ac)
    print(did[:24],"| addr=",addr,"| core=",repr(ac),"| -> entity:",hit)
    if hit:
        docs.update_one({"_id":did},{"$set":{"property_ids":[hit],"address_norm":norm_address(addr)}})
        print("   LINKED ->",hit)
m.close()
