"""
Ingest MangoTree partner/investor replies (Outlook `.msg`, `partners/` folder).

These are replies from MangoTree's own investor group to Rakesh's periodic
"MangoTree Litigation Update" partner letter. The letter itself goes out as a
Mailchimp bulk mailing (parent Message-ID @mail151.atl241.mcsv.net), which is
why the thread parent is absent from the Gmail-derived corpus — the replies
land in Rakesh's mailbox but the outbound blast never does.

Classification (differs from every other email path here, deliberately):

  * privilege_status=not_privileged — the senders are investors, not counsel
    and not the client. James Quinn says so in his own reply: "we are
    investors, not lawyers". The legal_correspondence corpus default is
    `privileged`; inheriting it would mislabel investor mail and overstate
    our privilege posture, so it is overridden explicitly.
  * is_ours=True, party_alignment=mangotree_partner — our own side.
  * content_kind=editorial_feedback — these are suggestions ON a draft letter,
    not assertions of fact. Where they restate figures ($1.4M escrow release,
    $100k adequate protection, $650k forfeited deposit, $15,995,000 asking
    price), they are quoting Rakesh's DRAFT, so `quotes_draft_letter=True`
    warns the agent not to cite them as settled facts.

Body handling: the standard cleaner runs with strip_quotes=True. Verified
against both files — it drops the quoted parent letter from James's reply
(his substance is the numbered paragraph suggestions) while preserving Alan
Someck's markup, which is interleaved inside a letter he pasted inline rather
than quoted. Raw bodies are retained in body_text_raw either way.

Usage:
    python -m scripts.ingest_partner_msg --dry-run
    python -m scripts.ingest_partner_msg --live
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from email import message_from_bytes
from email.utils import parseaddr
from pathlib import Path
from typing import Any, Dict, List, Optional

import extract_msg

from config.settings import Settings
from src.cleaner import clean_email_body, html_to_text
from src.db.mongo import MongoClientWrapper
from src.db.repository import EmailRepository
from src.rag import evidence_schema as ev
from src.utils.hashing import sha256_bytes, sha256_strings
from src.utils.logger import logger

from scripts.ingest_eml_folder import (
    _extract_attachments,
    _extract_bodies,
    _normalize_subject,
)

PARTNER_ROOT = Path("partners")
FOLDER_PATH = "MangoTree Partners"
ID_PREFIX = "partners:"
CUSTODIAN = "Rakesh Bhargava mailbox (rakesh@mtreh.com) — partner replies"


def _addr_from(value: Optional[str]) -> Dict[str, str]:
    name, email = parseaddr(value or "")
    return {"email": (email or "").strip().lower(), "name": (name or "").strip()}


def _addr_list_from(value: Optional[str]) -> List[Dict[str, str]]:
    """extract_msg exposes recipients as a single display string."""
    from email.utils import getaddresses

    out: List[Dict[str, str]] = []
    for name, email in getaddresses([value or ""]):
        email = (email or "").strip().lower()
        if email:
            out.append({"email": email, "name": (name or "").strip()})
    return out


def parse_msg_file(path: Path) -> Dict[str, Any]:
    """Parse a .msg, using its decoded headers but the reconstructed RFC822
    MIME tree for bodies/attachments (so the .eml path's part handling and
    signature-logo filtering apply unchanged)."""
    raw_file = path.read_bytes()
    msg = extract_msg.Message(str(path))
    try:
        # Headers: take extract_msg's decoded values. The RFC822 that
        # asEmailMessage() rebuilds re-encodes Subject/In-Reply-To as RFC2047,
        # which would leave mojibake in the subject and a mangled parent id.
        subject = (msg.subject or "").strip()
        sender = _addr_from(msg.sender)
        to = _addr_list_from(msg.to)
        cc = _addr_list_from(msg.cc)
        message_id = (getattr(msg, "messageId", None) or "").strip()
        in_reply_to = (getattr(msg, "inReplyTo", None) or "").strip() or None
        refs_raw = (getattr(msg, "references", None) or "").strip()
        references = refs_raw.split() if refs_raw else []

        date = msg.date
        if date is not None:
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            date = date.astimezone(timezone.utc)

        mime = message_from_bytes(msg.asEmailMessage().as_bytes())
        plain, html = _extract_bodies(mime)
        if not plain:
            plain = msg.body or ""
        attachments, skipped_logos = _extract_attachments(mime)
    finally:
        msg.close()

    body_source = plain or (html_to_text(html) if html else "")
    body_clean = clean_email_body(body_source, strip_quotes=True)

    return {
        "file_sha": sha256_bytes(raw_file),
        "rel_path": str(Path(PARTNER_ROOT.name) / path.name),
        "message_id": message_id,
        "in_reply_to": in_reply_to,
        "references": references,
        "subject": subject,
        "subject_normalized": _normalize_subject(subject),
        "from": sender,
        "to": to,
        "cc": cc,
        "date": date,
        "body_text_raw": plain,
        "body_html": html,
        "body_text": body_clean,
        "attachments": attachments,
        "skipped_logos": skipped_logos,
    }


def build_email_doc(parsed: Dict[str, Any], run_id, max_body_chars: int) -> dict:
    body_clean = parsed["body_text"]
    body_raw = parsed["body_text_raw"]
    body_html = parsed["body_html"]
    if len(body_clean) > max_body_chars:
        body_clean = body_clean[:max_body_chars] + "\n…[truncated]"
    if len(body_raw) > max_body_chars:
        body_raw = body_raw[:max_body_chars] + "\n…[truncated]"
    if len(body_html) > max_body_chars:
        body_html = body_html[:max_body_chars] + "\n<!-- truncated -->"

    content_hash = sha256_strings([
        parsed["from"].get("email", "") or parsed["from"].get("name", ""),
        ",".join(a.get("email", "") for a in parsed["to"]),
        parsed["subject_normalized"],
        (parsed["date"].isoformat() if parsed["date"] else ""),
        body_clean[:5000],
    ])

    base = parsed["message_id"] or ("path:" + parsed["rel_path"])
    pst_entry_id = ID_PREFIX + base

    # Mailchimp stamps a per-recipient Message-ID on the outbound letter, so
    # In-Reply-To/References differ for every partner and would scatter the
    # replies into singleton threads. Group on the normalized subject instead
    # so all feedback on one letter reads as one conversation.
    thread_id = ("subj:" + parsed["subject_normalized"][:120]
                 if parsed["subject_normalized"]
                 else (parsed["in_reply_to"] or parsed["message_id"]))

    d = parsed["date"]
    evidence = ev.evidentiary_fields(
        corpus=ev.CORPUS_LEGAL_CORRESPONDENCE,
        source_file=parsed["rel_path"],
        sha256=parsed["file_sha"],
        ingest_run_id=str(run_id),
        custodian=CUSTODIAN,
        privilege_status=ev.PRIVILEGE_NOT_PRIVILEGED,
        evidentiary_class=ev.EVID_CORRESPONDENCE,
    )

    return {
        "pst_entry_id": pst_entry_id,
        "internet_message_id": parsed["message_id"] or None,
        "content_hash": content_hash,

        "subject": parsed["subject"],
        "subject_normalized": parsed["subject_normalized"],

        "from": parsed["from"],
        "to": parsed["to"],
        "cc": parsed["cc"],
        "bcc": [],
        "reply_to": [],

        "date": d,
        "date_sent": d,
        "date_received": d,
        "date_modified": None,
        "date_year": d.year if d else None,
        "date_month": d.month if d else None,
        "date_day": d.day if d else None,
        "date_ym": f"{d.year:04d}-{d.month:02d}" if d else None,
        "date_ymd": f"{d.year:04d}-{d.month:02d}-{d.day:02d}" if d else None,
        "date_weekday": d.strftime("%A") if d else None,

        "body_text": body_clean,
        "body_text_raw": body_raw,
        "body_html": body_html,
        "body_format": "plain" if parsed["body_text_raw"] else "html",

        "has_attachments": bool(parsed["attachments"]),
        "attachment_count": len(parsed["attachments"]),
        "attachment_ids": [],

        "in_reply_to": parsed["in_reply_to"],
        "references": parsed["references"],
        "thread_id": thread_id,
        "conversation_topic": parsed["subject_normalized"],

        "folder_path": FOLDER_PATH,
        "gmail_labels": ["MangoTree Partners"],
        "importance": None,
        "size_bytes": (len(body_raw) + len(body_html)) if (body_raw or body_html) else 0,
        "headers_raw": {},

        # ---- Partner-specific classification (see module docstring) ----
        "is_ours": True,
        "party_alignment": "mangotree_partner",
        "sender_role": "investor_partner",
        "adverse_source": False,
        "contains_allegations": False,
        "content_kind": "editorial_feedback",
        "quotes_draft_letter": True,
        "doc_source_type": "email_body",
        "instrument_subtype": "partner_correspondence",
        "thread_parent_present": False,

        "source": {
            "origin": "partner_msg_folder",
            "root": PARTNER_ROOT.name,
            "rel_path": parsed["rel_path"],
            "file_sha256": parsed["file_sha"],
        },
        "ingested_at": datetime.now(timezone.utc),
        "ingestion_run_id": run_id,

        **evidence,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Ingest MangoTree partner .msg replies.")
    ap.add_argument("--root", default=str(PARTNER_ROOT))
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--live", dest="dry_run", action="store_false")
    args = ap.parse_args()

    root = Path(args.root)
    files = sorted(root.glob("*.msg"))
    if not files:
        logger.error(f"No .msg files under {root}")
        return 2

    logger.info(f"{len(files)} partner .msg "
                f"({'DRY RUN' if args.dry_run else 'LIVE — writing to MongoDB'})")

    settings = Settings.load()
    mongo: Optional[MongoClientWrapper] = None
    repo: Optional[EmailRepository] = None
    run_id: Any = "dry-run"
    existing: set[str] = set()

    if not args.dry_run:
        mongo = MongoClientWrapper(settings.mongo_uri, settings.mongo_db_name)
        mongo.ping()
        repo = EmailRepository(mongo)
        run_id = repo.start_run(pst_meta={
            "path": str(root.resolve()), "name": "MangoTree Partners",
            "origin": "partner_msg_folder", "corpus": ev.CORPUS_LEGAL_CORRESPONDENCE,
        })
        existing = {
            doc["pst_entry_id"]
            for doc in mongo.emails.find(
                {"pst_entry_id": {"$regex": f"^{ID_PREFIX}"}},
                {"pst_entry_id": 1, "_id": 0})
        }
        logger.info(f"{len(existing)} partner emails already ingested — will skip those")

    totals = {"seen": 0, "inserted": 0, "skipped_existing": 0,
              "attachments_stored": 0, "logos_skipped": 0, "errors": 0}

    for path in files:
        totals["seen"] += 1
        try:
            parsed = parse_msg_file(path)
        except Exception as exc:  # noqa: BLE001
            totals["errors"] += 1
            logger.warning(f"parse failed {path.name}: {exc}")
            continue

        totals["logos_skipped"] += parsed["skipped_logos"]
        doc = build_email_doc(parsed, run_id, settings.max_body_chars)

        logger.info(
            f"  {path.name[:44]:46s}\n"
            f"      from={doc['from']['name']} <{doc['from']['email']}>  "
            f"date={doc['date']}\n"
            f"      subj={doc['subject'][:70]!r}\n"
            f"      privilege={doc['privilege_status']}  corpus={doc['corpus']}  "
            f"is_ours={doc['is_ours']}  align={doc['party_alignment']}\n"
            f"      body_clean={len(doc['body_text']):,}  raw={len(doc['body_text_raw']):,}  "
            f"att={doc['attachment_count']}  logos_skipped={parsed['skipped_logos']}\n"
            f"      thread_id={str(doc['thread_id'])[:60]}"
        )

        if args.dry_run:
            continue
        if doc["pst_entry_id"] in existing:
            totals["skipped_existing"] += 1
            logger.info("      -> already ingested, skipping")
            continue

        id_map = repo.upsert_emails([doc])  # type: ignore[union-attr]
        email_id = id_map.get(doc["pst_entry_id"])
        totals["inserted"] += 1

        att_ids = []
        for att in parsed["attachments"]:
            if att.size_bytes > settings.attachment_max_bytes:
                logger.warning(f"skip oversize {att.filename} ({att.size_bytes:,}B)")
                continue
            aid = repo.store_attachment(  # type: ignore[union-attr]
                email_id=email_id, email_pst_entry_id=doc["pst_entry_id"],
                filename=att.filename, display_name=att.filename,
                content_type=att.content_type, data=att.data,
                sha256=sha256_bytes(att.data), is_inline=att.is_inline,
                content_id=att.content_id)
            att_ids.append(aid)
            totals["attachments_stored"] += 1
        if att_ids:
            repo.link_attachments_to_email(email_id, att_ids)  # type: ignore[union-attr]
        existing.add(doc["pst_entry_id"])
        logger.info(f"      -> inserted _id={email_id}")

    if not args.dry_run and repo is not None:
        try:
            repo.upsert_folder(FOLDER_PATH)
        except Exception:  # noqa: BLE001
            pass
        repo.finish_run(run_id, totals, status="completed")
        if mongo is not None:
            mongo.close()

    logger.info(f"DONE. totals={totals}")
    if args.dry_run:
        logger.info("DRY RUN — re-run with --live to store.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
