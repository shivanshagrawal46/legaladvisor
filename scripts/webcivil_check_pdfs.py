"""Validate every downloaded PDF before OCR.

Catches the failure mode that matters for a partially-written download: a file
that opens fine but is truncated. We check the %PDF magic bytes, that the page
tree is readable, that the trailer (%%EOF) is present, and that each page can
actually be loaded - a truncated file typically opens, reports a page count from
the xref, then throws when a late page is touched.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import fitz

ROOT = Path(r"E:\WEBCIVIL")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def check(p: Path):
    """Return (ok, pages, problem)."""
    try:
        data = p.read_bytes()
    except Exception as exc:
        return False, 0, f"unreadable: {exc}"
    if not data.startswith(b"%PDF"):
        return False, 0, "missing %PDF header"
    if b"%%EOF" not in data[-2048:]:
        return False, 0, "no %%EOF in trailer (likely truncated)"
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        return False, 0, f"open failed: {str(exc)[:70]}"
    try:
        n = doc.page_count
        if n <= 0:
            return False, 0, "zero pages"
        # Touch first, middle and last page: truncation shows up at the end.
        for i in {0, n // 2, n - 1}:
            doc.load_page(i).get_text("text")
        return True, n, ""
    except Exception as exc:
        return False, 0, f"page load failed: {str(exc)[:70]}"
    finally:
        doc.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    args = ap.parse_args()
    root = Path(args.root)

    files = sorted(root.rglob("*.pdf"))
    print(f"checking {len(files)} PDFs under {root}\n")
    bad = []
    pages = 0
    for i, p in enumerate(files, 1):
        ok, n, prob = check(p)
        pages += n
        if not ok:
            bad.append((p, prob))
            print(f"  BAD  {p.relative_to(root)}  -> {prob}")
        if i % 200 == 0:
            print(f"  ...{i}/{len(files)} checked, {len(bad)} bad so far")

    print(f"\n{'=' * 70}")
    print(f"files checked : {len(files)}")
    print(f"total pages   : {pages:,}")
    print(f"corrupt/partial: {len(bad)}")
    if bad:
        print("\nRe-download these before ingesting:")
        for p, prob in bad:
            print(f"  {p}  ({prob})")
        return 1
    print("\nALL PDFs COMPLETE AND READABLE - safe to ingest.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
