"""
Create canonical property entities for portfolio addresses that appear in the
money graph but are absent from the entity graph, then link their money records.

The money graph exposed ~273 real property addresses (Newark/LI rehab portfolio)
referenced by thousands of cheques/line-items but never created as property
entities. Per the total-linkage requirement we create them, with full provenance
and a needs_review flag (auditable; mergeable by a later consolidate pass), and
attach property_ids so the per-property money graph surfaces every record.

Quality gate (avoid P&L noise like 'Profit Allocation', 'Legal Fees'):
  * address-core must start with a house number, have >=2 tokens, and contain a
    real street word (a token beyond the house number that is not purely a
    directional), and contain no distribution/expense stopwords.

Usage:
  python _money_create_props.py            # dry-run
  python _money_create_props.py --live
"""
from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.utils.logger import logger
from scripts.ingest_titles_full import norm_address, addr_core, _DIRECTIONALS
from scripts.ingest_insurance import build_prop_index
from scripts.build_entities_from_llc import slug
from pymongo import UpdateOne

STOP = {"profit", "allocation", "total", "grand", "fees", "legal", "various",
        "properties", "property", "transfer", "wire", "rent", "investment",
        "reimb", "package", "half", "paid", "misc", "expenses", "exp", "exps",
        "of", "management", "payroll", "insurance", "tax", "taxes", "gh", "ii",
        "credit", "card", "loan", "deposit", "refund", "balance", "due"}


def _acore(addr: str) -> str:
    return addr_core(norm_address(addr or ""))


def candidate_addrs(rec):
    out = []
    prop = (rec.get("property") or "").strip()
    if prop:
        out.append(prop)
    memo = (rec.get("memo") or "").strip()
    if memo:
        head = re.split(r"\s*[-–|]\s*|\ba/c\b|\bA/C\b|#", memo)[0].strip()
        if head and head != prop:
            out.append(head)
    return out


def is_real_address(core: str) -> bool:
    toks = core.split()
    if len(toks) < 2 or not toks[0][0].isdigit():
        return False
    street_words = [t for t in toks[1:] if t not in _DIRECTIONALS]
    if not street_words:
        return False
    if any(t in STOP for t in toks):
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args()
    s = Settings.load()
    now = datetime.now(timezone.utc)
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    m.ping()
    mr, ents = m.db["money_records"], m.db["entities"]
    rels = m.db["relationships"]
    idx = build_prop_index(ents)
    logger.info(f"existing property index: {len(idx)} keys")

    # gather unmatched real-address cores from unlinked money records
    core_raws = defaultdict(Counter)
    core_recs = defaultdict(list)
    for r in mr.find({"property_ids": {"$size": 0}},
                     {"property": 1, "memo": 1}):
        for a in candidate_addrs(r):
            ac = _acore(a)
            if ac and ac not in idx and is_real_address(ac):
                core_raws[ac][a.strip()] += 1
                core_recs[ac].append(r["_id"])
                break

    logger.info(f"NEW property entities to create: {len(core_raws)} "
                f"covering {sum(len(v) for v in core_recs.values())} money records")

    ops_ents = []
    new_index = {}
    for ac, raws in core_raws.items():
        # canonical address = the most complete raw text (most tokens, prefers one with city/state)
        canonical = max(raws, key=lambda t: (len(t.split()), len(t)))
        eid = "ent_prop_a_" + slug(ac)
        new_index[ac] = eid
        ops_ents.append(UpdateOne(
            {"_id": eid},
            {"$setOnInsert": {
                "_id": eid, "kind": "property",
                "canonical_address": canonical,
                "address_variants": sorted(raws),
                "address_core": ac,
                "parcel_id": None, "county": None,
                "source": "money_graph_inferred", "needs_review": True,
                "matter_id": getattr(s, "default_matter_id", None) or "discovery_mt",
                "created_at": now, "updated_at": now,
            }}, upsert=True))

    for ac, raws in list(core_raws.items())[:25]:
        logger.info(f"  {len(core_recs[ac]):4d} recs | {ac:24s} | {new_index[ac]} | {max(raws, key=lambda t:(len(t.split()),len(t)))!r}")

    if not args.live:
        logger.info("DRY-RUN — no writes. Re-run with --live.")
        m.close()
        return 0

    if ops_ents:
        ents.bulk_write(ops_ents, ordered=False)
    logger.info(f"created/ensured {len(ops_ents)} property entities")

    # link money records + ABOUT_PROPERTY edges
    link_ops = []
    edge_ops = []
    linked = 0
    for ac, rec_ids in core_recs.items():
        eid = new_index[ac]
        for rid in rec_ids:
            link_ops.append(UpdateOne({"_id": rid}, {"$set": {"property_ids": [eid]}}))
            linked += 1
        # one money_about edge per (doc?, property) is overkill; record entity-level coverage
    for i in range(0, len(link_ops), 1000):
        mr.bulk_write(link_ops[i:i + 1000], ordered=False)
    logger.info(f"linked {linked} money records to {len(new_index)} new properties")
    logger.info(f"property entities now: {ents.count_documents({'kind':'property'})}")
    m.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
