import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
em = m.db["emails"]
q = {"$or": [
    {"folder_path": {"$regex": "boris", "$options": "i"}},
    {"gmail_labels": {"$regex": "boris", "$options": "i"}},
    {"also_seen_gmail_labels": {"$regex": "boris", "$options": "i"}},
]}
n = em.count_documents(q)
print("emails matching 'boris' label:", n)

fps, lbls = set(), set()
for d in em.find(q, {"folder_path": 1, "gmail_labels": 1, "also_seen_gmail_labels": 1}):
    if d.get("folder_path"):
        fps.add(d["folder_path"])
    for l in (d.get("gmail_labels") or []):
        lbls.add(l)
    for l in (d.get("also_seen_gmail_labels") or []):
        lbls.add(l)
print("folder_paths:", sorted(fps)[:20])
print("labels:", sorted(lbls)[:20])

print("--- latest 5 by date ---")
for d in em.find(q, {"date": 1, "subject": 1, "from": 1}).sort("date", -1).limit(5):
    fr = (d.get("from") or {}).get("email", "")
    print(d.get("date"), "|", fr, "|", (d.get("subject") or "")[:60])

# also check any label containing 'lawsuit'
q2 = {"$or": [
    {"folder_path": {"$regex": "lawsuit", "$options": "i"}},
    {"gmail_labels": {"$regex": "lawsuit", "$options": "i"}},
    {"also_seen_gmail_labels": {"$regex": "lawsuit", "$options": "i"}},
]}
print("\nemails matching 'lawsuit' label:", em.count_documents(q2))
m.close()
