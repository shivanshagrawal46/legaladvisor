#!/usr/bin/env python3
"""
mbox_extract.py — Stream-extract a huge Gmail Takeout .mbox.

Built for 80GB+ mboxes. Features:
  - Streaming parser           -> constant memory
  - Resumable                  -> survives crashes / Ctrl+C
  - Smart Gmail label routing  -> custom labels become folders
  - YYYY-MM subfolders         -> avoids 1M files in one dir
  - Master CSV index           -> every header field, every attachment
  - Saves full .eml + extracted original attachments

USAGE:
  python mbox_extract.py "C:\\path\\to\\All mail Including Spam and Trash.mbox" -o "D:\\gmail_out"
  python mbox_extract.py "C:\\path\\to\\folder_with_mbox_files"               -o "D:\\gmail_out"

RESUME after crash / Ctrl+C:
  python mbox_extract.py <same input> -o <same output> --resume
"""

import argparse
import csv
import hashlib
import json
import re
import sys
import time
from email import message_from_bytes
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime
from pathlib import Path

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False


# ---------- Gmail label intelligence ---------- #

GMAIL_SYSTEM_LABELS = {
    "Inbox", "Sent", "Drafts", "Trash", "Spam", "Starred",
    "Important", "Unread", "Opened", "Archived", "Chat",
    "Category Personal", "Category Social", "Category Promotions",
    "Category Updates", "Category Forums",
    "IMAP_Sent", "IMAP_Drafts", "IMAP_Trash",
}
SYSTEM_PRIORITY = ["Inbox", "Sent", "Drafts", "Starred", "Important", "Trash", "Spam", "Chat"]

SAFE_CHARS = re.compile(r"[^\w\-. ]+", re.UNICODE)
MAX_NAME_LEN = 60

CSV_FIELDS = [
    "id", "folder", "all_labels", "date_raw", "date_parsed",
    "from", "to", "cc", "bcc", "subject", "message_id",
    "has_attachments", "attachment_count", "attachment_names",
    "size_bytes", "eml_path", "byte_offset",
]


# ---------- Helpers ---------- #

def sanitize(name: str, fallback: str = "untitled") -> str:
    if not name:
        return fallback
    if "=?" in name:
        try:
            name = str(make_header(decode_header(name)))
        except Exception:
            pass
    name = SAFE_CHARS.sub("_", name).strip("._ ")
    name = re.sub(r"\s+", "_", name)
    return (name[:MAX_NAME_LEN] or fallback)


def decode_field(raw) -> str:
    if raw is None:
        return ""
    try:
        return str(make_header(decode_header(str(raw))))
    except Exception:
        return str(raw)


def parse_date(msg):
    raw = msg.get("Date") or ""
    if not raw:
        return "", "", ""
    try:
        dt = parsedate_to_datetime(raw)
        if dt is None:
            return raw, "", ""
        return raw, dt.strftime("%Y-%m-%d"), dt.strftime("%Y-%m")
    except Exception:
        return raw, "", ""


def pick_folder(labels_str: str) -> str:
    if not labels_str:
        return "_no_label"
    labels = [l.strip() for l in labels_str.split(",") if l.strip()]
    user_labels = [l for l in labels if l not in GMAIL_SYSTEM_LABELS]
    if user_labels:
        return sanitize(user_labels[0])
    for sys_lbl in SYSTEM_PRIORITY:
        if sys_lbl in labels:
            return sanitize(sys_lbl)
    return sanitize(labels[0]) if labels else "_no_label"


# ---------- Streaming mbox reader ---------- #

def stream_messages(path: Path, start_offset: int = 0):
    """
    Yield (raw_bytes, msg_start_offset, next_msg_offset).
    Memory: constant. Splits on lines starting with b'From '.
    """
    with open(path, "rb", buffering=4 * 1024 * 1024) as f:
        f.seek(start_offset)
        buf = []
        msg_start = start_offset
        while True:
            line_start = f.tell()
            line = f.readline()
            if not line:
                break
            if line.startswith(b"From "):
                if buf:
                    yield b"".join(buf), msg_start, line_start
                msg_start = line_start
                buf = [line]
            else:
                buf.append(line)
        if buf:
            yield b"".join(buf), msg_start, f.tell()


# ---------- Per-message processing ---------- #

EXT_FROM_CTYPE = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
    "image/webp": ".webp", "image/bmp": ".bmp", "image/tiff": ".tif",
    "application/pdf": ".pdf",
    "text/plain": ".txt", "text/html": ".html", "text/csv": ".csv",
    "application/zip": ".zip", "application/x-rar-compressed": ".rar",
    "application/json": ".json", "application/xml": ".xml",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "audio/mpeg": ".mp3", "video/mp4": ".mp4",
}


def extract_attachments(msg, attach_dir: Path, err_log) -> list:
    saved = []
    for part in msg.walk():
        if part.is_multipart():
            continue
        disp = (part.get("Content-Disposition") or "").lower()
        filename = part.get_filename()
        if not filename and "attachment" not in disp:
            continue
        if not filename:
            filename = f"part_{len(saved)+1}"
        fname = sanitize(decode_field(filename), f"attachment_{len(saved)+1}")
        if "." not in fname:
            ctype = (part.get_content_type() or "").lower()
            fname += EXT_FROM_CTYPE.get(ctype, "")

        attach_dir.mkdir(parents=True, exist_ok=True)
        target = attach_dir / fname
        stem, suffix = target.stem, target.suffix
        n = 1
        while target.exists():
            target = attach_dir / f"{stem}_{n}{suffix}"
            n += 1
        try:
            payload = part.get_payload(decode=True)
            if payload is not None:
                with open(target, "wb") as af:
                    af.write(payload)
                saved.append(target.name)
        except Exception as e:
            err_log.write(f"attachment_fail\t{fname}\t{e}\n")
    return saved


def process_message(raw_bytes: bytes, offset: int, idx: int, out_root: Path, err_log):
    try:
        msg = message_from_bytes(raw_bytes)
    except Exception as e:
        err_log.write(f"parse_fail\toffset={offset}\t{e}\n")
        return None

    labels = msg.get("X-Gmail-Labels", "")
    folder = pick_folder(labels)
    date_raw, date_str, ym = parse_date(msg)
    subject = decode_field(msg.get("Subject"))
    msg_id = decode_field(msg.get("Message-ID")) or f"noid-{offset}"

    h = hashlib.sha1(msg_id.encode("utf-8", "ignore")).hexdigest()[:8]
    base = f"{idx:07d}__{date_str or 'nodate'}__{sanitize(subject, 'no_subject')}__{h}"

    folder_dir = out_root / folder / (ym or "_undated")
    folder_dir.mkdir(parents=True, exist_ok=True)

    eml_path = folder_dir / f"{base}.eml"
    with open(eml_path, "wb") as f:
        f.write(raw_bytes)

    saved_atts = extract_attachments(msg, folder_dir / base, err_log)

    return {
        "id": idx,
        "folder": folder,
        "all_labels": labels,
        "date_raw": date_raw,
        "date_parsed": date_str,
        "from": decode_field(msg.get("From")),
        "to": decode_field(msg.get("To")),
        "cc": decode_field(msg.get("Cc")),
        "bcc": decode_field(msg.get("Bcc")),
        "subject": subject,
        "message_id": msg_id,
        "has_attachments": bool(saved_atts),
        "attachment_count": len(saved_atts),
        "attachment_names": " | ".join(saved_atts),
        "size_bytes": len(raw_bytes),
        "eml_path": str(eml_path.relative_to(out_root)),
        "byte_offset": offset,
    }


# ---------- Resume state ---------- #

def load_state(state_path: Path):
    if not state_path.exists():
        return set(), 0, 0
    processed = set()
    max_next = 0
    max_idx = 0
    with open(state_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                processed.add(obj["id"])
                max_next = max(max_next, int(obj.get("next_offset", 0)))
                max_idx = max(max_idx, int(obj.get("idx", 0)))
            except Exception:
                continue
    return processed, max_next, max_idx


def append_state(fp, msg_id: str, msg_start: int, next_offset: int, idx: int):
    fp.write(json.dumps({
        "id": msg_id, "msg_start": msg_start,
        "next_offset": next_offset, "idx": idx,
    }) + "\n")
    fp.flush()


# ---------- Input discovery ---------- #

def iter_inputs(input_path: Path):
    if input_path.is_file() and input_path.suffix.lower() == ".mbox":
        yield input_path
    elif input_path.is_dir():
        for p in sorted(input_path.rglob("*.mbox")):
            yield p
    else:
        raise SystemExit(f"Input must be a .mbox file or a folder with .mbox files: {input_path}")


# ---------- Main ---------- #

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="Path to a .mbox file OR a folder containing .mbox files")
    ap.add_argument("-o", "--output", default="output", help="Output directory")
    ap.add_argument("--resume", action="store_true", help="Resume from previous state")
    args = ap.parse_args()

    in_path = Path(args.input).expanduser().resolve()
    out_root = Path(args.output).expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    state_path = out_root / "_state.jsonl"
    index_path = out_root / "_index.csv"
    err_path = out_root / "_errors.log"

    processed_ids, resume_offset, last_idx = (set(), 0, 0)
    if args.resume:
        processed_ids, resume_offset, last_idx = load_state(state_path)
        print(f"[resume] {len(processed_ids):,} done, last offset={resume_offset:,}, idx={last_idx}")

    inputs = list(iter_inputs(in_path))
    print(f"[inputs] {len(inputs)} mbox file(s)")
    for p in inputs:
        print(f"   - {p}  ({p.stat().st_size / (1024**3):.2f} GB)")
    print(f"[output] {out_root}")

    csv_mode = "a" if (args.resume and index_path.exists()) else "w"
    cf = open(index_path, csv_mode, newline="", encoding="utf-8")
    writer = csv.DictWriter(cf, fieldnames=CSV_FIELDS)
    if csv_mode == "w":
        writer.writeheader()

    err_log = open(err_path, "a", encoding="utf-8")
    state_fp = open(state_path, "a", encoding="utf-8")

    idx = last_idx
    t0 = time.time()
    bytes_seen = 0
    skipped = 0

    try:
        for mbox_path in inputs:
            total_size = mbox_path.stat().st_size
            # Only the first input uses the resume_offset; later files start at 0.
            start = resume_offset if (mbox_path == inputs[0]) else 0
            resume_offset = 0  # don't reuse for next files

            print(f"\n[reading] {mbox_path.name}")
            pbar = None
            if HAS_TQDM:
                pbar = tqdm(total=total_size, initial=start, unit="B",
                            unit_scale=True, desc=mbox_path.name[:30])

            last_report = start
            for raw, msg_start, next_off in stream_messages(mbox_path, start_offset=start):
                if pbar:
                    pbar.update(msg_start - last_report)
                    last_report = msg_start

                # cheap duplicate check via Message-ID
                try:
                    head_end = raw.find(b"\r\n\r\n")
                    if head_end == -1:
                        head_end = raw.find(b"\n\n")
                    headers_only = raw[: head_end if head_end != -1 else 4096]
                    msg = message_from_bytes(headers_only)
                    mid = decode_field(msg.get("Message-ID"))
                    if mid and mid in processed_ids:
                        skipped += 1
                        continue
                except Exception:
                    pass

                idx += 1
                row = process_message(raw, msg_start, idx, out_root, err_log)
                if row:
                    writer.writerow(row)
                    cf.flush()
                    append_state(state_fp, row["message_id"], msg_start, next_off, idx)
                    processed_ids.add(row["message_id"])
                bytes_seen = next_off

            if pbar:
                pbar.update(total_size - last_report)
                pbar.close()
    except KeyboardInterrupt:
        print("\n[interrupted] state saved. Re-run with --resume to continue.")
    finally:
        cf.close()
        err_log.close()
        state_fp.close()

    dt = time.time() - t0
    print(f"\n[done] {idx:,} emails | {skipped:,} skipped (already done)")
    print(f"       elapsed: {dt/60:.1f} min")
    print(f"       index:  {index_path}")
    print(f"       errors: {err_path}")


if __name__ == "__main__":
    main()
