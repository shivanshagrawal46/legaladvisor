import config.settings  # noqa
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name)
docs=m.db["documents"]; ch=m.db["email_chunks_v2"]; ents=m.db["entities"]; mr=m.db["money_records"]
print("=== DOCUMENTS ===")
print(" title_report:",docs.count_documents({"source_type":"title_report"}))
print("   missing_title origin:",docs.count_documents({"source_type":"title_report","custody.origin":"missing_title_reports"}))
# frontier re-audit on missing-title
bad=0
for d in docs.find({"source_type":"title_report","custody.origin":"missing_title_reports"},{"extraction_method":1}):
    em=d.get("extraction_method") or {}
    if isinstance(em,dict) and any(k not in ("claude_vision","openai_vision") for k in em): bad+=1
print("   missing_title NON-frontier docs:",bad)
print("=== CHUNKS ===")
print(" total chunks:",ch.estimated_document_count())
print(" title chunks:",ch.count_documents({"source_type":"title_report"}))
print("=== ENTITIES ===")
print(" property entities:",ents.count_documents({"kind":"property"}))
print("=== MONEY ===")
print(" money_records:",mr.count_documents({}))
print(" linked to property:",mr.count_documents({"property_ids.0":{"$exists":True}}))
print("=== GRAPH ===")
print(" relationships:",m.db["relationships"].count_documents({}))
print(" events:",m.db["events"].count_documents({}))
print(" dossiers:",m.db["property_dossier"].count_documents({}) if "property_dossier" in m.db.list_collection_names() else "n/a")
m.close()
