"""Airtight staleness proof: split each chunk's text into the GENERATED
contextual-summary portion vs the OCR BODY portion, and confirm the BODY is
present in the current (new) attachments_v2 extracted_text."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import Settings
from src.db.mongo import MongoClientWrapper


def norm(t: str) -> str:
    return " ".join((t or "").split()).lower()


def main() -> int:
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    m.ping()
    ch = m.db["email_chunks_v2"]
    v2 = m.db["attachments_v2"]

    # inspect the raw structure of one flagged chunk
    sample = ch.find_one({"sha256": {"$regex": "^b29ffd2198"},
                          "source_type": "attachment", "chunk_index": 188})
    if sample:
        print("FIELDS on chunk:", sorted(sample.keys()))
        print("\ncontextual_summary field:\n  ",
              repr((sample.get("contextual_summary") or "")[:200]))
        print("\ntext field head:\n  ", repr((sample.get("text") or "")[:200]))
        print("\ntext field tail:\n  ", repr((sample.get("text") or "")[-200:]))

    shas = [ln.strip() for ln in Path("_fraud_mixed_done_sha.txt").read_text(
        encoding="utf-8").splitlines() if ln.strip()]

    # For each chunk, take the LAST 80 chars of the text (deep in the OCR body,
    # past any summary), and confirm it's in the current OCR text.
    print("\n" + "=" * 60)
    not_found = 0
    checked = 0
    for sha in shas:
        a = v2.find_one({"sha256": sha}, {"extracted_text": 1})
        cur = norm((a or {}).get("extracted_text") or "")
        for c in ch.find({"sha256": sha, "source_type": "attachment"},
                         {"text": 1, "chunk_index": 1}):
            body = norm(c.get("text") or "")
            if len(body) < 120:
                continue
            checked += 1
            tail = body[-80:]
            if tail not in cur:
                not_found += 1
                if not_found <= 8:
                    print(f"  NOTFOUND sha={sha[:10]} idx={c.get('chunk_index')} "
                          f"tail={tail!r}")
    print("=" * 60)
    print(f"checked={checked}  tail_not_in_new_ocr={not_found}")
    print("(tail = end of chunk = deep in OCR body, past the summary prefix)")
    m.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
