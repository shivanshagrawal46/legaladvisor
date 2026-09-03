"""Entity-link every chunk that has not been through the backfill yet.

Why this exists rather than `backfill_chunk_entities.py --sha-file`:
that script scopes with {"sha256": {"$in": shas}}, but `_boris_enrich.py`
emits `email:<id>` keys for email bodies, which carry no sha256 field. Those
keys silently match nothing, so body chunks never get linked on a scoped run.

Scoping on the absence of `entity_backfill_at` — the marker the backfill
itself writes — covers bodies and attachments alike and is naturally
idempotent: once linked, a chunk drops out of scope.

Matching logic (alias index, address-core index, bucketing, touches_david)
is imported from backfill_chunk_entities so both paths stay identical.

Usage:
    python -m scripts.link_new_chunks            # dry run
    python -m scripts.link_new_chunks --apply
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from typing import Dict, List, Set

from pymongo import UpdateOne

from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.utils.logger import logger
from scripts.backfill_chunk_entities import (
    build_alias_index,
    build_addr_index,
    addr_hits,
)

CHUNKS = "email_chunks_v2"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Write the links.")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    ents, chunks = m.db["entities"], m.db[CHUNKS]

    kind_of = {e["_id"]: e.get("kind") for e in ents.find({}, {"kind": 1})}
    side_of = {e["_id"]: e.get("side") for e in ents.find({}, {"side": 1})}
    david_ids = {e["_id"] for e in ents.find({"is_david": True}, {"_id": 1})}

    idx = build_alias_index(ents)
    aidx = build_addr_index(ents)
    phrases = sorted(idx.keys(), key=len, reverse=True)
    big = re.compile(r"(?<![a-z0-9])(" +
                     "|".join(re.escape(p) for p in phrases) +
                     r")(?![a-z0-9])", re.IGNORECASE)
    logger.info(f"alias index: {len(phrases)} phrases over {len(kind_of)} entities")

    scope = {"entity_backfill_at": {"$exists": False}}
    total = chunks.count_documents(scope)
    logger.info(f"chunks awaiting entity linkage: {total:,}")
    if total == 0:
        m.close()
        return 0

    cur = chunks.find(scope, {"_id": 1, "text": 1, "body": 1, "entity_refs": 1,
                              "source_type": 1, "sha256": 1, "email_id": 1,
                              "primary_property_id": 1})
    if args.limit:
        cur = cur.limit(args.limit)

    ops: List[UpdateOne] = []
    n = n_linked = 0
    by_type: Dict[str, int] = {}
    for ch in cur:
        n += 1
        st = ch.get("source_type") or "?"
        text = ((ch.get("body") or "") + " " + (ch.get("text") or "")).lower()
        hits: Set[str] = set()
        for tok in big.findall(text):
            hits |= idx.get(tok.strip().lower(), set())
        hits |= addr_hits(text, aidx)

        existing = ch.get("entity_refs") or {}
        buckets: Dict[str, Set[str]] = {
            "people": set(existing.get("people") or []),
            "llcs": set(existing.get("llcs") or []),
            "orgs": set(existing.get("orgs") or []),
            "properties": set(existing.get("properties") or []),
            "cases": set(existing.get("cases") or []),
        }
        for eid in hits:
            k = kind_of.get(eid)
            if k == "person":
                buckets["people"].add(eid)
            elif k == "llc":
                buckets["llcs"].add(eid)
            elif k == "org":
                buckets["orgs"].add(eid)
            elif k == "property":
                buckets["properties"].add(eid)
            elif k == "case":
                buckets["cases"].add(eid)

        all_ids = set().union(*buckets.values())
        if all_ids:
            n_linked += 1
            by_type[st] = by_type.get(st, 0) + 1
        refs = {k: sorted(v) for k, v in buckets.items()}

        ops.append(UpdateOne({"_id": ch["_id"]}, {"$set": {
            "entity_refs": refs,
            "entity_ids": sorted(all_ids),
            "primary_property_id": (refs["properties"][0] if refs["properties"]
                                    else ch.get("primary_property_id")),
            "touches_david": bool(all_ids & david_ids),
            "entity_sides": sorted({side_of.get(e) for e in all_ids if side_of.get(e)}),
            "entity_backfill_at": now,
        }}))
        if args.apply and len(ops) >= 500:
            chunks.bulk_write(ops, ordered=False)
            ops = []
            logger.info(f"  ...{n}/{total} processed, {n_linked} linked")

    if args.apply and ops:
        chunks.bulk_write(ops, ordered=False)

    logger.info(f"processed={n}  linked_to_>=1_entity={n_linked} "
                f"({100 * n_linked / max(n, 1):.1f}%)  by_source_type={by_type}")
    if not args.apply:
        logger.info("DRY RUN — re-run with --apply to write.")
    m.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
