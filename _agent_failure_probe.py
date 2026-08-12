"""Outcome breakdown for agent runs + anatomy of the 1189s failure."""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
tl = m.db["agent_trace_log"]

print("=" * 70)
print("OUTCOME BREAKDOWN")
print("=" * 70)
for k, v in Counter(d.get("outcome") for d in tl.find({}, {"outcome": 1})).most_common():
    print(f"  {v:>4}x  {k}")

print("\n" + "=" * 70)
print("RUNTIME DISTRIBUTION")
print("=" * 70)
els = sorted((d.get("elapsed_ms") or 0) / 1000 for d in tl.find({}, {"elapsed_ms": 1}))
n = len(els)
buckets = [(0, 60), (60, 180), (180, 300), (300, 600), (600, 1200), (1200, 10 ** 9)]
for lo, hi in buckets:
    c = sum(1 for e in els if lo <= e < hi)
    label = f"{lo}-{hi}s" if hi < 10 ** 9 else f">{lo}s"
    print(f"  {label:>12}: {c:>4}  ({c/n*100:>5.1f}%)  {'#' * int(c / n * 50)}")
print(f"\n  median {els[n//2]:.0f}s   p90 {els[int(n*0.9)]:.0f}s   max {els[-1]:.0f}s")

print("\n" + "=" * 70)
print("ANATOMY OF THE 1189s RUN")
print("=" * 70)
d = tl.find_one({"elapsed_ms": {"$gte": 1_185_000, "$lte": 1_195_000}})
if d:
    print(f"  query   : {(d.get('query') or '')[:100]}")
    print(f"  outcome : {d.get('outcome')}")
    print(f"  elapsed : {(d.get('elapsed_ms') or 0)/1000:.0f}s")
    print(f"  steps   : {d.get('n_steps')}  facts={d.get('n_facts')} "
          f"verified={d.get('n_verified')} chunks={d.get('n_chunks_discovered')}")
    b = d.get("budget") or {}
    print(f"  budget  : tool_calls={b.get('tool_calls_used')}/{b.get('max_tool_calls')} "
          f"tokens={b.get('total_tokens')}/{b.get('max_total_tokens')} "
          f"elapsed_s={b.get('elapsed_s')}/{b.get('max_wall_clock_s')}")
    fa = d.get("final_answer")
    if isinstance(fa, dict):
        fa = fa.get("answer") or str(fa)
    print(f"  answer  : {str(fa or '')[:400]}")
    print("\n  step timeline:")
    for i, st in enumerate(d.get("steps") or []):
        print(f"    {i:>2}. {str(st.get('type')):18s} {str(st.get('tool_name')):22s} "
              f"{(st.get('elapsed_ms') or 0)/1000:>7.1f}s  {str(st.get('summary'))[:44]}")

# Where does the time actually go? Sum step time vs total.
print("\n" + "=" * 70)
print("TIME ACCOUNTED FOR BY TOOL STEPS vs UNACCOUNTED (planner thinking/hangs)")
print("=" * 70)
tot_run = tot_step = 0
worst = []
for d in tl.find({}, {"elapsed_ms": 1, "steps": 1, "query": 1}):
    run = (d.get("elapsed_ms") or 0) / 1000
    stp = sum((st.get("elapsed_ms") or 0) for st in (d.get("steps") or [])) / 1000
    if run <= 0:
        continue
    tot_run += run
    tot_step += stp
    if run > 300:
        worst.append((run - stp, run, stp, (d.get("query") or "")[:48]))
print(f"  total wall time across all runs : {tot_run:>10,.0f}s")
print(f"  time inside tool steps          : {tot_step:>10,.0f}s ({tot_step/tot_run*100:.1f}%)")
print(f"  UNACCOUNTED (planner LLM waits) : {tot_run - tot_step:>10,.0f}s "
      f"({(tot_run-tot_step)/tot_run*100:.1f}%)")
worst.sort(reverse=True)
print("\n  worst unaccounted gaps:")
for gap, run, stp, q in worst[:10]:
    print(f"    gap={gap:>7.0f}s  (run={run:>6.0f}s tools={stp:>6.0f}s)  {q}")

m.close()
