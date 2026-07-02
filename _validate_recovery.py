import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.cleaner import clean_email_body, html_to_text
from bson import ObjectId


def recover_html(mojibake: str) -> str:
    # CJK codepoints are really UTF-16-LE byte pairs of cp1252/latin-1 text.
    raw = mojibake.encode("utf-16-le", "ignore")
    for enc in ("cp1252", "latin-1", "utf-8"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("latin-1", "ignore")


s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
emails = m.db["emails"]
em = emails.find_one({"_id": ObjectId("6a0830d39a4a41f30e352dbe")})
html = em.get("body_html") or em.get("body_text_raw") or ""
rec = recover_html(html)
print("=== recovered HTML head ===")
print(rec[:400])
txt = html_to_text(rec)
cleaned = clean_email_body(txt, strip_quotes=True)
print("\n=== html_to_text -> clean_email_body (first 1200) ===")
print(cleaned[:1200])
print("\nlen recovered html:", len(rec), "| clean text len:", len(cleaned))
m.close()
