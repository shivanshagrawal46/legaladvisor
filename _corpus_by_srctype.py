import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
m.ping()
ch = m.db["email_chunks_v2"]
combo = Counter()
src = Counter()
for c in ch.find({}, {"source_type": 1, "corpus": 1}):
    st = c.get("source_type")
    src[st] += 1
    combo[(st, c.get("corpus") or "(none)")] += 1
print("source_type counts:", dict(src))
print("\n(source_type, corpus) distribution:")
for (st, corp), n in sorted(combo.items()):
    print(f"  {st:<14} {corp:<24} {n}")
m.close()
