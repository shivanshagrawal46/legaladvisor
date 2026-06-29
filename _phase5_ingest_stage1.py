"""PHASE 5 - STAGE 1: store + FRONTIER OCR + dedup + path-linkage.

Reads _phase5_manifest.json, and for every DISTINCT new-content file:
  - extracts text with FRONTIER-ONLY OCR policy:
      .pdf            -> force-vision every page (Claude Sonnet 4.6 -> GPT-5 fallback)
      .jpg/.png/etc   -> Claude Vision (NEVER RapidOCR)
      .docx/.xlsx     -> native structured parse
      .xls            -> xlrd / Excel COM
      .doc            -> Word COM
      .csv/.txt/.rtf  -> text decode
  - stores a `documents` record with the evidentiary spine + Bates + custody +
    path-derived linkage (matter, corpus, privilege, property_ids, doc_category)
    + occurrences[] (every E: path of this content).
For content already in the DB (attachments_v2 / documents), it does NOT re-store;
it appends the new occurrence/linkage to the existing record.

Resumable: a sha already stored as doc_p5_<sha16> is skipped (unless --reocr).
Idempotent. Spend-guarded.

Usage:
  python _phase5_ingest_stage1.py --matter da_response --limit 15 --dry   # Gate C dry-run
  python _phase5_ingest_stage1.py --matter da_response                    # ingest DA
  python _phase5_ingest_stage1.py                                         # all folders
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import traceback
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.extractor.extractor import extract_from_bytes
from src.extractor import rescue
from src.utils.logger import logger
from scripts.ingest_titles_full import norm_address, addr_core
from scripts.ingest_insurance import build_prop_index

MANIFEST = "_phase5_manifest.json"
FAILURES = "_phase5_stage1_failures.json"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".webp"}

CORPUS = {
    "ipa_litigation": "litigation_records",
    "shared_with_boris": "attorney_work_product",
    "da_response": "da_production",
    "discovery_mt": "discovery_production",
}
_HOUSE_ST = re.compile(r"\b(\d{1,5}(?:-\d{1,5})?)\s+([A-Za-z][A-Za-z .']{2,40})")
_CHECK_RE = re.compile(r"\b(\d{3,5})(?:\s*-\s*(\d{3,5}))?\b")
_AMOUNT_RE = re.compile(r"\$\s?([\d,]+(?:\.\d{2})?)")
_YEAR_RE = re.compile(r"\b(20\d{2})\b")

CATEGORY_RULES = [
    ("deed", ["deed"]),
    ("mortgage", ["mortgage"]),
    ("settlement_sheet", ["settlement sheet", "settlement analysis", "settlement reconciliation"]),
    ("closing_document", ["closing document", "closing doc"]),
    ("service_agreement", ["service agreement"]),
    ("projection_sheet", ["projection"]),
    ("contract", ["contract"]),
    ("bill_invoice", ["bills", "invoice", "bill "]),
    ("cheque", ["check issued", "checks issued", "cheque", "check recvd", "checks &"]),
    ("wire_confirmation", ["wire", "rent wire"]),
    ("title_report", ["title report", "title"]),
    ("affidavit", ["affidavit", "affirmation"]),
    ("otsc_filing", ["otsc"]),
    ("total_view_report", ["total view", "datatree", "tvr"]),
    ("tax_record", ["tax search", "tax bill", "statement of tax"]),
    ("llc_record", ["llc", "filingrec", "articles", "certificate of"]),
    ("rent_record", ["rent"]),
    ("litigation_filing", ["lawsuit", "complaint", "motion", "exhibit", "schedule a", "schedule b", "schedule c"]),
    ("property_summary_xls", ["property summary", "master list", "job ledger", "financing evaluator"]),
]
AUTHORITY = {
    "deed": 1.30, "mortgage": 1.25, "settlement_sheet": 1.15, "title_report": 1.15,
    "closing_document": 1.12, "cheque": 1.10, "wire_confirmation": 1.10,
    "bill_invoice": 1.05, "service_agreement": 1.08, "litigation_filing": 1.10,
    "affidavit": 1.05, "otsc_filing": 1.08, "tax_record": 1.05,
    "total_view_report": 1.05, "llc_record": 1.05, "rent_record": 1.02,
    "projection_sheet": 1.0, "contract": 1.05, "property_summary_xls": 1.0,
    "generic_document": 1.0,
}


def classify_category(path_low: str) -> str:
    for cat, kws in CATEGORY_RULES:
        if any(k in path_low for k in kws):
            return cat
    return "generic_document"


def resolve_properties(text_for_match: str, prop_idx: Dict[str, str]) -> List[str]:
    pids: List[str] = []
    for mt in _HOUSE_ST.finditer(text_for_match):
        ac = addr_core(norm_address(f"{mt.group(1)} {mt.group(2)}"))
        pid = prop_idx.get(ac)
        if pid and pid not in pids:
            pids.append(pid)
    return pids


def parse_occurrence(matter: str, rel: str, prop_idx) -> Dict[str, Any]:
    low = rel.lower()
    cat = classify_category(low)
    pids = resolve_properties(rel.replace("\\", " "), prop_idx)
    years = _YEAR_RE.findall(rel)
    checks = []
    if cat == "cheque":
        for m in _CHECK_RE.finditer(rel):
            checks.append(m.group(1))
            if m.group(2):
                checks.append(m.group(2))
    amts = _AMOUNT_RE.findall(rel)
    return {"matter": matter, "rel": rel, "doc_category": cat,
            "property_ids": pids, "years": years, "check_nos": checks,
            "amounts": amts}


def extract_frontier(path: Path, ext: str, s) -> Any:
    name = path.name
    data = path.read_bytes()
    if ext == ".pdf":
        return extract_from_bytes(
            data, name, ocr_lang=s.ocr_lang, ocr_min_chars=10_000_000,
            ocr_dpi=s.ocr_dpi, enable_ocr=True, vision_enabled=True,
            vision_model=s.ocr_vision_model, vision_min_pages=1,
            vision_dpi=s.ocr_vision_dpi,
            vision_concurrency=s.ocr_vision_max_concurrency)
    if ext in IMAGE_EXTS:
        return rescue.re_ocr_image_via_vision(data, name)
    if ext == ".xls":
        return rescue.extract_xls_via_xlrd(data, name)
    if ext == ".doc":
        return rescue.extract_doc_via_word_com(data, name)
    # .docx .xlsx .csv .txt .rtf .md .log
    return extract_from_bytes(data, name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--matter", default=None, help="scope to one matter")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry", action="store_true", help="extract+print, no DB writes")
    ap.add_argument("--reocr", action="store_true", help="redo even if stored")
    ap.add_argument("--manifest", default=MANIFEST, help="manifest json to ingest")
    ap.add_argument("--budget", type=float, default=3000.0)
    args = ap.parse_args()

    s = Settings.load()
    now = datetime.now(timezone.utc)
    from src.extractor.claude_ocr import init_spend_guard
    init_spend_guard(args.budget)

    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    m.ping()
    docs = m.db["documents"]
    ents = m.db["entities"]
    av2 = m.db["attachments_v2"]
    state = m.db["phase5_state"]
    prop_idx = build_prop_index(ents)
    logger.info(f"property index: {len(prop_idx)} keys")

    # existing fingerprints -> where
    existing_doc = {}
    for d in docs.find({}, {"custody.sha256": 1}):
        sh = (d.get("custody") or {}).get("sha256")
        if sh:
            existing_doc[sh] = d["_id"]
    existing_att = {}
    for a in av2.find({}, {"sha256": 1}):
        if a.get("sha256"):
            existing_att.setdefault(a["sha256"], a["_id"])

    data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    files = data["files"]
    if args.matter:
        files = [f for f in files if f["matter"] == args.matter]

    # group by sha -> occurrences
    by_sha: Dict[str, List[Dict]] = defaultdict(list)
    sha_info: Dict[str, Dict] = {}
    for f in files:
        by_sha[f["sha256"]].append(f)
        sha_info.setdefault(f["sha256"], f)

    shas = list(by_sha.keys())
    if args.limit:
        shas = shas[: args.limit]
    logger.info(f"distinct contents to process: {len(shas)} "
                f"(matter={args.matter or 'ALL'}, dry={args.dry})")

    # bates counter
    bdoc = state.find_one({"_id": "bates"}) or {"value": 0}
    bates = int(bdoc.get("value", 0))

    stored = linked_existing = skipped = failed = 0
    failures = []
    method_tally = defaultdict(int)

    for i, sha in enumerate(shas, 1):
        occ_files = by_sha[sha]
        matter = occ_files[0]["matter"]
        occurrences = [parse_occurrence(o["matter"], o["rel"], prop_idx) for o in occ_files]
        all_pids = sorted({p for o in occurrences for p in o["property_ids"]})
        cat = occurrences[0]["doc_category"]
        doc_id = "doc_p5_" + sha[:16]

        # already in DB (email attachment or prior doc) -> link occurrence only
        if sha in existing_att or sha in existing_doc:
            tgt_coll, tgt_id = (("attachments_v2", existing_att[sha]) if sha in existing_att
                                else ("documents", existing_doc[sha]))
            if not args.dry:
                m.db[tgt_coll].update_one({"_id": tgt_id}, {"$addToSet": {
                    "phase5_occurrences": {"$each": [
                        {"matter": o["matter"], "rel": o["rel"],
                         "doc_category": o["doc_category"],
                         "property_ids": o["property_ids"]} for o in occurrences]}},
                    "$set": {"phase5_linked_at": now}})
            linked_existing += 1
            if i % 50 == 0:
                logger.info(f"  [{i}/{len(shas)}] linked-existing={linked_existing} "
                            f"stored={stored} failed={failed}")
            continue

        # resumable
        if not args.reocr and docs.find_one({"_id": doc_id}, {"_id": 1}):
            skipped += 1
            continue

        ext = sha_info[sha]["ext"]
        path = Path(sha_info[sha]["path"])
        try:
            res = extract_frontier(path, ext, s)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            failures.append({"sha": sha, "path": str(path), "ext": ext,
                             "error": f"{type(exc).__name__}: {exc}",
                             "tb": traceback.format_exc()[-800:]})
            logger.warning(f"  [{i}/{len(shas)}] EXTRACT FAILED {path.name[:40]}: {exc}")
            continue

        text = (res.text or "").strip()
        pages = res.pages or []
        for p in pages:
            method_tally[getattr(p, "method", "?")] += 1
        page_count = max(1, len(pages))

        if not text:
            failed += 1
            failures.append({"sha": sha, "path": str(path), "ext": ext,
                             "error": f"empty_text method={res.method} "
                                      f"reason={getattr(res,'skipped_reason',None)}"})
            logger.warning(f"  [{i}/{len(shas)}] EMPTY {path.name[:40]} "
                           f"method={res.method} reason={getattr(res,'skipped_reason',None)}")
            continue

        st = cat
        doc = {
            "_id": doc_id, "source_type": st, "doc_category": cat,
            "matter_id": matter, "corpus": CORPUS.get(matter, "litigation_records"),
            "privilege_status": "privileged",
            "evidentiary_class": "privileged_material",
            "authority_score": AUTHORITY.get(cat, 1.0),
            "property_ids": all_pids,
            "primary_property_id": (all_pids[0] if all_pids else None),
            "page_count": page_count, "extracted_text": text,
            "extraction_method": res.method,
            "ocr_confidence": getattr(res, "avg_ocr_confidence", None),
            "pages": [{"page_no": getattr(p, "page_no", j + 1),
                       "method": getattr(p, "method", "?"),
                       "char_count": len(getattr(p, "text", "") or ""),
                       "ocr_confidence": getattr(p, "ocr_confidence", None)}
                      for j, p in enumerate(pages)],
            "custody": {"sha256": sha, "source_files": [str(path)],
                        "origin": f"phase5:{matter}", "ingested_at": now},
            "occurrences": occurrences,
            "bates_start": None, "bates_end": None,
            "quality": {"needs_review": len(text) < 120},
            "updated_at": now, "created_at": now,
        }
        # bates
        doc["bates_start"] = f"MT-IPA-{bates + 1:07d}"
        doc["bates_end"] = f"MT-IPA-{bates + page_count:07d}"
        if args.dry:
            logger.info(f"  [{i}/{len(shas)}] DRY {matter}/{cat} pages={page_count} "
                        f"chars={len(text)} method={res.method} props={all_pids} "
                        f"page_methods={ {p['method'] for p in doc['pages']} } {path.name[:38]}")
        else:
            bates += page_count
            docs.update_one({"_id": doc_id}, {"$set": doc}, upsert=True)
            state.update_one({"_id": "bates"}, {"$set": {"value": bates}}, upsert=True)
            stored += 1
            if i % 25 == 0 or stored % 25 == 0:
                logger.info(f"  [{i}/{len(shas)}] stored={stored} linked={linked_existing} "
                            f"failed={failed} skip={skipped} last={cat}/{path.name[:30]}")

    logger.info("=" * 60)
    logger.info(f"STAGE1 {'DRY ' if args.dry else ''}DONE matter={args.matter or 'ALL'}: "
                f"stored={stored} linked_existing={linked_existing} "
                f"skipped={skipped} failed={failed}")
    logger.info(f"page method tally: {dict(method_tally)}")
    if failures:
        Path(FAILURES).write_text(json.dumps(failures, indent=1), encoding="utf-8")
        logger.info(f"failures -> {FAILURES} ({len(failures)})")
    m.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
