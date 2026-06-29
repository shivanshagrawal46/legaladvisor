import config.settings  # noqa
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name)
docs=m.db["documents"]
q={"source_type":"title_report","custody.origin":"missing_title_reports"}
n=docs.count_documents(q)
auth=docs.count_documents({**q,"authority_score":{"$exists":True}})
pid=docs.count_documents({**q,"property_ids.0":{"$exists":True}})
upd=docs.count_documents({**q,"is_update":True})
chk=docs.count_documents({**q,"chunked_at":{"$exists":True}})
print(f"missing-title docs={n} | has authority_score={auth} | has property_ids={pid} | is_update flagged={upd} | already chunked={chk}")
d=docs.find_one(q,{"authority_score":1,"property_ids":1,"is_update":1,"order_number":1,"vendor":1,"property_address":1,"completed_date":1})
print("sample:",{k:d.get(k) for k in ("vendor","property_address","order_number","authority_score","property_ids","is_update","completed_date")})
m.close()
