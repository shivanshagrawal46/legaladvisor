from datetime import datetime, timezone
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
r = m.db["entities"].update_one(
    {"_id": "ent_llc_washington_new_realty_llc"},
    {"$set": {"side": "co_victim", "is_david": False, "is_david_network": False,
              "side_source": "user_decision_2026_06_15",
              "updated_at": datetime.now(timezone.utc)}})
print("washington_new matched:", r.matched_count)
m.close()
