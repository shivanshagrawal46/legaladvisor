import config.settings  # noqa
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name)
docs=m.db["documents"]; ch=m.db["email_chunks_v2"]
tr=docs.count_documents({"source_type":"title_report"})
trc=docs.count_documents({"source_type":"title_report","chunked_at":{"$exists":True}})
pend=docs.count_documents({"source_type":"title_report","chunked_at":{"$exists":False}})
trchunks=ch.count_documents({"source_type":"title_report"})
print(f"title docs={tr} chunked={trc} pending={pend}")
print(f"title chunks in email_chunks_v2={trchunks}")
# missing-title specifically
mt=docs.count_documents({"source_type":"title_report","custody.origin":"missing_title_reports"})
mtc=docs.count_documents({"source_type":"title_report","custody.origin":"missing_title_reports","chunked_at":{"$exists":True}})
print(f"missing-title docs={mt} chunked={mtc}")
m.close()
