import config.settings  # noqa
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
import json
s=Settings.load(); m=MongoClientWrapper(s.mongo_uri,s.mongo_db_name)
mr=m.db["money_records"]
for d in mr.find({},{"_id":0,"embedding":0}).limit(3):
    print(json.dumps({k:(str(v)[:120]) for k,v in d.items()},indent=2,default=str))
    print("amount type:",type(d.get("amount")).__name__,"value:",repr(d.get("amount")))
    print("---")
m.close()
