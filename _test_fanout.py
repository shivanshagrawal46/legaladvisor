"""Verify entity fan-out: a plain property question reaches EVERY source type."""
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.graph.fanout import EntityIndex, fan_out_chunks, source_type_breakdown

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
ents, chunks = m.db["entities"], m.db["email_chunks_v2"]
idx = EntityIndex(ents)
print("entities indexed:", len(idx.by_id), "| name phrases:", len(idx.phrase_to_ids),
      "| address keys:", len(idx.addr_to_ids))

# pick a David property that has title+insurance+equity to test fan-out
prop = ents.find_one({"kind": "property", "has_title": True, "has_insurance": True,
                      "is_david": True}, {"_id": 1, "canonical_address": 1})
print("\ntest property:", prop)

for q in ["what is the full story on 520 East 81st?",
          (prop or {}).get("canonical_address") or "227 West Neck Road",
          "anything about IPA Asset Management?"]:
    res = idx.resolve(q)
    ch = fan_out_chunks(chunks, res["all"], limit=300)
    print(f"\nQUERY: {q!r}")
    print(f"  resolved entities: {len(res['all'])} "
          f"(props={len(res['properties'])} people={len(res['people'])} llcs={len(res['llcs'])})")
    print(f"  fan-out chunks: {len(ch)}  by source: {source_type_breakdown(ch)}")
m.close()
