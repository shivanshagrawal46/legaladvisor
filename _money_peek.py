import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
money = m.db["money_records"]
for r in money.find().limit(8):
    print("-" * 70)
    print(f"doc      : {r['document_id']}  ({r.get('doc_category')})")
    print(f"payer    : {r.get('payer')}")
    print(f"payee    : {r.get('payee')}")
    print(f"amount   : {r.get('amount')}  (value={r.get('amount_value')})")
    print(f"date     : {r.get('date')}   instrument: {r.get('instrument')} #{r.get('instrument_no')}")
    print(f"property : {r.get('property')}  pids={r.get('property_ids')}")
    print(f"quote    : {(r.get('source_quote') or '')[:120]}")
print("=" * 70)
print("total money_records:", money.estimated_document_count())
m.close()
