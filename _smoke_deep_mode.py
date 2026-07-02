"""Smoke test for the Deep Investigation upgrade — imports, config, prompt."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# 1. Imports compile
from src.rag.v3.agent import AgentRunner
from src.rag.v3.prompts import build_agent_system_prompt
from src.rag.v3 import tools as v3_tools
from src.rag.v2.llm_reranker import LLMReranker
from src.rag.v2.orchestrator import V2Settings
from src.rag.v2 import answer_pipeline
from src.rag.chat import LegalAdvisorChat
from src.rag.retriever import Retriever
print("[1] imports OK")

# 2. Settings parse the new .env values
from config.settings import Settings
s = Settings.load()
assert s.claude_model == "claude-fable-5", s.claude_model
assert s.claude_max_output_tokens == 32768, s.claude_max_output_tokens
assert s.rag_v3_agent_model == "claude-fable-5", s.rag_v3_agent_model
assert s.rag_v3_agent_max_tokens_per_call == 32768
assert s.rag_v3_agent_effort == "high", s.rag_v3_agent_effort
assert s.rag_v2_llm_reranker_model == "claude-opus-4-8"
assert s.rag_v2_llm_reranker_effort == "high"
print("[2] settings OK:",
      f"chat={s.claude_model}, agent={s.rag_v3_agent_model} "
      f"(effort={s.rag_v3_agent_effort}, {s.rag_v3_agent_max_tokens_per_call} tok/call), "
      f"reranker={s.rag_v2_llm_reranker_model} (effort={s.rag_v2_llm_reranker_effort})")

# 3. Prompt has the new posture, not the old one
p = build_agent_system_prompt(max_calls=30)
assert "STRONG BIAS TOWARD SUBMITTING" not in p
assert "FORENSIC legal investigator" in p
assert "Investigator's assessment" in p
assert "Follow every dollar" in p
print("[3] prompt OK (deep forensic mode, submit-bias removed)")

# 4. AgentRunner accepts effort; seed caps raised
class _FakePipe:  # minimal stand-ins; runner __init__ doesn't touch them
    settings = None
r = AgentRunner(anthropic_client=object(), v2_pipeline=_FakePipe(),
                retriever=object(), model=s.rag_v3_agent_model,
                max_tokens_per_call=s.rag_v3_agent_max_tokens_per_call,
                effort=s.rag_v3_agent_effort)
assert r.effort == "high"
assert r.SEED_CHUNK_CHAR_CAP == 4500
print("[4] AgentRunner OK (effort wired, seed cap", r.SEED_CHUNK_CHAR_CAP, "chars/chunk)")

# 5. Tool truncation limits raised
import inspect
src = inspect.getsource(v3_tools)
assert "max_chars: int = 1600" in src
assert "_short_body(c, 1200)" in src
assert "40000" in src
print("[5] tool budgets OK (briefs 1200, full-doc 40K)")

# 6. LLMReranker defaults
rr = LLMReranker(object())
assert rr.snippet_chars == 1200 and rr.effort == "high"
print("[6] LLM reranker OK (snippet 1200, effort high)")

# 7. V2Settings carries reranker effort
vs = V2Settings(enabled=True, llm_reranker_effort=s.rag_v2_llm_reranker_effort)
assert vs.llm_reranker_effort == "high"
print("[7] V2Settings OK")

print("\nALL SMOKE CHECKS PASSED")
