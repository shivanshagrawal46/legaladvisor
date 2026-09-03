"""Entity-link ONLY the partner chunks.

backfill_chunk_entities.py can only be scoped by --sha-file, which keys on the
chunk `sha256` field that email bodies do not carry; running it unscoped would
re-link the whole corpus. This reuses its alias/address index and the identical
match -> bucket -> update logic, restricted to the partner email chunks.
"""
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Set

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pymongo import UpdateOne

from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from scripts.backfill_chunk_entities import build_alias_index, build_addr_index, addr_hits

APPLY = "--apply" in sys.argv

now = datetime.now(timezone.utc)
s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
ents, chunks, em = m.db["entities"], m.db["email_chunks_v2"], m.db["emails"]

kind_of = {e["_id"]: e.get("kind") for e in ents.find({}, {"kind": 1})}
side_of = {e["_id"]: e.get("side") for e in ents.find({}, {"side": 1})}
name_of = {e["_id"]: e.get("canonical_name") for e in ents.find({}, {"canonical_name": 1})}
david_ids = {e["_id"] for e in ents.find({"is_david": True}, {"_id": 1})}

idx = build_alias_index(ents)
aidx = build_addr_index(ents)
phrases = sorted(idx.keys(), key=len, reverse=True)
big = re.compile(r"(?<![a-z0-9])(" + "|".join(re.escape(p) for p in phrases) +
                 r")(?![a-z0-9])", re.IGNORECASE)
print(f"alias index: {len(phrases)} phrases over {len(kind_of)} entities")

ids = [d["_id"] for d in em.find({"pst_entry_id": {"$regex": "^partners:"}}, {"_id": 1})]
ops = []
for ch in chunks.find({"email_id": {"$in": ids}, "source_type": "email_body"},
                      {"_id": 1, "text": 1, "body": 1, "entity_refs": 1,
                       "from_email": 1, "primary_property_id": 1}):
    text = ((ch.get("body") or "") + " " + (ch.get("text") or "")).lower()
    hits: Set[str] = set()
    for mtok in big.findall(text):
        hits |= idx.get(mtok.strip().lower(), set())
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
    refs = {k: sorted(v) for k, v in buckets.items()}
    print(f"\n  {ch.get('from_email')}  -> {len(all_ids)} entities")
    for k, v in refs.items():
        if v:
            print(f"     {k:11s}: " + ", ".join(str(name_of.get(e, e))[:34] for e in v))

    ops.append(UpdateOne({"_id": ch["_id"]}, {"$set": {
        "entity_refs": refs,
        "entity_ids": sorted(all_ids),
        "primary_property_id": (refs["properties"][0] if refs["properties"]
                                else ch.get("primary_property_id")),
        "touches_david": bool(all_ids & david_ids),
        "entity_sides": sorted({side_of.get(e) for e in all_ids if side_of.get(e)}),
        "entity_backfill_at": now,
    }}))

if APPLY and ops:
    r = chunks.bulk_write(ops, ordered=False)
    print(f"\nlinked {r.modified_count} chunks")
else:
    print("\nDRY — pass --apply to write.")
m.close()
