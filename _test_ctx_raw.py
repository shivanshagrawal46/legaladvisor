import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from anthropic import Anthropic
from bson import ObjectId

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
emails = m.db["emails"]
ch = m.db["email_chunks_v2"]
eid = ObjectId("6a0830d39a4a41f30e352dbe")
em = emails.find_one({"_id": eid}) or {}
body = em.get("body_text") or ""
c = ch.find_one({"email_id": eid}, {"body": 1})
chunk_text = c.get("body") or ""

print("=== body_text first 600 chars ===")
print(repr(body[:600]))
print("=== chunk body ===")
print(repr(chunk_text[:400]))

cl = Anthropic(api_key=s.anthropic_api_key, timeout=60.0, max_retries=0)
r = cl.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=200,
    system="You write short, factual context summaries.",
    messages=[{"role": "user", "content":
        f"<document>\n{body[:60000]}\n</document>\n\nWrite a 100-150 token context "
        f"situating this chunk:\n<chunk>\n{chunk_text}\n</chunk>\nAnswer with only the context."}],
)
print("=== stop_reason:", r.stop_reason)
print("=== content blocks:", r.content)
print("=== usage:", r.usage)
m.close()
