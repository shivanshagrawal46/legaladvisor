"""
Money -> property linkage + amount_value numeric coercion.

Every grounded money_record carries a free-text `property` (e.g. "321 S Orange")
and/or a `memo` ("761 S 20th St - Rehab"). Canonicalize via the SAME
addr_core(norm_address(...)) key used by the title/insurance pipelines and attach
the canonical property entity id to `property_ids`, so the per-property graph
(money_records.find({"property_ids": pid})) surfaces every cheque/wire/line item.

Also coerce `amount_value` from string ("71.3") to float so property_graph's
money_total actually sums.

Usage: python _money_link_props.py            # dry-run (default)
       python _money_link_props.py --live
"""
from __future__ import annotations

import argparse
import re
from collections import Counter

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.utils.logger import logger
from scripts.ingest_titles_full import norm_address, addr_core
from scripts.ingest_insurance import build_prop_index
from pymongo import UpdateOne


def _acore(addr: str) -> str:
    return addr_core(norm_address(addr or ""))


def _to_float(v):
    if isinstance(v, (int, float)):
        return float(v)
    if not v:
        return None
    s = re.sub(r"[^0-9.\-]", "", str(v))
    if s in ("", ".", "-"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def candidate_addrs(rec) -> list:
    """Address-ish strings to try, best first."""
    out = []
    prop = (rec.get("property") or "").strip()
    if prop:
        out.append(prop)
    memo = (rec.get("memo") or "").strip()
    if memo:
        # take the part before a separator / account marker
        head = re.split(r"\s*[-–|]\s*|\ba/c\b|\bA/C\b|#", memo)[0].strip()
        if head and head != prop:
            out.append(head)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args()
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    m.ping()
    mr, ents = m.db["money_records"], m.db["entities"]
    prop_idx = build_prop_index(ents)
    logger.info(f"property index: {len(prop_idx)} keys")

    total = already = linked = no_text = no_match = coerced = 0
    ops = []
    miss = Counter()
    for r in mr.find({}, {"property_ids": 1, "property": 1, "memo": 1, "amount_value": 1}):
        total += 1
        upd = {}
        # numeric coercion
        fv = _to_float(r.get("amount_value"))
        if fv is not None and not isinstance(r.get("amount_value"), (int, float)):
            upd["amount_value"] = fv
            coerced += 1
        # linkage
        pids = r.get("property_ids") or []
        if pids:
            already += 1
        else:
            hit = None
            for a in candidate_addrs(r):
                ac = _acore(a)
                if ac and ac in prop_idx:
                    hit = prop_idx[ac]
                    break
            if hit:
                upd["property_ids"] = [hit]
                linked += 1
            elif not candidate_addrs(r):
                no_text += 1
            else:
                no_match += 1
                miss[_acore(candidate_addrs(r)[0])] += 1
        if upd:
            ops.append(UpdateOne({"_id": r["_id"]}, {"$set": upd}))

    logger.info(f"records={total} already_linked={already} NEW_linked={linked} "
                f"no_text={no_text} no_match={no_match} amount_coerced={coerced}")
    logger.info(f"top unmatched address-cores: {miss.most_common(15)}")

    if args.live and ops:
        for i in range(0, len(ops), 1000):
            mr.bulk_write(ops[i:i + 1000], ordered=False)
        logger.info(f"APPLIED {len(ops)} updates")
    else:
        logger.info(f"DRY-RUN: would apply {len(ops)} updates (use --live)")
    m.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
