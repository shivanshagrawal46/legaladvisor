"""Print the number of WebCivil PDFs still outstanding for a stage.

Used by the pipeline orchestrator to decide completion from the database
rather than from the presence of worker processes.
"""
from __future__ import annotations

import sys
from pathlib import Path

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

ROOT = Path(r"E:\WEBCIVIL")
Q = {"instrument_subtype": "nyscef_efiled"}


def main() -> int:
    stage = (sys.argv[1] if len(sys.argv) > 1 else "ocr").lower()
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    docs = m.db["documents"]

    if stage == "ocr":
        done_names, done_shas = set(), set()
        for d in docs.find(Q, {"custody.sha256": 1, "custody.source_files": 1}):
            cust = d.get("custody") or {}
            done_names.update(cust.get("source_files") or [])
            if cust.get("sha256"):
                done_shas.add(cust["sha256"])
        # A file whose bytes are already ingested under a different name (e.g. a
        # "foo (1).pdf" re-download) is done, not outstanding. Hashing is scoped
        # to unaccounted files only, so this stays cheap.
        import hashlib
        rem = 0
        for c in ROOT.iterdir():
            if not c.is_dir():
                continue
            for p in c.glob("*.pdf"):
                if p.name in done_names:
                    continue
                if hashlib.sha256(p.read_bytes()).hexdigest() in done_shas:
                    continue
                rem += 1
        print(rem)
    else:
        print(docs.count_documents({**Q, "chunked_at": None}))
    m.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
