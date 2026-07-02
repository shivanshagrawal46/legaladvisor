import config.settings  # noqa
from collections import Counter
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name); db=m.db
em=db["emails"]; av=db["attachments_v2"]
fraud_ids=set(e["_id"] for e in em.find({"corpus":"fraud_communications"},{"_id":1}))
print("fraud emails:",len(fraud_ids))
# attachments belonging to fraud emails
method_ctr=Counter(); 
pdf_text_sha=set(); pdf_text_pages=0; pdf_text_rows=0
ext_ctr=Counter()
for a in av.find({}, {"email_id":1,"extraction.method":1,"extraction.page_count":1,"sha256":1,"extension":1,"extraction.pages":1}):
    if a.get("email_id") not in fraud_ids: continue
    meth=(a.get("extraction") or {}).get("method")
    method_ctr[meth]+=1
    if meth=="pdf_text":
        pdf_text_rows+=1
        pdf_text_sha.add(a.get("sha256"))
        pdf_text_pages+=int((a.get("extraction") or {}).get("page_count") or 0)
        ext_ctr[(a.get("extension") or "").lower()]+=1
print("fraud attachment methods:",dict(method_ctr))
print("\nPDF_TEXT rows:",pdf_text_rows,"| unique sha:",len(pdf_text_sha),"| total pages:",pdf_text_pages)
print("by extension:",dict(ext_ctr))
m.close()
