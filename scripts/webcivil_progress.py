"""Per-worker progress report for the sharded WebCivil pipeline."""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

TOTAL_PDFS = 1155
_SHARD_RE = re.compile(r"shard (\d+)/(\d+): (\d+) (?:file|doc)")
_DONE_RE = re.compile(r"\[(\d+)/(\d+)\]")
_DOCS_RE = re.compile(r"docs=(\d+)")
_CHUNK_RE = re.compile(r"chunks?=(\d+)")


def worker_lines(stage: str) -> list[str]:
    d = Path(rf"E:\WEBCIVIL_logs\{stage}")
    if not d.exists():
        return []
    out = []
    for log in sorted(d.glob("w*.err"), key=lambda p: int(p.stem[1:])):
        # loguru logs to stderr, so .err carries the real progress stream.
        txt = log.read_text(encoding="utf-8", errors="replace")
        alive = "" if "=== SUMMARY" in txt or "done." in txt[-400:] else "running"
        planned = 0
        m = _SHARD_RE.search(txt)
        if m:
            planned = int(m.group(3))
        seen = [int(x.group(1)) for x in _DONE_RE.finditer(txt)]
        cur = max(seen) if seen else 0
        errs = txt.count("Connection error") + txt.count("Traceback")
        pct = (cur / planned * 100) if planned else 0.0
        bar = "#" * int(pct / 5) + "." * (20 - int(pct / 5))
        out.append(f"  w{log.stem[1:]:<3}[{bar}] {cur:>4}/{planned:<4} "
                   f"{pct:>5.1f}%  err={errs:<4} {alive}")
    return out


def main() -> int:
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    docs = m.db["documents"]
    q = {"instrument_subtype": "nyscef_efiled"}
    n_ocr = docs.count_documents(q)
    n_emb = docs.count_documents({**q, "chunked_at": {"$ne": None}})
    n_pages = next(docs.aggregate([{"$match": q},
                                   {"$group": {"_id": None,
                                               "p": {"$sum": "$page_count"}}}]),
                   {}).get("p", 0)
    chunks = m.db["email_chunks_v2"]
    n_chunks = chunks.count_documents({"instrument_subtype": "nyscef_efiled"})
    n_linked = chunks.count_documents({"instrument_subtype": "nyscef_efiled",
                                       "entity_backfill_at": {"$ne": None}})

    print(f"=== WebCivil pipeline  {time.strftime('%H:%M:%S')} ===")
    print(f"OCR'd    : {n_ocr:>5}/{TOTAL_PDFS}  ({n_ocr / TOTAL_PDFS * 100:.1f}%)"
          f"   pages={n_pages}")
    print(f"Embedded : {n_emb:>5}/{TOTAL_PDFS}  ({n_emb / TOTAL_PDFS * 100:.1f}%)"
          f"   chunks={n_chunks}")
    print(f"Entity-linked chunks: {n_linked}/{n_chunks}")
    for stage in ("ocr", "embed"):
        lines = worker_lines(stage)
        if lines:
            print(f"\n-- {stage} workers --")
            print("\n".join(lines))
    m.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
