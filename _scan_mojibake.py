"""Scan the entire emails collection for byte-swapped UTF-16 mojibake
(CJK-looking body_text that is really HTML). Reports how widespread it is."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper


def cjk_ratio(t: str) -> float:
    if not t:
        return 0.0
    s = t[:400]
    cjk = sum(1 for c in s if 0x3000 <= ord(c) <= 0x9FFF)
    return cjk / len(s)


def recovers_to_html(t: str) -> bool:
    try:
        real = t[:200].encode("utf-16-le", "ignore").decode("cp1252", "ignore").lower()
        return "<html" in real or "<head" in real or "xmlns" in real or "<body" in real
    except Exception:
        return False


def main() -> int:
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    emails = m.db["emails"]
    total = emails.estimated_document_count()
    n = corrupt = recov = 0
    samples = []
    for em in emails.find({}, {"body_text": 1, "subject": 1}):
        n += 1
        bt = em.get("body_text") or ""
        if cjk_ratio(bt) > 0.3:
            corrupt += 1
            ok = recovers_to_html(bt)
            if ok:
                recov += 1
            if len(samples) < 10:
                samples.append((str(em["_id"]), (em.get("subject") or "")[:50], ok))
    print(f"emails scanned: {n}/{total}")
    print(f"mojibake (CJK>30%) bodies: {corrupt}")
    print(f"  recoverable to HTML:     {recov}")
    print("samples (id, subject, recoverable):")
    for x in samples:
        print("   ", x)
    m.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
