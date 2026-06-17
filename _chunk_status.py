from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
d = m.db["documents"]
ch = m.db["email_chunks_v2"]
T = ["title_report", "insurance", "equity_schedule", "service_agreement", "litigation_update"]
tot = d.count_documents({"source_type": {"$in": T}})
done = d.count_documents({"source_type": {"$in": T}, "chunked_at": {"$exists": True}})
print("chunked", done, "of", tot)
for st in T:
    a = d.count_documents({"source_type": st, "chunked_at": {"$exists": True}})
    b = d.count_documents({"source_type": st})
    print(f"  {st}: {a}/{b}")
print("phase3 chunks in email_chunks_v2:",
      ch.count_documents({"source_type": {"$in": T}}))
m.close()
