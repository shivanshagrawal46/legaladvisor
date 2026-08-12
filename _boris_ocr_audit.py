"""Audit the newest Boris attachments_v2 rows: which engine OCR'd each page?

The requirement is Claude Vision only. Anything whose pages came back as
rapidocr / text_layer / empty needs to be re-done, so list those explicitly.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

LABEL = "__....Boris Lawsuit"
shas = [ln.strip() for ln in Path("_boris_shas.txt").read_text(encoding="utf-8").splitlines() if ln.strip()]

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
db = m.db
av2, ch = db["attachments_v2"], db["email_chunks_v2"]

# The ones with no vector yet == the ones just OCR'd (or still missing).
vec = set(ch.distinct("sha256", {"source_type": "attachment", "sha256": {"$in": shas}}))
fresh = [x for x in shas if x not in vec]

print(f"Boris unique sha256            : {len(shas):,}")
print(f"  already vectorised           : {len(vec):,}")
print(f"  NOT yet vectorised (inspect) : {len(fresh):,}")
print()

rows = list(av2.find({"sha256": {"$in": fresh}}))
print(f"attachments_v2 rows for those  : {len(rows):,}")
print("=" * 78)

overall = Counter()
bad = []
seen = set()
for r in rows:
    sha = r.get("sha256")
    if sha in seen:
        continue
    seen.add(sha)
    ex = r.get("extraction") or {}
    pages = ex.get("pages") or []
    pm = Counter(p.get("method") for p in pages)
    overall.update(pm)
    chars = ex.get("char_count") or len(r.get("extracted_text") or "")
    skipped = r.get("skipped")
    non_claude = {k: v for k, v in pm.items() if k != "claude_vision"}
    flag = ""
    if skipped:
        flag = f"SKIPPED({skipped})"
    elif not pages:
        flag = "NO PAGES"
    elif non_claude:
        flag = f"NON-CLAUDE {dict(non_claude)}"
    if flag:
        bad.append((sha, r.get("filename"), flag))
    print(f"  {(r.get('filename') or '')[:52]:52s} pages={len(pages):>3} "
          f"chars={chars:>7,} {dict(pm)} {flag}")

print("=" * 78)
print(f"page-method totals across these: {dict(overall)}")
print()
if bad:
    print(f"!! {len(bad)} attachment(s) NOT pure Claude Vision:")
    for sha, fn, flag in bad:
        print(f"   {sha[:16]}…  {(fn or '')[:46]:46s} {flag}")
    Path("_boris_redo_shas.txt").write_text(
        "\n".join(x[0] for x in bad) + "\n", encoding="utf-8")
    print(f"\n   wrote {len(bad)} sha256 -> _boris_redo_shas.txt")
else:
    print("All inspected attachments are pure claude_vision.")

m.close()
