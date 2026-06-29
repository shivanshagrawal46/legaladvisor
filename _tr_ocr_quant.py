import config.settings  # noqa
from collections import Counter
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name)
docs=m.db["documents"]
ocr_pages=0; pdf_ocr_pages=0; docs_ocr=0; docs_pdfocr=0; docs_borndigital=0
docs_with_ocr=[]
for d in docs.find({"source_type":"title_report"},{"extraction_method":1,"custody":1}):
    em=d.get("extraction_method")
    if isinstance(em,str):
        if em in ("ocr","rapidocr"): docs_ocr+=1; docs_with_ocr.append(d["_id"])
        elif em in ("pdf_ocr",): docs_pdfocr+=1
        elif em in ("text_layer","pdf_text"): docs_borndigital+=1
        continue
    if isinstance(em,dict):
        o=em.get("ocr",0)+em.get("rapidocr",0)
        po=em.get("pdf_ocr",0)
        if o: docs_ocr+=1; docs_with_ocr.append(d["_id"]); ocr_pages+=o
        if po: docs_pdfocr+=1; pdf_ocr_pages+=po
print(f"title docs={docs.count_documents({'source_type':'title_report'})}")
print(f"docs with RapidOCR(ocr) pages={docs_ocr}  total RapidOCR pages={ocr_pages}")
print(f"docs with pdf_ocr={docs_pdfocr}  pdf_ocr pages={pdf_ocr_pages}")
print(f"docs born-digital(text_layer str)={docs_borndigital}")
print("sample ocr docs:",docs_with_ocr[:8])
m.close()
