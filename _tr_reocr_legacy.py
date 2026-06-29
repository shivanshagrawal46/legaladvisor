"""
Re-OCR the legacy title docs that still contain RapidOCR ('ocr') pages, using
frontier vision (Claude Sonnet 4.6 -> GPT-5), sourcing the original PDFs from
F:\Title reports. Brings the ENTIRE title corpus to frontier-only.

Resolves each doc to its source file via custody.source_files relative paths
(e.g. '2021\\X.pdf' -> F:\Title reports\\2021\\X.pdf), with a basename-index
fallback. Replaces extracted_text + extraction_method, records ocr_upgraded_*,
and unsets chunked_at so the doc is re-chunked.

Usage:
  python _tr_reocr_legacy.py            # dry-run: match rate + page totals
  python _tr_reocr_legacy.py --live
  python _tr_reocr_legacy.py --live --shard 0/3
"""
from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.utils.logger import logger
from scripts.ingest_titles_full import full_ocr

ROOT = Path(r"F:\Title reports")


def methods(d):
    em = d.get("extraction_method")
    if isinstance(em, dict):
        return em
    if isinstance(em, str) and em:
        return {em: int(d.get("page_count") or d.get("num_pages") or 1)}
    return {}


def has_rapid(d):
    return any(k in ("ocr", "rapidocr") for k in methods(d))


def build_basename_index():
    from collections import Counter
    cnt = Counter()
    path = {}
    for p in ROOT.rglob("*.pdf"):
        key = p.name.lower()
        cnt[key] += 1
        path.setdefault(key, p)
    return dict(cnt), path


def _paths_with_folders(d):
    """Only source_path/path values that carry folder structure (not bare names).
    These can resolve EXACTLY against F:, giving an unambiguous file identity."""
    out = []
    c = d.get("custody") or {}
    srcs = list(c.get("source_files") or [])
    if c.get("source_path"):
        srcs.append({"source_path": c["source_path"]})
    for f in srcs:
        if isinstance(f, dict):
            p = f.get("source_path") or f.get("path") or ""
        else:
            p = str(f)
        if p:
            out.append(p.replace("/", "\\"))
    return out


def resolve_exact(d):
    """100%-safe resolution: an absolute path that exists, or a folder-qualified
    relative path that resolves under F:. Returns Path or None. No address/basename
    guessing (unsafe: same address has multiple versions across year folders)."""
    for p in _paths_with_folders(d):
        if os.path.isabs(p) and os.path.exists(p):
            return Path(p)
        # strip a leading 'Title reports\' if present, then join under ROOT
        rel = p
        low = rel.lower()
        if low.startswith("f:\\title reports\\"):
            rel = rel[len("f:\\title reports\\"):]
        cand = ROOT / rel
        if cand.exists():
            return cand
    return None


def resolve_basename_unique(d, bidx_count, bidx_path):
    """Tier-2: basename matches exactly ONE file in F: -> still unambiguous."""
    c = d.get("custody") or {}
    for f in (c.get("source_files") or []):
        if isinstance(f, dict):
            p = f.get("source_path") or f.get("path") or f.get("name") or ""
            if p:
                name = Path(p.replace("/", "\\")).name.lower()
                if bidx_count.get(name) == 1:
                    return bidx_path[name]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--shard", default=None)
    args = ap.parse_args()
    s = Settings.load()
    now = datetime.now(timezone.utc)
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    m.ping()
    docs = m.db["documents"]

    proj = {"extraction_method": 1, "page_count": 1, "num_pages": 1,
            "custody": 1, "property_address": 1}
    targets = [d for d in docs.find({"source_type": "title_report"}, proj)
               if has_rapid(d)]
    if args.shard:
        import hashlib
        sk, sn = (int(x) for x in args.shard.split("/"))
        targets = [d for d in targets
                   if int(hashlib.md5(d["_id"].encode()).hexdigest(), 16) % sn == sk]

    logger.info(f"legacy title docs with RapidOCR pages: {len(targets)}")
    bidx_count, bidx_path = build_basename_index()
    logger.info(f"F: basename index: {len(bidx_path)} unique names")

    # tier the targets by resolution safety
    matched, deferred = [], []
    rapid_pages = 0
    for d in targets:
        rp = sum(v for k, v in methods(d).items() if k in ("ocr", "rapidocr"))
        rapid_pages += rp
        p = resolve_exact(d)
        tier = "EXACT"
        if not p:
            p = resolve_basename_unique(d, bidx_count, bidx_path)
            tier = "UNIQUE_NAME"
        if p:
            matched.append((d, p, tier))
        else:
            deferred.append(d)

    n_exact = sum(1 for _, _, t in matched if t == "EXACT")
    n_uniq = sum(1 for _, _, t in matched if t == "UNIQUE_NAME")
    logger.info(f"SAFE matches: {len(matched)} (EXACT={n_exact}, UNIQUE_NAME={n_uniq}) | "
                f"DEFERRED (ambiguous/no-source): {len(deferred)} | "
                f"total RapidOCR pages across all: {rapid_pages}")
    for d in deferred[:40]:
        logger.warning(f"  DEFERRED {d['_id'][:26]} addr={d.get('property_address')!r}")

    if not args.live:
        logger.info("DRY-RUN — no OCR. Re-run with --live (optionally --shard k/N).")
        m.close()
        return 0

    done = upgraded_pages = 0
    for d, p, tier in matched:
        try:
            res = full_ocr(Path(p), s, force=True)  # frontier every page
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"  {d['_id']}: OCR failed ({str(exc)[:80]})")
            continue
        pm = [pg.method for pg in res.pages]
        nf = [x for x in pm if x not in ("claude_vision", "openai_vision")]
        if nf:
            logger.warning(f"  {d['_id']}: still {len(nf)} non-frontier pages -> keeping previous")
            continue
        docs.update_one({"_id": d["_id"]}, {"$set": {
            "extracted_text": res.text,
            "extraction_method": {mth: pm.count(mth) for mth in set(pm)},
            "page_count": len(res.pages),
            "ocr_upgraded_from_legacy": True,
            "ocr_upgraded_at": now,
        }, "$unset": {"chunked_at": ""}})
        done += 1
        upgraded_pages += len(res.pages)
        logger.info(f"  [{done}/{len(matched)}] re-OCR'd {d['_id']} <- {p.name} "
                    f"({len(res.pages)} pages, methods={ {mth: pm.count(mth) for mth in set(pm)} })")

    logger.info(f"DONE: re-OCR'd {done}/{len(matched)} docs, {upgraded_pages} pages. "
                f"chunked_at unset -> re-chunk next.")
    m.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
