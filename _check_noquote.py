import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.cleaner import clean_email_body, html_to_text
from bson import ObjectId

EIDS = ["6a082dc49a4a41f30e351ead", "6a082db39a4a41f30e351e4a",
        "6a0830d39a4a41f30e352dbe", "6a0830d39a4a41f30e352dbf",
        "6a0830d39a4a41f30e352dc1", "6a0837a254c72cee2b866b4e",
        "6a0837c654c72cee2b866c43", "6a083cd654c72cee2b8686ae"]

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
emails = m.db["emails"]
for e in EIDS:
    em = emails.find_one({"_id": ObjectId(e)}, {"body_html": 1, "subject": 1})
    raw = html_to_text(em.get("body_html") or "")
    keep = clean_email_body(raw, strip_quotes=False)
    strip = clean_email_body(raw, strip_quotes=True)
    print(f"{e} | {(em.get('subject') or '')[:40]!r}")
    print(f"   raw={len(raw)}  keep_quotes={len(keep)}  strip_quotes={len(strip)}")
    print(f"   keep head: {keep[:140]!r}")
m.close()
