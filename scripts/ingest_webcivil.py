"""Ingest NYSCEF e-filed PDFs downloaded from WebCivil Supreme into the corpus.

Layout produced by the manual WebCivil download:

    E:\\WEBCIVIL\\IndexNo_<index><year>\\<index>_<year>_<caption>_<DOCTYPE>_<n>.pdf

The case caption is identical for every file in a folder, so we recover it as
the longest common prefix of that folder's filenames; whatever follows it is the
document type, and the trailing integer is the NYSCEF document number. The
authoritative metadata (index number, NYSCEF doc number, filing date, county
clerk) is then re-read from the NYSCEF stamp that appears on every e-filed page,
which beats trusting a filename the website truncated.

Pipeline (mirrors scripts/ingest_pacer_case.py):
  1. FORCE-VISION OCR every page - Claude Sonnet 4.6, GPT-5 vision fallback,
     RapidOCR only if both fail. Original bytes to GridFS, one `documents`
     record per PDF (source_type=court_record, corpus=court_records,
     privilege_status=public_record). Idempotent by sha256.
  2. python -m scripts.chunk_embed_documents --source-type court_record \
         --ctx-batch 8 --shard k/N        (contextual summary + chunk + embed)

Because identity is the sha256 of the file, the same document appearing under
two different party searches - or in two different case folders - is stored
ONCE and simply gains a second entry in `case_ids`. Nothing is OCR'd twice.

Usage:
  python -m scripts.ingest_webcivil                          # dry run
  python -m scripts.ingest_webcivil --live --workers 6
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.extractor.extractor import extract_from_bytes
from src.extractor.claude_ocr import init_spend_guard
from src.rag.evidence_schema import DEFAULT_MATTER_ID
from src.utils.hashing import sha256_bytes
from src.utils.logger import logger

ROOT_DEFAULT = r"E:\WEBCIVIL"
COURT = "New York State Supreme Court"

# The party names this collection was built around. We record which of them
# actually appear in each document's text, because a WebCivil caption only ever
# shows the FIRST plaintiff and FIRST defendant - an entity can be a party to a
# case whose caption never mentions it.
TARGET_PARTIES = [
    "ISLAND PROPERTIES & ASSOCIATES, LLC",
    "IPA ASSET MANAGEMENT, LLC",
    "IPA ASSET MANAGEMENT III, LLC",
    "IPA ASSET MANAGEMENT IV, LLC",
    "31F0, LLC",
    "453F, LLC",
    "91G, LLC",
    "LONG ISLAND INVESTMENTS, LLC",
    "35DO, LLC",
    "1032C, LLC",
    "DAVID DEROSA",
]

_FOLDER_RE = re.compile(r"^IndexNo_(\d+)(\d{4})$")
_TRAILING_NUM_RE = re.compile(r"_(\d+)$")

# NYSCEF stamps every e-filed page with a header block like:
#   FILED: SUFFOLK COUNTY CLERK 09/13/2022 03:42 PM   INDEX NO. 200331/2022
#   NYSCEF DOC. NO. 113                               RECEIVED NYSCEF: 09/13/2022
_STAMP_INDEX_RE = re.compile(r"INDEX\s+NO\.\s*([0-9]{3,8}\s*[/\-]\s*[0-9]{4})", re.I)
_STAMP_DOCNO_RE = re.compile(r"NYSCEF\s+DOC\.\s*NO\.\s*(\d+)", re.I)
_STAMP_RECV_RE = re.compile(r"RECEIVED\s+NYSCEF\s*:\s*(\d{1,2}/\d{1,2}/\d{4})", re.I)
_STAMP_FILED_RE = re.compile(
    r"FILED\s*:\s*([A-Z][A-Z .'-]{2,30}?COUNTY\s+CLERK)\s*(\d{1,2}/\d{1,2}/\d{4})", re.I)


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("_", " ")).strip()


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")


def _common_prefix(names: List[str]) -> str:
    """Longest common prefix of the folder's filenames, trimmed back to a token
    boundary. That prefix is `<index>_<year>_<caption>_`."""
    if not names:
        return ""
    pre = os.path.commonprefix(names)
    # Never let the prefix eat into a document type: cut at the last '_'.
    if "_" in pre:
        pre = pre[: pre.rindex("_") + 1]
    return pre


def discover_cases(root: Path) -> List[Dict[str, Any]]:
    """One record per IndexNo_* folder, with caption and per-file metadata."""
    cases: List[Dict[str, Any]] = []
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        m = _FOLDER_RE.match(d.name)
        if not m:
            logger.warning(f"skipping folder with unexpected name: {d.name}")
            continue
        idx_digits, year = m.group(1), m.group(2)
        index_number = f"{idx_digits}/{year}"
        files = sorted(d.glob("*.pdf"))
        if not files:
            continue
        stems = [f.stem for f in files]
        prefix = _common_prefix(stems)
        # Strip the leading "<index>_<year>_" to leave the caption.
        caption_raw = prefix
        lead = f"{idx_digits}_{year}_"
        if caption_raw.startswith(lead):
            caption_raw = caption_raw[len(lead):]
        case_title = _clean(caption_raw) or f"Index {index_number}"

        items = []
        for f in files:
            rest = f.stem[len(prefix):] if f.stem.startswith(prefix) else f.stem
            dm = _TRAILING_NUM_RE.search(rest)
            doc_no = int(dm.group(1)) if dm else None
            doc_type = _clean(rest[: dm.start()] if dm else rest)
            items.append({"path": f, "doc_no": doc_no,
                          "doc_type": doc_type or "DOCUMENT"})
        cases.append({
            "folder": d, "index_number": index_number, "case_title": case_title,
            "case_id": f"ent_case_nyscef_{idx_digits}_{year}",
            "prefix": prefix, "items": items,
        })
    return cases


def parse_stamp(text: str) -> Dict[str, Any]:
    """Pull index number / NYSCEF doc number / filing date off the e-file stamp.
    Only the first ~4000 chars are searched: the stamp is a page header, and
    scanning the whole document would pick up stamps quoted inside exhibits."""
    head = text[:4000]
    out: Dict[str, Any] = {}
    m = _STAMP_INDEX_RE.search(head)
    if m:
        out["stamp_index_number"] = re.sub(r"\s*", "", m.group(1)).replace("-", "/")
    m = _STAMP_DOCNO_RE.search(head)
    if m:
        out["stamp_doc_no"] = int(m.group(1))
    m = _STAMP_RECV_RE.search(head)
    if m:
        try:
            out["stamp_received"] = datetime.strptime(
                m.group(1), "%m/%d/%Y").replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    m = _STAMP_FILED_RE.search(head)
    if m:
        out["county_clerk"] = _clean(m.group(1)).title()
        try:
            out["stamp_filed"] = datetime.strptime(
                m.group(2), "%m/%d/%Y").replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return out


def parties_present(text: str) -> List[str]:
    """Which of the target entities are named anywhere in this document."""
    up = re.sub(r"\s+", " ", (text or "").upper())
    found = []
    for p in TARGET_PARTIES:
        # Compare on alphanumerics only so ", LLC" / " LLC" / "&" vs "AND"
        # and OCR spacing noise don't cause misses.
        needle = re.sub(r"[^A-Z0-9]", "", p.upper())
        hay = re.sub(r"[^A-Z0-9]", "", up)
        if needle and needle in hay:
            found.append(p)
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=ROOT_DEFAULT)
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--live", dest="dry_run", action="store_false")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--budget", type=float, default=400.0)
    ap.add_argument("--limit", type=int, default=0, help="max PDFs (testing)")
    ap.add_argument("--reocr", action="store_true")
    ap.add_argument("--smart", action="store_true",
                    help="vision only on scanned pages; keep born-digital text layer")
    ap.add_argument("--vision-concurrency", type=int, default=0,
                    help="pages in flight per document (0 = auto from --workers)")
    ap.add_argument("--only-case", default=None, help="restrict to one index number")
    ap.add_argument("--shard", default=None,
                    help="k/N disjoint worker shard. Files are ordered largest-"
                         "first and dealt round-robin, so every shard gets a "
                         "comparable page count instead of one worker landing "
                         "all the 100-page exhibits.")
    ap.add_argument("--retry-failed", action="store_true",
                    help="re-OCR only the documents that still have untranscribed "
                         "pages, or that predate the no-RapidOCR policy. Leaves "
                         "every complete document alone.")
    args = ap.parse_args()

    s = Settings.load()
    now = datetime.now(timezone.utc)
    init_spend_guard(args.budget)

    root = Path(args.root)
    if not root.exists():
        logger.error(f"root does not exist: {root}")
        return 2
    cases = discover_cases(root)
    if args.only_case:
        cases = [c for c in cases if c["index_number"] == args.only_case]
    total_files = sum(len(c["items"]) for c in cases)
    logger.info(f"{len(cases)} case folder(s), {total_files} PDF(s) under {root}")
    for c in cases:
        logger.info(f"  {c['index_number']:<16} {len(c['items']):>4} docs  {c['case_title'][:70]}")

    # Per-document page concurrency has to be divided among the workers or the
    # combined in-flight vision calls will trip Anthropic's rate limit.
    vconc = args.vision_concurrency or max(
        2, int(s.ocr_vision_max_concurrency) // max(1, args.workers))
    ocr_min_chars = s.ocr_text_layer_min_chars if args.smart else 10_000_000
    logger.info(f"workers={args.workers} vision_concurrency={vconc}/doc "
                f"force_vision={not args.smart} budget=${args.budget}")

    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    docs, ents, rels = m.db["documents"], m.db["entities"], m.db["relationships"]
    gridfs_files = m.db["attachment_files.files"]

    if not args.dry_run:
        for c in cases:
            ents.update_one({"_id": c["case_id"]}, {"$set": {
                "_id": c["case_id"], "kind": "case", "matter_id": DEFAULT_MATTER_ID,
                "canonical_name": f"{c['case_title']} — Index {c['index_number']}",
                "aliases": list({c["case_title"], c["index_number"],
                                 c["index_number"].replace("/", "-")}),
                "case_number": c["index_number"], "court": COURT,
                "source": "webcivil_nyscef", "updated_at": now,
            }, "$setOnInsert": {"created_at": now}}, upsert=True)
        logger.info(f"upserted {len(cases)} case entities")

    # Documents to force through OCR again even though they already have text:
    # ones with pages neither vision model could read, and ones ingested before
    # the no-RapidOCR policy existed (so every record carries an engine tally).
    force_paths: set = set()
    if args.retry_failed:
        for d in docs.find({"instrument_subtype": "nyscef_efiled",
                            "$or": [{"ocr_failed_pages": {"$gt": 0}},
                                    {"ocr_engine_policy": {"$exists": False}}]},
                           {"custody.source_path": 1, "ocr_failed_pages": 1}):
            sp = (d.get("custody") or {}).get("source_path")
            if sp:
                force_paths.add(sp)
        logger.info(f"--retry-failed: {len(force_paths)} document(s) queued for re-OCR")

    work: List[Tuple[int, Dict[str, Any], Dict[str, Any]]] = []
    for c in cases:
        for it in c["items"]:
            work.append((0, c, it))
    if args.shard:
        sk, sn = (int(x) for x in args.shard.split("/"))
        # Deal largest-first so page counts balance across shards; byte size is
        # a good proxy for page count and needs no PDF parsing.
        ordered = sorted(work, key=lambda t: -t[2]["path"].stat().st_size)
        work = [t for i, t in enumerate(ordered) if i % sn == sk]
        mb = sum(t[2]["path"].stat().st_size for t in work) / 1048576
        logger.info(f"shard {sk}/{sn}: {len(work)} file(s), {mb:.0f} MB in this worker")

    work = [(i + 1, c, it) for i, (_, c, it) in enumerate(work)]
    if args.limit:
        work = work[: args.limit]
    nfiles = len(work)

    counts = {"processed": 0, "skipped": 0, "failed": 0, "pages": 0,
              "dedup_crosslinked": 0, "empty_text": 0, "failed_pages": 0}
    lock = threading.Lock()
    party_hits: Dict[str, set] = {}
    engine_totals: Dict[str, int] = {}

    def handle(job) -> None:
        n, case, it = job
        p: Path = it["path"]
        try:
            data = p.read_bytes()
        except Exception as exc:  # noqa: BLE001
            with lock:
                counts["failed"] += 1
            logger.warning(f"  [{n}/{nfiles}] READ FAILED {p.name[:60]}: {exc}")
            return
        sha = sha256_bytes(data)
        doc_id = "doc_webcivil_" + sha[:16]

        existing = docs.find_one({"_id": doc_id},
                                 {"extracted_text": 1, "case_ids": 1})
        redo = args.reocr or str(p) in force_paths
        if existing and (existing.get("extracted_text") or "").strip() and not redo:
            # Same file already ingested - possibly under a different case or a
            # different party search. Link this case in; never OCR it twice.
            if case["case_id"] not in (existing.get("case_ids") or []):
                if not args.dry_run:
                    docs.update_one({"_id": doc_id},
                                    {"$addToSet": {"case_ids": case["case_id"]},
                                     "$set": {"updated_at": now}})
                    rels.update_one(
                        {"type": "FILED_IN", "src": doc_id, "dst": case["case_id"]},
                        {"$set": {"type": "FILED_IN", "src": doc_id,
                                  "dst": case["case_id"], "updated_at": now}},
                        upsert=True)
                with lock:
                    counts["dedup_crosslinked"] += 1
                logger.info(f"  [{n}/{nfiles}] DEDUP -> linked existing doc to "
                            f"{case['index_number']}  {p.name[:46]}")
                return
            with lock:
                counts["skipped"] += 1
            logger.info(f"  [{n}/{nfiles}] SKIP (already OCR'd) #{it['doc_no']} {p.name[:46]}")
            return

        if args.dry_run:
            logger.info(f"  [{n}/{nfiles}] would OCR {case['index_number']} "
                        f"#{it['doc_no']:<4} {it['doc_type'][:28]:<28} {p.name[:44]}")
            return

        try:
            res = extract_from_bytes(
                data, p.name,
                ocr_lang=s.ocr_lang, ocr_min_chars=ocr_min_chars, ocr_dpi=s.ocr_dpi,
                enable_ocr=True, vision_enabled=True, vision_model=s.ocr_vision_model,
                vision_min_pages=1, vision_dpi=s.ocr_vision_dpi,
                vision_concurrency=vconc,
                allow_rapidocr=False)
            text = (res.text or "").strip()
        except Exception as exc:  # noqa: BLE001
            with lock:
                counts["failed"] += 1
            logger.warning(f"  [{n}/{nfiles}] OCR FAILED {p.name[:50]}: {str(exc)[:140]}")
            return

        npages = len(res.pages or [])
        stamp = parse_stamp(text)
        found = parties_present(text)
        # Per-page engine tally, so "which pages did Claude do vs GPT-5, and did
        # anything fail?" is answerable from the database without re-running OCR.
        engines: Dict[str, int] = {}
        for pg in (res.pages or []):
            engines[getattr(pg, "method", "unknown")] = \
                engines.get(getattr(pg, "method", "unknown"), 0) + 1
        failed_pages = sum(v for k, v in engines.items()
                           if k in ("vision_failed", "vision_unavailable",
                                    "ocr_failed", "render_failed", "ocr_capped"))

        if not gridfs_files.find_one({"metadata.sha256": sha}, {"_id": 1}):
            try:
                m.gridfs.upload_from_stream(
                    p.name, data,
                    metadata={"sha256": sha, "origin": "webcivil_nyscef",
                              "index_number": case["index_number"]})
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"    gridfs store failed for {p.name[:40]}: {exc}")

        doc_date = stamp.get("stamp_received") or stamp.get("stamp_filed")
        doc = {
            "_id": doc_id, "source_type": "court_record",
            "instrument_subtype": "nyscef_efiled", "matter_id": DEFAULT_MATTER_ID,
            "corpus": "court_records", "privilege_status": "public_record",
            "evidentiary_class": "court_record", "authority_score": 1.15,
            "case_number": case["index_number"], "case_title": case["case_title"],
            "court": COURT, "county_clerk": stamp.get("county_clerk"),
            "docket_no": stamp.get("stamp_doc_no") or it["doc_no"],
            "nyscef_doc_no": stamp.get("stamp_doc_no") or it["doc_no"],
            "document_title": it["doc_type"], "document_date": doc_date,
            "filed_date": stamp.get("stamp_filed"),
            "received_date": stamp.get("stamp_received"),
            "stamp_index_number": stamp.get("stamp_index_number"),
            "target_parties": found,
            "page_count": npages, "extracted_text": text,
            "ocr_method": res.method, "ocr_avg_confidence": res.avg_ocr_confidence,
            "ocr_page_methods": engines, "ocr_failed_pages": failed_pages,
            "ocr_engine_policy": "claude_sonnet_4_6 -> gpt5_vision (no rapidocr)",
            "custody": {"source_files": [p.name], "source_path": str(p),
                        "sha256": sha, "origin": "webcivil_nyscef",
                        "retrieved_from": "WebCivil Supreme / NYSCEF",
                        "ingested_at": now},
            "quality": {"needs_review": len(text) < 200 or failed_pages > 0,
                        "ocr_failed_pages": failed_pages},
            "updated_at": now, "created_at": now,
        }
        docs.update_one({"_id": doc_id},
                        {"$set": doc,
                         "$addToSet": {"case_ids": case["case_id"]},
                         "$unset": {"chunked_at": "", "chunk_count": ""}},
                        upsert=True)
        rels.update_one({"type": "FILED_IN", "src": doc_id, "dst": case["case_id"]},
                        {"$set": {"type": "FILED_IN", "src": doc_id,
                                  "dst": case["case_id"], "as_of": doc_date,
                                  "updated_at": now}}, upsert=True)

        with lock:
            counts["processed"] += 1
            counts["pages"] += npages
            counts["failed_pages"] += failed_pages
            for k, v in engines.items():
                engine_totals[k] = engine_totals.get(k, 0) + v
            if len(text) < 200:
                counts["empty_text"] += 1
            for f in found:
                party_hits.setdefault(f, set()).add(case["index_number"])
        logger.info(f"  [{n}/{nfiles}] OK {case['index_number']} #{doc['docket_no']} "
                    f"pages={npages} chars={len(text):,} {res.method} "
                    f"{it['doc_type'][:26]}")

    if args.workers > 1 and not args.dry_run:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futs = [pool.submit(handle, j) for j in work]
            for f in as_completed(futs):
                exc = f.exception()
                if exc:
                    logger.warning(f"  worker crashed: {type(exc).__name__}: {exc}")
    else:
        for j in work:
            handle(j)

    logger.info("================ WEBCIVIL OCR INGEST DONE ================")
    logger.info(f"processed={counts['processed']} skipped={counts['skipped']} "
                f"cross-linked={counts['dedup_crosslinked']} failed={counts['failed']} "
                f"pages={counts['pages']} thin_text={counts['empty_text']}")
    if engine_totals:
        logger.info("pages by OCR engine (RapidOCR is disabled for this corpus):")
        for k, v in sorted(engine_totals.items(), key=lambda kv: -kv[1]):
            logger.info(f"    {k:<24} {v}")
        if counts["failed_pages"]:
            logger.warning(f"  {counts['failed_pages']} page(s) got NO transcription "
                           f"from either Claude or GPT-5 — re-run with --reocr")
    if party_hits:
        logger.info("target parties found in text:")
        for p in TARGET_PARTIES:
            if p in party_hits:
                logger.info(f"    {p:<40} {sorted(party_hits[p])}")
        missing = [p for p in TARGET_PARTIES if p not in party_hits]
        if missing:
            logger.info(f"  NOT found in any document: {missing}")
    logger.info(f"documents/court_record total: "
                f"{docs.count_documents({'source_type':'court_record'})}")
    if args.dry_run:
        logger.info("DRY RUN — re-run with --live to store.")
    m.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
