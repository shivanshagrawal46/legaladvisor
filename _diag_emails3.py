import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from bson import ObjectId

EIDS = ["6a0830d39a4a41f30e352dbe", "6a0830d39a4a41f30e352dbf",
        "6a083cd654c72cee2b8686ae"]


def try_swap(text):
    """Recover byte-swapped UTF-16 mojibake: re-encode as UTF-16-BE then
    decode as UTF-16-LE (or vice versa)."""
    out = []
    for enc, dec in [("utf-16-be", "utf-16-le"), ("utf-16-le", "utf-16-be")]:
        try:
            r = text.encode(enc, "ignore").decode(dec, "ignore")
            out.append((f"{enc}->{dec}", r))
        except Exception as e:
            out.append((f"{enc}->{dec}", f"ERR {e}"))
    return out


s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
emails = m.db["emails"]
for e in EIDS:
    em = emails.find_one({"_id": ObjectId(e)}) or {}
    print("=" * 70)
    print("email", e, "| subject:", repr((em.get("subject") or "")[:60]))
    for f in ("body_text", "body_text_raw", "body_html"):
        v = em.get(f) or ""
        print(f"  {f}: len={len(v)} head={repr(v[:80])}")
    # attempt recovery on body_text
    bt = em.get("body_text") or ""
    if bt:
        print("  --- recovery attempts on body_text ---")
        for label, r in try_swap(bt):
            print(f"    {label}: {repr(r[:120])}")
m.close()
