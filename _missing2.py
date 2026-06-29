import config.settings  # noqa
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name)
docs=m.db["documents"]
for needle in ["fort hill","ann dr","ann drive"]:
    print(f"--- '{needle}' ---")
    for d in docs.find({"source_type":"title_report","$or":[
        {"address_norm":{"$regex":needle,"$options":"i"}},
        {"property_address":{"$regex":needle,"$options":"i"}}]},
        {"property_address":1,"order_type":1,"is_update":1,"new_effective_date":1,"search_date":1,"custody.origin":1,"_id":1}):
        print("  ",d["_id"][:30], "|",d.get("property_address"),"|",d.get("order_type"),"| upd=",d.get("is_update"),"| neff=",d.get("new_effective_date"),"| origin=",(d.get("custody") or {}).get("origin"))
m.close()
