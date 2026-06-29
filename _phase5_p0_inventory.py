"""PHASE 5 - P0 inventory, hashing & dedup map (READ-ONLY).

Walks the 4 matter folders, EXCLUDES emails (.msg/.eml) and PST, SHA-256 hashes
every in-scope document, dedups internally, and cross-checks each hash against
what is ALREADY in the database (attachments_v2 + email_chunks_v2 + documents).
Writes a manifest (_phase5_manifest.json) + prints a human report.

Rules honored:
  - emails (.msg/.eml) and .pst are EXCLUDED by type, everywhere.
  - dedup is by EXACT content (sha256) only; every occurrence/path is recorded.
  - archives (.zip/.rar) are flagged separately (unpack decision is P0.6).
"""
from __future__ import annotations
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

FOLDERS = {
    "ipa_litigation": r"E:\00 - IPA Litigation",
    "shared_with_boris": r"E:\2. Shared with Boris",
    "da_response": r"E:\DA",
    "discovery_mt": r"E:\Discovery_docs_mt",
}
EMAIL_EXT = {".msg", ".eml", ".pst"}
ARCHIVE_EXT = {".zip", ".rar", ".7z"}
MANIFEST = "_phase5_manifest.json"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(blk)
    return h.hexdigest()


def main() -> int:
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    m.ping()

    print("loading existing DB fingerprints (sha256) ...")
    existing = set()
    for a in m.db["attachments_v2"].find({}, {"sha256": 1}):
        if a.get("sha256"):
            existing.add(a["sha256"])
    for sha in m.db["email_chunks_v2"].distinct("sha256"):
        if sha:
            existing.add(sha)
    for d in m.db["documents"].find({}, {"custody": 1}):
        cu = d.get("custody") or {}
        if isinstance(cu, dict) and cu.get("sha256"):
            existing.add(cu["sha256"])
    print(f"  existing fingerprints in DB: {len(existing)}")
    m.close()

    manifest = []
    sha_to_paths = defaultdict(list)
    per_folder = {}

    for matter, root in FOLDERS.items():
        rootp = Path(root)
        in_scope = excluded_email = archives = 0
        ext_counter = Counter()
        arch_list = []
        if not rootp.exists():
            print(f"!! MISSING FOLDER: {root}")
            per_folder[matter] = {"missing": True}
            continue
        for p in rootp.rglob("*"):
            if not p.is_file():
                continue
            ext = p.suffix.lower()
            if ext in EMAIL_EXT:
                excluded_email += 1
                continue
            if ext in ARCHIVE_EXT:
                archives += 1
                arch_list.append(str(p))
                continue
            # in-scope document
            try:
                sha = sha256_of(p)
            except Exception as exc:  # noqa: BLE001
                print(f"   hash failed {p}: {exc}")
                continue
            in_scope += 1
            ext_counter[ext] += 1
            sha_to_paths[sha].append(str(p))
            manifest.append({
                "matter": matter, "path": str(p), "rel": str(p)[len(root):],
                "ext": ext, "size": p.stat().st_size, "sha256": sha,
                "in_db": sha in existing,
            })
        per_folder[matter] = {
            "in_scope": in_scope, "excluded_email": excluded_email,
            "archives": archives, "by_ext": dict(ext_counter),
            "archive_files": arch_list,
        }
        print(f"\n[{matter}] in_scope={in_scope} excluded_email={excluded_email} "
              f"archives={archives}")
        print(f"   by_ext: {dict(ext_counter)}")
        if arch_list:
            for a in arch_list:
                print(f"   ARCHIVE: {a}")

    # dedup + db cross-check stats
    distinct = len(sha_to_paths)
    total = sum(len(v) for v in sha_to_paths.values())
    internal_dups = sum(len(v) - 1 for v in sha_to_paths.values() if len(v) > 1)
    new_sha = [sha for sha in sha_to_paths if sha not in existing]
    already = [sha for sha in sha_to_paths if sha in existing]

    print("\n" + "=" * 64)
    print("P0 INVENTORY & DEDUP SUMMARY")
    print("=" * 64)
    print(f"  total in-scope document files     : {total}")
    print(f"  distinct contents (unique sha256) : {distinct}")
    print(f"  internal duplicate copies (E:)    : {internal_dups}")
    print(f"  NEW (not in DB) distinct contents : {len(new_sha)}")
    print(f"  ALREADY in DB distinct contents   : {len(already)}")
    new_files = sum(1 for x in manifest if not x["in_db"])
    print(f"  NEW files to ingest (incl. copies): {new_files}")

    Path(MANIFEST).write_text(json.dumps({
        "per_folder": per_folder,
        "stats": {"total": total, "distinct": distinct,
                  "internal_dups": internal_dups,
                  "new_distinct": len(new_sha), "already_distinct": len(already),
                  "new_files": new_files},
        "files": manifest,
    }, indent=1), encoding="utf-8")
    print(f"\nmanifest written -> {MANIFEST} ({len(manifest)} file rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
