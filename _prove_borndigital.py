"""Prove the 536 targets were born-digital (text_layer), NOT vision OCR.
Shows, for legal-corpus attachments that still carry a text_layer page
(i.e. not yet reprocessed by the running job), the exact page-method mix,
their extraction.method, extracted_via tag, and a text snippet."""
from __future__ import annotations
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import Settings
from src.db.mongo import MongoClientWrapper


def main() -> int:
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    m.ping()
    v2 = m.db["attachments_v2"]
    ch = m.db["email_chunks_v2"]

    # legal-corpus sha set
    legal_sha = set()
    for c in ch.find({"source_type": "attachment", "corpus": "legal_correspondence"},
                     {"sha256": 1}):
        legal_sha.add(c.get("sha256"))

    # Among legal sha: split by current extraction state
    still_textlayer = 0
    now_vision = 0
    via_counter = Counter()
    method_when_tl = Counter()
    samples = []
    seen = set()
    for a in v2.find({"sha256": {"$in": list(legal_sha)}},
                     {"sha256": 1, "filename": 1, "extracted_via": 1,
                      "extraction.method": 1, "extraction.pages.method": 1,
                      "extracted_text": 1}):
        sha = a.get("sha256")
        if sha in seen:
            continue
        seen.add(sha)
        pages = (a.get("extraction") or {}).get("pages") or []
        pm = Counter(p.get("method") for p in pages)
        via_counter[a.get("extracted_via")] += 1
        if "text_layer" in pm:
            still_textlayer += 1
            method_when_tl[(a.get("extraction") or {}).get("method")] += 1
            if len(samples) < 12:
                txt = (a.get("extracted_text") or "")[:160].replace("\n", " ")
                samples.append((a.get("filename"), dict(pm),
                                a.get("extracted_via"), txt))
        elif any(v in pm for v in ("claude_vision", "openai_vision", "image_vision")):
            now_vision += 1

    print(f"legal-corpus unique sha examined: {len(seen)}")
    print(f"  still on text_layer (born-digital, NOT yet vision): {still_textlayer}")
    print(f"  now vision (claude/openai/image): {now_vision}")
    print(f"  extracted_via tags: {dict(via_counter)}")
    print(f"  extraction.method of the text_layer docs: {dict(method_when_tl)}")
    print("\nSAMPLES still on text_layer (proof they were born-digital, not vision):")
    for fn, pm, via, txt in samples:
        print(f"\n  file={str(fn)[:55]!r}")
        print(f"    page_methods={pm}  extracted_via={via}")
        print(f"    text[:160]={txt!r}")
    m.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
