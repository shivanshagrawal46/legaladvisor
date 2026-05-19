"""
Phase 1 entry point: extract everything from the PST file into MongoDB.

Usage:
    python ingest.py
    python ingest.py --dry-run            # parse PST without writing to Mongo
    python ingest.py --limit 50           # process only first 50 messages (testing)
    python ingest.py --reset              # drop emails / attachments / GridFS first

Reads configuration from .env (see .env.example).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow `python ingest.py` from project root
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.parser.pst_parser import PSTParser
from src.pipeline.ingestion import IngestionPipeline
from src.utils.logger import configure_logger, logger


def _reset_collections(mongo: MongoClientWrapper) -> None:
    logger.warning("--reset flag: dropping emails, attachments, folders, GridFS bucket")
    mongo.emails.drop()
    mongo.attachments.drop()
    mongo.folders.drop()
    for coll in ("attachment_files.files", "attachment_files.chunks"):
        try:
            mongo.db[coll].drop()
        except Exception:
            pass


def _dry_run(settings: Settings, limit: int | None) -> None:
    logger.info("DRY-RUN: parsing PST without touching MongoDB")
    with PSTParser(settings.pst_file_path) as parser:
        seen = 0
        with_attach = 0
        attach_total = 0
        for parsed in parser.iter_parsed():
            seen += 1
            if parsed.attachments:
                with_attach += 1
                attach_total += len(parsed.attachments)
            if seen <= 3:
                logger.info(
                    f"[{seen}] {parsed.folder_path} | from={parsed.sender.get('email')} "
                    f"| subj={parsed.subject[:80]!r} | atts={len(parsed.attachments)}"
                )
            if limit and seen >= limit:
                break
    logger.info(f"DRY-RUN complete: {seen} messages, {with_attach} with attachments, {attach_total} attachments total")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest a PST file into MongoDB.")
    parser.add_argument("--dry-run", action="store_true", help="Parse without writing to Mongo")
    parser.add_argument("--reset", action="store_true", help="Drop existing collections first")
    parser.add_argument("--limit", type=int, default=None, help="Process only first N messages (dry-run only)")
    args = parser.parse_args()

    try:
        settings = Settings.load()
    except RuntimeError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        print("Hint: copy .env.example to .env and fill in your values.", file=sys.stderr)
        return 2

    configure_logger(settings.logs_dir)
    logger.info(f"PST file: {settings.pst_file_path}")
    logger.info(f"Mongo DB: {settings.mongo_db_name}")

    if args.dry_run:
        _dry_run(settings, args.limit)
        return 0

    mongo = MongoClientWrapper(settings.mongo_uri, settings.mongo_db_name)
    try:
        mongo.ping()
        if args.reset:
            _reset_collections(mongo)
        mongo.ensure_indexes()

        pipeline = IngestionPipeline(settings, mongo)
        result = pipeline.run()
        logger.info(f"Done. {result}")
        return 0 if result["status"] == "completed" else 1
    finally:
        mongo.close()


if __name__ == "__main__":
    raise SystemExit(main())
