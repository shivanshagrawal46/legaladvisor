"""What labels do Maida's un-ingested messages actually carry? The pull stamps
gmail_labels/folder_path from the --label flag, so this decides how to group
the pulls and avoids mislabelling non-Boris mail as Boris Lawsuit."""
import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings  # noqa: F401
from src.ingest.gmail_client import GmailClient

ids = [r["gmail_id"] for r in
       csv.DictReader(Path("_maida_ids.csv").open(newline="", encoding="utf-8"))
       if r.get("gmail_id")]

client = GmailClient().authenticate()
# id -> name map for every label in the mailbox
name_of = {}
try:
    for lb in client.list_labels():
        if isinstance(lb, dict):
            name_of[lb.get("id")] = lb.get("name")
except Exception as exc:  # noqa: BLE001
    print(f"(could not list labels: {exc})")

groups = defaultdict(list)
for gid in ids:
    meta = client.get_metadata(gid)
    lids = meta.get("label_ids") or meta.get("labelIds") or []
    names = tuple(sorted(name_of.get(l, l) for l in lids
                         if not str(l).startswith("CATEGORY_")))
    groups[names].append(gid)
    print(f"  {gid}  {list(names)}")

print("\n--- grouped ---")
for names, gids in groups.items():
    print(f"  {len(gids):>2} msg  {list(names)}")
