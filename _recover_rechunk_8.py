"""Recover the 8 emails whose body was stored as byte-swapped UTF-16 (real
content is HTML that decodes to CJK mojibake). Reverse the swap, re-derive
clean body_text via the project's html cleaner, persist, then re-chunk those
emails (context summaries + Voyage embeddings) using the exact build pipeline.

Scoped strictly to emails detected as mojibake. body_text_raw/body_html are
overwritten with the RECOVERED versions (the prior values were corrupt)."""
from __future__ import annotations
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.cleaner import clean_email_body, html_to_text
from src.utils.logger import logger
from scripts.build_email_chunks_v2 import (
    VoyageEmbedder, ContextualSummarizer, _Flusher, _process_one_body,
    EMBEDDING_MODEL, CHUNK_SIZE_TOKENS, CHUNK_OVERLAP_TOKENS,
)


def cjk_ratio(t: str) -> float:
    if not t:
        return 0.0
    s = t[:400]
    return sum(1 for c in s if 0x3000 <= ord(c) <= 0x9FFF) / len(s)


def recover_html(mojibake: str) -> str:
    raw = mojibake.encode("utf-16-le", "ignore")
    for enc in ("cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("latin-1", "ignore")


def main() -> int:
    s = Settings.load()
    mongo = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    emails = mongo.db["emails"]
    chunks = mongo.db["email_chunks_v2"]
    embedder = VoyageEmbedder(api_key=s.voyage_api_key, model=EMBEDDING_MODEL)
    summarizer = ContextualSummarizer(api_key=s.anthropic_api_key,
                                      model="claude-sonnet-4-6")
    now = datetime.now(timezone.utc)
    try:
        mongo.ping()
        # detect mojibake emails
        targets = []
        for em in emails.find({}, {"body_text": 1}):
            if cjk_ratio(em.get("body_text") or "") > 0.3:
                targets.append(em["_id"])
        logger.info(f"mojibake emails detected: {len(targets)}")

        # ---- recover + persist clean bodies ----
        for eid in targets:
            em = emails.find_one({"_id": eid},
                                 {"body_html": 1, "body_text_raw": 1, "body_text": 1})
            src = em.get("body_html") or em.get("body_text_raw") or em.get("body_text") or ""
            rec_html = recover_html(src)
            raw_text = html_to_text(rec_html)
            clean = clean_email_body(raw_text, strip_quotes=True)
            emails.update_one({"_id": eid}, {"$set": {
                "body_html": rec_html,
                "body_text_raw": raw_text,
                "body_text": clean,
                "body_recovered_at": now,
                "body_recovery_method": "utf16le_byteswap_reverse_v1",
            }})
            logger.info(f"  recovered {eid}: html={len(rec_html)} clean_text={len(clean)}")

        # ---- re-chunk those emails ----
        flusher = _Flusher(chunks_col=chunks, embedder=embedder,
                           embedding_model=EMBEDDING_MODEL, batch_size=64, dry=False)
        written = 0
        for eid in targets:
            res = _process_one_body(
                eid, emails_col=emails, chunk_size=CHUNK_SIZE_TOKENS,
                chunk_overlap=CHUNK_OVERLAP_TOKENS, summarizer=summarizer)
            if not res or not res.get("docs"):
                logger.warning(f"  no chunks produced for {eid}")
                # still drop any stale garbage chunks for this email
                chunks.delete_many({"email_id": eid, "source_type": "email_body"})
                continue
            flusher.add_body_group(eid, res["docs"])
            flusher.flush(force=True)
            written += len(res["docs"])
            logger.info(f"  re-chunked {eid}: {len(res['docs'])} chunks")

        u = summarizer.usage_summary
        logger.info(f"DONE: recovered {len(targets)} emails, wrote {written} chunks; "
                    f"ctx_cost=${u['approx_cost_usd']:.2f}")
        # write the email-sha list so entity backfill can be scoped
        Path("_sha8.txt").write_text(
            "\n".join(f"email:{e}" for e in targets) + "\n", encoding="utf-8")
        return 0
    finally:
        mongo.close()


if __name__ == "__main__":
    raise SystemExit(main())
