import config.settings  # noqa
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from collections import Counter
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name)
mr=m.db["money_records"]; docs=m.db["documents"]
total=mr.count_documents({})
grounded=mr.count_documents({"source_quote":{"$exists":True,"$ne":""}})
has_amt=mr.count_documents({"amount":{"$gt":0}})
has_prop=mr.count_documents({"property_ids.0":{"$exists":True}})
has_payer=mr.count_documents({"payer":{"$exists":True,"$ne":""}})
has_payee=mr.count_documents({"payee":{"$exists":True,"$ne":""}})
has_date=mr.count_documents({"date":{"$exists":True,"$ne":""}})
recon=mr.count_documents({"reconciled_across_docs.0":{"$exists":True}})
inst=Counter(d.get("instrument","?") for d in mr.find({},{"instrument":1}))
# money-bearing docs coverage
mb=docs.count_documents({"money_extracted_at":{"$exists":True}})
print(f"money_records total: {total}")
print(f"  grounded (source_quote): {grounded} ({100*grounded//max(total,1)}%)")
print(f"  amount>0: {has_amt} | date: {has_date} | payer: {has_payer} | payee: {has_payee}")
print(f"  linked to property: {has_prop} ({100*has_prop//max(total,1)}%)")
print(f"  reconciled across docs: {recon}")
print(f"  by instrument: {dict(inst)}")
print(f"docs with money_extracted_at stamp: {mb}")
m.close()
