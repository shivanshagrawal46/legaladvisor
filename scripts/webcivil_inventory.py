"""Full inventory of E:\\WEBCIVIL: PDFs, pages and ingest state per case."""
from __future__ import annotations

import sys
from pathlib import Path

import fitz

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

ROOT = Path(r"E:\WEBCIVIL")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main() -> int:
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    docs = m.db["documents"]
    done = {}
    for d in docs.find({"instrument_subtype": "nyscef_efiled"},
                       {"custody.source_files": 1, "chunked_at": 1}):
        srcs = (d.get("custody") or {}).get("source_files") or []
        if srcs:
            done[srcs[0]] = bool(d.get("chunked_at"))

    print(f"{'case folder':<22}{'index no':<14}{'pdfs':>6}{'pages':>8}{'MB':>8}"
          f"{'ocr':>6}{'emb':>6}{'todo':>6}")
    print("-" * 82)
    t_pdf = t_pg = t_mb = t_ocr = t_emb = 0
    for d in sorted(x for x in ROOT.iterdir()
                    if x.is_dir() and x.name.startswith("IndexNo_")):
        files = sorted(d.glob("*.pdf"))
        pages = 0
        for p in files:
            try:
                doc = fitz.open(p)
                pages += doc.page_count
                doc.close()
            except Exception:
                pass
        mb = sum(p.stat().st_size for p in files) / 1048576
        n_ocr = sum(1 for p in files if p.name in done)
        n_emb = sum(1 for p in files if done.get(p.name))
        idx = f"{d.name[8:-4]}/{d.name[-4:]}"
        print(f"{d.name:<22}{idx:<14}{len(files):>6}{pages:>8}{mb:>8.0f}"
              f"{n_ocr:>6}{n_emb:>6}{len(files) - n_ocr:>6}")
        t_pdf += len(files); t_pg += pages; t_mb += mb
        t_ocr += n_ocr; t_emb += n_emb
    print("-" * 82)
    print(f"{'TOTAL':<36}{t_pdf:>6}{t_pg:>8}{t_mb:>8.0f}{t_ocr:>6}{t_emb:>6}"
          f"{t_pdf - t_ocr:>6}")
    print(f"\nfolders: {len([x for x in ROOT.iterdir() if x.is_dir()])}")
    print(f"PDFs to OCR   : {t_pdf - t_ocr}")
    print(f"PDFs to embed : {t_pdf - t_emb}")
    m.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
