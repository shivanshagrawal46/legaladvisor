import collections
import random
import re

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

IMG = {"jpg", "jpeg", "png", "gif", "bmp", "tif", "tiff", "webp", "emz", "emf", "wmf"}
s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
db = m.db
tiny, big = [], []
for a in db["attachments_v2"].find({}, {"extension": 1, "filename": 1,
                                        "size_bytes": 1, "extracted_text": 1}):
    fn = a.get("filename", "") or ""
    ext = (a.get("extension") or (fn.rsplit(".", 1)[-1] if "." in fn else "")).lower().lstrip(".")
    if ext not in IMG:
        continue
    b = a.get("size_bytes") or 0
    (tiny if b < 15000 else big).append(a)

nm = collections.Counter()
for a in tiny:
    fn = (a.get("filename", "") or "").lower()
    nm[re.sub(r"\d+", "#", fn)] += 1
print("TINY (<15KB) count:", len(tiny))
print("top tiny filename patterns:")
for k, v in nm.most_common(15):
    print(f"   {v:4d}  {k}")
print("--- sample tiny OCR text (<=60 chars) ---")
for a in random.sample(tiny, min(10, len(tiny))):
    t = " ".join((a.get("extracted_text") or "").split())[:60]
    print(f"   {a.get('size_bytes'):6d}B  {(a.get('filename','') or '')[:32]:32s} | {t}")
print("--- sample BIG (>=200KB) filenames ---")
big.sort(key=lambda x: -(x.get("size_bytes") or 0))
for a in big[:8]:
    print(f"   {a.get('size_bytes'):8d}B  {(a.get('filename','') or '')[:50]}")
m.close()
