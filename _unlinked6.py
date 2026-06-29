import config.settings  # noqa
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from scripts.ingest_titles_full import norm_address, addr_core
from scripts.ingest_insurance import build_prop_index
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name)
docs=m.db["documents"]; ents=m.db["entities"]
idx=build_prop_index(ents)
for d in docs.find({"source_type":"title_report","$or":[{"property_ids":{"$size":0}},{"property_ids":{"$exists":False}}]},
                   {"property_address":1,"address_norm":1,"custody.source_files":1,"vendor":1,"extracted_text":1}):
    sf=(d.get("custody") or {}).get("source_files") or []
    path=""
    if sf and isinstance(sf[0],dict): path=sf[0].get("source_path") or sf[0].get("path") or ""
    txt=(d.get("extracted_text") or "")[:300].replace(chr(10)," ")
    print("ID:",d["_id"][:30],"| addr_norm=",repr(d.get("address_norm")),"| path=",path.split("\\")[-1] if path else "")
    print("   text head:",txt[:160])
m.close()
