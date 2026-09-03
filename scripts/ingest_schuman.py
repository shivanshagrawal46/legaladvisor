"""Ingest the Brian_Schuman/ filings — the Aug 2026 "fraud on the Court" papers
in In re IPA Asset Management, LLC, Case No. 8-25-72526-spg (Bankr. E.D.N.Y.).

Despite the folder name these were NOT filed by Brian Schuman. Three are Marie
Holdings' papers by Scott Kreppein (Devitt Spellman Barrett), and the fourth is
the Debtor's/DeRosa's own counsel asking for more time. Attribution is therefore
per-file, in FILES below, rather than one label for the batch.

None of this is our knowledge. Every record is stored with:

  * is_ours=False and contains_allegations=True — the assertions inside are
    contested party contentions, not findings of fact.
  * party_alignment — who advanced the assertion. Marie Holdings attacks DeRosa
    (the same target as us) but is still a third party, not our client; the Nash
    letter is the opposing debtor. Neither may be read as our position.
  * authority_score 1.0, deliberately below the 1.15 of neutral court records
    and the 1.05 of our counsel's own updates, so an allegation here never
    outranks an order, a deed, or our own work product on the same question.
  * privilege_status=public_record — publicly filed; nothing of ours is waived.

Pipeline (mirrors scripts/ingest_webcivil.py):
  1. FORCE-VISION OCR every page — Claude Sonnet 4.6 only, RapidOCR disabled.
     One `documents` record per PDF, idempotent by sha256.
  2. python -m scripts.chunk_embed_documents --source-type court_record \
         --instrument-subtype schuman_filing

Usage: python -m scripts.ingest_schuman --live   (default dry-run)
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.extractor.extractor import extract_from_bytes
from src.rag.evidence_schema import DEFAULT_MATTER_ID
from src.utils.hashing import sha256_bytes
from src.utils.logger import logger
from scripts.ingest_titles_full import norm_address, addr_core
from scripts.ingest_insurance import build_prop_index

ROOT = Path(__file__).resolve().parent.parent / "Brian_Schuman"
SUBTYPE = "schuman_filing"
CASE_ID = "ent_case_ipa_8_2025bk72526"
DEROSA_ID = "ent_per_david_derosa"
IPA_ID = "ent_llc_ipa_asset_management_llc"

_HOUSE_ST = re.compile(r"\b(\d{1,5}(?:-\d{1,5})?)\s+([A-Za-z][A-Za-z .']{2,40})")

KREPPEIN = "Scott Kreppein (Devitt Spellman Barrett, LLP)"
GOLDBERG = "J. Ted Donovan (Goldberg Weprin Finkel Goldstein LLP)"


def _d(y: int, mo: int, day: int) -> datetime:
    return datetime(y, mo, day, tzinfo=timezone.utc)


# Attribution per file, read off the documents themselves rather than inferred
# from the folder name.
FILES = {
    "Scott Memorandum.pdf": {
        "document_title": "Memorandum Re: Fraud on the Court",
        "docket_no": "159", "document_date": _d(2026, 8, 25),
        "filed_by": KREPPEIN, "filed_for": "Marie Holdings, Inc. (creditor)",
        "party_alignment": "co_creditor_vs_derosa",
    },
    "Scott Declaration.pdf": {
        "document_title": "Attorney Declaration of Scott Kreppein "
                          "(indexes exhibits A–MM)",
        "docket_no": "159-1", "document_date": _d(2026, 8, 25),
        "filed_by": KREPPEIN, "filed_for": "Marie Holdings, Inc. (creditor)",
        "party_alignment": "co_creditor_vs_derosa",
    },
    "Scott Kreppein Filing August 25.2026 Contents.pdf": {
        "document_title": "ECF document-selection index for Doc 159 "
                          "(46 parts, 1,013 pages, 66.18 MB)",
        "docket_no": "159", "document_date": _d(2026, 8, 25),
        "filed_by": KREPPEIN, "filed_for": "Marie Holdings, Inc. (creditor)",
        "party_alignment": "co_creditor_vs_derosa",
        "is_index_only": True,
    },
    "Letter from NASH August 26.pdf": {
        "document_title": "Letter to Hon. Sheryl P. Giugliano requesting an "
                          "extension to respond until September 8, 2026",
        "docket_no": "160", "document_date": _d(2026, 8, 26),
        "filed_by": GOLDBERG,
        "filed_for": "IPA Asset Management, LLC (debtor) and David DeRosa",
        "party_alignment": "adverse_debtor",
    },
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--live", dest="dry_run", action="store_false")
    ap.add_argument("--dump-text", default=None,
                    help="also write the OCR'd text to this folder for review")
    args = ap.parse_args()

    s = Settings.load()
    now = datetime.now(timezone.utc)
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    docs, ents, rels = m.db["documents"], m.db["entities"], m.db["relationships"]
    prop_idx = build_prop_index(ents)

    files = sorted(p for p in ROOT.rglob("*") if p.suffix.lower() == ".pdf")
    logger.info(f"{len(files)} Schuman filings in {ROOT}")

    records = []
    for p in files:
        raw = p.read_bytes()
        sha = sha256_bytes(raw)
        doc_id = "doc_schuman_" + sha[:16]
        if docs.find_one({"_id": doc_id}, {"_id": 1}):
            logger.info(f"  already ingested, skipping: {p.name}")
            continue
        # Force vision: reject any born-digital text layer so every page goes
        # to Claude Sonnet 4.6, and forbid the RapidOCR fallback outright.
        res = extract_from_bytes(
            raw, p.name,
            ocr_min_chars=10 ** 9, enable_ocr=True,
            vision_enabled=True, vision_model="claude-sonnet-4-6",
            vision_min_pages=1, allow_rapidocr=False,
        )
        text = (res.text or "").strip()
        pages = res.pages or []
        engines: dict = {}
        for pg in pages:
            k = getattr(pg, "method", None) or "unknown"
            engines[k] = engines.get(k, 0) + 1

        pids = []
        for mt in _HOUSE_ST.finditer(text):
            pid = prop_idx.get(addr_core(norm_address(f"{mt.group(1)} {mt.group(2)}")))
            if pid and pid not in pids:
                pids.append(pid)

        meta = FILES.get(p.name)
        if meta is None:
            logger.warning(f"  no attribution entry for {p.name!r} — add it to "
                           f"FILES before ingesting; skipping.")
            continue
        records.append({"path": p, "sha": sha, "doc_id": doc_id, "text": text,
                        "pages": len(pages), "engines": engines, "pids": pids,
                        "meta": meta})
        logger.info(f"  {p.name[:52]:54s} pages={len(pages):>3} "
                    f"chars={len(text):>7,} engines={engines} props={len(pids)}")

        if args.dump_text:
            out = Path(args.dump_text)
            out.mkdir(parents=True, exist_ok=True)
            (out / (p.stem + ".txt")).write_text(text, encoding="utf-8")

    if args.dry_run:
        logger.info("DRY RUN — re-run with --live to store.")
        m.close()
        return 0

    for r in records:
        p, meta = r["path"], r["meta"]
        doc = {
            "_id": r["doc_id"], "source_type": "court_record",
            "instrument_subtype": SUBTYPE, "matter_id": DEFAULT_MATTER_ID,
            "corpus": "court_records", "privilege_status": "public_record",
            "evidentiary_class": "court_record",
            # Below neutral court records (1.15) and our own work product (1.05):
            # these are contested contentions, not findings.
            "authority_score": 1.0,
            "is_ours": False, "contains_allegations": True,
            "alleges_against": [DEROSA_ID],
            "case_number": "8-25-72526-spg",
            "case_title": "In re IPA Asset Management, LLC",
            "court": "United States Bankruptcy Court, E.D.N.Y.",
            "case_ids": [CASE_ID], "property_ids": r["pids"],
            "entity_ids": [DEROSA_ID, IPA_ID],
            "page_count": r["pages"], "extracted_text": r["text"],
            "ocr_engines": r["engines"],
            "custody": {"source_files": [p.name], "source_path": str(p),
                        "sha256": r["sha"], "origin": "brian_schuman_folder",
                        "ingested_at": now},
            "quality": {"needs_review": len(r["text"]) < 200},
            "updated_at": now, "created_at": now,
            **meta,
        }
        docs.update_one({"_id": r["doc_id"]}, {"$set": doc}, upsert=True)

        for typ, dst in ([("FILED_IN", CASE_ID), ("ALLEGES_AGAINST", DEROSA_ID)]
                         + [("CONCERNS_PROPERTY", pid) for pid in r["pids"]]):
            rels.update_one({"type": typ, "src": r["doc_id"], "dst": dst},
                            {"$set": {"type": typ, "src": r["doc_id"], "dst": dst,
                                      "as_of": meta["document_date"],
                                      "source_doc_id": r["doc_id"],
                                      "is_ours": False, "updated_at": now}},
                            upsert=True)

    logger.info("================ SCHUMAN INGEST DONE ================")
    logger.info(f"stored {len(records)} filings "
                f"(documents/{SUBTYPE} total: "
                f"{docs.count_documents({'instrument_subtype': SUBTYPE})})")
    logger.info("Next: python -m scripts.chunk_embed_documents "
                f"--source-type court_record --instrument-subtype {SUBTYPE}")
    m.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
