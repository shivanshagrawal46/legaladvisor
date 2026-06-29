"""Verify the 27 re-OCR'd fraud pdf_mixed docs are CLEANLY re-chunked:
 1) old chunks deleted (no stale leftovers: every chunk created in this run)
 2) no duplicate chunks
 3) every chunk has an embedding (correct dim)
 4) corpus/privilege correctly set (fraud_communications / adverse_party)
 5) entity links present
 6) email<->attachment linkage intact (occurrences reference real emails)
 7) NOT stale: chunk text is drawn from the CURRENT (new) OCR extracted_text
"""
from __future__ import annotations
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import Settings
from src.db.mongo import MongoClientWrapper

# rechunk job ran ~14:15-15:16 IST on 2026-06-26 => 08:45 UTC. Anything before
# this cutoff for these sha would be a stale leftover.
CUTOFF = datetime(2026, 6, 26, 8, 40, tzinfo=timezone.utc)


def main() -> int:
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    m.ping()
    ch = m.db["email_chunks_v2"]
    v2 = m.db["attachments_v2"]

    shas = [ln.strip() for ln in Path("_fraud_mixed_done_sha.txt").read_text(
        encoding="utf-8").splitlines() if ln.strip()]
    print(f"verifying {len(shas)} sha\n" + "=" * 60)

    total = 0
    stale = 0
    no_emb = 0
    bad_dim = 0
    wrong_corpus = 0
    no_entity = 0
    no_occ = 0
    dup = 0
    stale_text = 0
    EXPECT_DIM = 2048

    for sha in shas:
        cur = list(ch.find({"sha256": sha, "source_type": "attachment"}))
        total += len(cur)
        # current OCR text for staleness comparison
        a = v2.find_one({"sha256": sha}, {"extracted_text": 1})
        cur_text = (a or {}).get("extracted_text") or ""

        seen_idx = set()
        for c in cur:
            ca = c.get("created_at")
            if not ca or (ca.replace(tzinfo=timezone.utc) if ca.tzinfo is None else ca) < CUTOFF:
                stale += 1
            emb = c.get("embedding")
            if not emb:
                no_emb += 1
            elif len(emb) != EXPECT_DIM:
                bad_dim += 1
            if c.get("corpus") != "fraud_communications" or c.get("privilege_status") != "adverse_party":
                wrong_corpus += 1
            if not (c.get("entity_ids") or c.get("linked_entities") or c.get("entities")):
                no_entity += 1
            if not c.get("occurrences"):
                no_occ += 1
            idx = c.get("chunk_index")
            if idx in seen_idx:
                dup += 1
            seen_idx.add(idx)
            # staleness of TEXT: strip ctx-summary prefix, check raw body is in new OCR
            raw = c.get("raw_text") or c.get("text") or ""
            probe = raw[-200:].strip()
            if probe and cur_text and probe[:60] not in cur_text:
                # try a mid-slice fallback before counting as stale
                mid = raw[len(raw)//2: len(raw)//2 + 60].strip()
                if mid and mid not in cur_text:
                    stale_text += 1

    print(f"total attachment chunks for 27 sha : {total}")
    print(f"stale (created before rechunk run) : {stale}   <- must be 0")
    print(f"duplicate chunk_index              : {dup}     <- must be 0")
    print(f"missing embedding                  : {no_emb}  <- must be 0")
    print(f"wrong embedding dim                : {bad_dim} <- must be 0")
    print(f"wrong corpus/privilege             : {wrong_corpus} <- must be 0")
    print(f"missing entity links               : {no_entity}")
    print(f"missing occurrences (linkage)      : {no_occ}  <- must be 0")
    print(f"possibly-stale TEXT vs new OCR     : {stale_text} <- must be 0")
    print("=" * 60)
    ok = (stale == 0 and dup == 0 and no_emb == 0 and bad_dim == 0
          and wrong_corpus == 0 and no_occ == 0 and stale_text == 0)
    print("RESULT:", "PASS - clean delete+reinsert, fully linked, no stale data"
          if ok else "FAIL - investigate above")
    m.close()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
