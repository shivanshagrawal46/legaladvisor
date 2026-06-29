import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

CATS = ["cheque", "wire_confirmation", "settlement_sheet", "bill_invoice", "closing_document"]
s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
docs = m.db["documents"]

print("money-bearing doc_categories (phase5):")
total = 0
for c in CATS:
    n = docs.count_documents({"_id": {"$regex": "^doc_p5_"}, "doc_category": c})
    total += n
    print(f"  {c:20s}: {n}")
print(f"  {'TOTAL':20s}: {total}")

already = docs.count_documents({"_id": {"$regex": "^doc_p5_"}, "doc_category": {"$in": CATS},
                                "money_extracted_at": {"$exists": True}})
print(f"already extracted        : {already}")
print(f"pending                  : {total - already}")
m.close()
