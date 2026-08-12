"""Was it Anthropic rejecting us, or a connection that went silent?

A rejection from Anthropic arrives as an HTTP status (429 rate limit, 529
overloaded, 500 server error) and is fast. A silent stall arrives as a
client-side socket timeout with no status code at all. The two look very
different in the logs, so count them separately.
"""
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
tl = m.db["agent_trace_log"]

print("=" * 72)
print("HOW DID EACH RUN ACTUALLY END? (parsed from the stub answer text)")
print("=" * 72)

kinds = Counter()
timeouts = []
for d in tl.find({}, {"final_answer": 1, "elapsed_ms": 1, "query": 1, "started_at": 1}):
    fa = d.get("final_answer")
    txt = fa.get("answer") if isinstance(fa, dict) else fa
    txt = str(txt or "")
    el = (d.get("elapsed_ms") or 0) / 1000
    if "planner_error" in txt:
        mt = re.search(r"planner_error:\s*([^)]*)", txt)
        detail = (mt.group(1).strip() if mt else "?")[:52]
        kinds[f"planner_error: {detail}"] += 1
        timeouts.append((el, d.get("started_at"), (d.get("query") or "")[:44]))
    elif "investigation budget was reached" in txt:
        mt = re.search(r"budget was reached \(([^)]*)\)", txt)
        kinds[f"real budget: {(mt.group(1) if mt else '?')[:44]}"] += 1
    else:
        kinds["completed normally"] += 1

total = sum(kinds.values())
for k, v in kinds.most_common():
    print(f"  {v:>4}x  ({v/total*100:>4.1f}%)  {k}")

if timeouts:
    print(f"\n  runs killed by a planner timeout ({len(timeouts)}):")
    for el, when, q in sorted(timeouts, reverse=True):
        print(f"    {el:>7.0f}s  {str(when)[:19]}  {q}")

print("\n" + "=" * 72)
print("EVIDENCE OF ANTHROPIC-SIDE REJECTIONS IN THE LOGS")
print("=" * 72)
pats = {
    "429 rate_limit": r"429|rate.?limit",
    "529 overloaded": r"529|overloaded",
    "500/502/503 server": r"\b50[023]\b|internal server error|bad gateway",
    "read timeout (SILENT STALL)": r"read operation timed out|ReadTimeout|readtimeout",
    "connection reset/aborted": r"connection reset|connection aborted|remotedisconnected",
    "APIStatusError": r"APIStatusError|APIError|BadRequestError",
}
logdir = Path("logs")
counts = Counter()
for lf in sorted(logdir.glob("*.log")):
    try:
        txt = lf.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    for label, pat in pats.items():
        n = len(re.findall(pat, txt, re.I))
        if n:
            counts[label] += n
            print(f"  {lf.name:34s} {label:30s} {n:>6}")
print("\n  TOTALS:")
for k, v in counts.most_common():
    print(f"    {k:30s} {v:>6}")
if not counts:
    print("    (no API error signatures found in logs/)")

m.close()
