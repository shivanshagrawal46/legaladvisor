import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.rag.v2.contextual_summary import ContextualSummarizer
from bson import ObjectId

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
emails = m.db["emails"]
ch = m.db["email_chunks_v2"]

eid = ObjectId("6a0830d39a4a41f30e352dbe")
em = emails.find_one({"_id": eid}) or {}
body = em.get("body_text") or em.get("body_text_raw") or ""
print("email body_text len:", len(body))
# a real chunk body for this email
c = ch.find_one({"email_id": eid}, {"body": 1, "text": 1})
chunk_text = (c.get("body") or c.get("text") or "")
print("chunk len:", len(chunk_text))

summ = ContextualSummarizer(api_key=s.anthropic_api_key, model="claude-sonnet-4-6")
# call the RAW cached path so the exception is NOT swallowed
try:
    out = summ._call_cached(body, chunk_text)
    print("CACHED OK:", repr(out[:200]))
except Exception as e:
    print("CACHED ERROR:", type(e).__name__, "::", str(e)[:400])

try:
    out = summ._call_uncached(body, chunk_text)
    print("UNCACHED OK:", repr(out[:200]))
except Exception as e:
    print("UNCACHED ERROR:", type(e).__name__, "::", str(e)[:400])
m.close()
