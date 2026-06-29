import config.settings  # noqa
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from scripts.ingest_titles_full import norm_address, addr_core
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name)
ents=m.db["entities"]
print("kind=property count:",ents.count_documents({"kind":"property"}))
# find entities matching orange/brookfield/amesworth/20th
import re
for needle in ["orange","brookfield","amesworth","20th","ocean"]:
    print(f"\n--- '{needle}' ---")
    for e in ents.find({"kind":"property","$or":[
        {"canonical_address":{"$regex":needle,"$options":"i"}},
        {"address_variants":{"$regex":needle,"$options":"i"}}]},
        {"canonical_address":1,"address_variants":1}).limit(4):
        ca=e.get("canonical_address")
        print("  CA:",repr(ca),"-> core:",repr(addr_core(norm_address(ca or ""))))
        for v in (e.get("address_variants") or [])[:3]:
            print("     var:",repr(v),"-> core:",repr(addr_core(norm_address(v))))
m.close()
