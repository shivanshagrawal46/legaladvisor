"""End-to-end test of the Deep Investigation upgrade: one real question
through the full production path (v2 retrieval -> Fable 5 agent loop ->
verifier -> hardening). Slightly reduced budget for the test run."""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.rag_singleton import make_chat

chat = make_chat()
# Test-sized budget (production stays 30 calls / 1200s).
chat.agent_max_tool_calls = 10
chat.agent_max_wall_clock_s = 600.0

events = []
def on_event(etype, payload):
    if etype == "agent_step":
        print(f"  [step {payload.get('step_num')}] {payload.get('tool_name')} "
              f"-> {str(payload.get('summary'))[:90]}", flush=True)
    elif etype in ("agent_plan", "agent_done", "agent_degraded",
                   "agent_forced_finalize", "agent_sufficiency_check"):
        print(f"  [{etype}] {str(payload)[:140]}", flush=True)
    events.append(etype)

chat.on_agent_event = on_event

q = ("What was the Confession of Judgment amount in the MangoTree/IPA "
     "settlement negotiations, and which mortgages were eliminated in "
     "exchange? Analyse what this exchange tells us about the parties' "
     "positions.")
print("QUESTION:", q, flush=True)
t0 = time.time()
turn = chat.ask(q)
dt = time.time() - t0

print("\n" + "=" * 70)
print(f"ELAPSED: {dt:.0f}s | outcome: {turn.verification_outcome} | "
      f"facts: {len(turn.facts or [])} | chunks: {len(turn.chunks or [])}")
print(f"ANSWER LENGTH: {len(turn.answer or '')} chars")
print("=" * 70)
print(turn.answer or "(empty)")
