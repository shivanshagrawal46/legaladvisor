from config.settings import Settings
from src.db.mongo import MongoClientWrapper
import collections

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
ch = m.db["email_chunks_v2"]

# do chunks already carry corpus / privilege?
print("chunks with corpus:", ch.count_documents({"corpus": {"$exists": True}}))
print("chunks with privilege_status:", ch.count_documents({"privilege_status": {"$exists": True}}))
print("corpus values:", collections.Counter(c.get("corpus") for c in ch.find({}, {"corpus": 1}).limit(40000)))

# what distinguishes the two email corpora? inspect emails collection
for name in m.db.list_collection_names():
    if "email" in name.lower() and "chunk" not in name.lower():
        col = m.db[name]
        print(f"\ncollection '{name}': {col.estimated_document_count()} docs")
        s1 = col.find_one() or {}
        keys = [k for k in s1.keys() if k.lower() in
                ("corpus", "folder", "folder_path", "source", "matter", "privilege",
                 "privilege_status", "mailbox", "account", "from_email", "origin")]
        print("  candidate keys:", keys)
        for k in ("corpus", "folder_path", "source", "origin"):
            if k in s1:
                print(f"  {k} sample:", s1[k])
m.close()
