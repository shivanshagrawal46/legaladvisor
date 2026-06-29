"""Post-run audit of the force-vision OCR pass.

Scopes to the attachments OCR'd in THIS run (extracted_at >= cutoff) and reports:
  1. Doc-level method=="skipped" files (the 58) — filename / size / reason.
  2. Every page where a frontier model did NOT OCR it (i.e. not claude_vision
     and not openai_vision) — these are pages Claude rejected and GPT did not
     transcribe (fell to RapidOCR / failed / empty). De-duplicated by sha256.

Read-only. Writes two CSVs for follow-up.
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import Settings
from src.db.mongo import MongoClientWrapper

# Run started 2026-06-25T10:47Z; use a safe cutoff just before it.
CUTOFF = datetime(2026, 6, 25, 10, 40, tzinfo=timezone.utc)

VISION_OK = {"claude_vision", "openai_vision"}
# Page methods that mean "a frontier vision model did NOT do this page".
# text_layer shouldn't appear (force-vision), but list it as "not vision" too.


def main() -> int:
    s = Settings.load()
    mongo = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    try:
        mongo.ping()
        v2 = mongo.db["attachments_v2"]

        cur = v2.find(
            {"extracted_at": {"$gte": CUTOFF}},
            {
                "sha256": 1, "filename": 1, "size_bytes": 1,
                "extraction.method": 1, "extraction.skipped_reason": 1,
                "extraction.page_count": 1, "extraction.char_count": 1,
                "extraction.pages.page_no": 1,
                "extraction.pages.method": 1,
                "extraction.pages.char_count": 1,
            },
        )

        seen_sha = set()
        skipped_docs = []          # doc-level method == skipped
        bad_pages = []             # (sha, filename, page_no, method, chars)
        per_method = defaultdict(int)
        total_unique = 0
        total_pages = 0

        for d in cur:
            sha = d.get("sha256")
            if sha in seen_sha:
                continue
            seen_sha.add(sha)
            total_unique += 1
            ext = d.get("extraction", {}) or {}
            method = ext.get("method")
            fn = d.get("filename")
            size = d.get("size_bytes")

            if method == "skipped":
                skipped_docs.append({
                    "sha256": sha, "filename": fn, "size_bytes": size,
                    "skipped_reason": ext.get("skipped_reason"),
                    "char_count": ext.get("char_count"),
                })

            for p in ext.get("pages", []) or []:
                total_pages += 1
                pm = p.get("method")
                per_method[pm] += 1
                if pm not in VISION_OK:
                    bad_pages.append({
                        "sha256": sha, "filename": fn, "page_no": p.get("page_no"),
                        "method": pm, "char_count": p.get("char_count"),
                    })

        print(f"\n=== FORCE-VISION RUN AUDIT (extracted_at >= {CUTOFF.isoformat()}) ===")
        print(f"Unique attachments in run:   {total_unique}")
        print(f"Total pages across run:      {total_pages}")
        print(f"\nPage method breakdown:")
        for m, n in sorted(per_method.items(), key=lambda x: -x[1]):
            flag = "" if m in VISION_OK else "   <-- NOT a frontier vision model"
            print(f"   {m:<22} {n:>6}{flag}")

        print(f"\n--- Doc-level method=='skipped' (couldn't parse): {len(skipped_docs)} ---")
        for r in skipped_docs:
            print(f"   {(r['filename'] or '')[:60]:<60} "
                  f"{(r['size_bytes'] or 0):>10}B  reason={r['skipped_reason']}  "
                  f"chars={r['char_count']}")

        # pages not OCR'd by a frontier model, grouped by sha
        by_sha = defaultdict(list)
        for bp in bad_pages:
            by_sha[bp["sha256"]].append(bp)
        print(f"\n--- Pages NOT OCR'd by Claude/GPT: {len(bad_pages)} "
              f"across {len(by_sha)} attachment(s) ---")
        for sha, pages in by_sha.items():
            fn = pages[0]["filename"]
            empties = sum(1 for p in pages if not p.get("char_count"))
            print(f"   {(fn or '')[:55]:<55} sha={sha[:12]} "
                  f"pages={len(pages)} empty={empties} "
                  f"methods={sorted(set(p['method'] for p in pages))}")

        out_dir = Path(__file__).resolve().parent
        with open(out_dir / "_ocr_skipped_docs.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["sha256", "filename", "size_bytes",
                                               "skipped_reason", "char_count"])
            w.writeheader()
            w.writerows(skipped_docs)
        with open(out_dir / "_ocr_bad_pages.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["sha256", "filename", "page_no",
                                               "method", "char_count"])
            w.writeheader()
            w.writerows(bad_pages)
        print(f"\nWrote _ocr_skipped_docs.csv and _ocr_bad_pages.csv")
        return 0
    finally:
        mongo.close()


if __name__ == "__main__":
    raise SystemExit(main())
