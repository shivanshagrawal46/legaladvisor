import config.settings  # noqa
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name)
docs=m.db["documents"]
T=["title_report","insurance","equity_schedule","service_agreement","litigation_update"]
pend=docs.count_documents({"source_type":{"$in":T},"chunked_at":{"$exists":False}})
tr_pend=docs.count_documents({"source_type":"title_report","chunked_at":{"$exists":False}})
print("pending chunk (all target types):",pend,"| title_report pending:",tr_pend)
m.close()
