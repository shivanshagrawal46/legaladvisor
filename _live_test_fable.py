"""Live 2-call check: Fable 5 + effort via streaming, Opus 4.8 + effort."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from anthropic import Anthropic

s = Settings.load()
c = Anthropic(api_key=s.anthropic_api_key, timeout=120.0, max_retries=0)

# 1. Fable 5, streaming, output_config effort=high (planner shape)
try:
    with c.messages.stream(
        model="claude-fable-5", max_tokens=2000,
        messages=[{"role": "user", "content": "Say 'fable ok' and nothing else."}],
        output_config={"effort": "high"},
    ) as st:
        m = st.get_final_message()
    txt = "".join(getattr(b, "text", "") for b in m.content)
    kinds = [getattr(b, "type", "?") for b in m.content]
    print("FABLE5 + effort=high (stream):", repr(txt.strip()),
          "| model:", m.model, "| blocks:", kinds)
except Exception as e:
    print("FABLE5 ERROR:", type(e).__name__, str(e)[:300])

# 2. Opus 4.8 + effort=high non-streaming with forced tool_choice (reranker shape)
_TOOL = {"name": "rank", "description": "rank",
         "input_schema": {"type": "object", "properties": {
             "ok": {"type": "boolean"}}, "required": ["ok"]}}
try:
    m = c.messages.create(
        model="claude-opus-4-8", max_tokens=2000,
        tools=[_TOOL], tool_choice={"type": "tool", "name": "rank"},
        messages=[{"role": "user", "content": "Call rank with ok=true."}],
        output_config={"effort": "high"},
    )
    kinds = [getattr(b, "type", "?") for b in m.content]
    print("OPUS4.8 + effort=high + forced tool (create): blocks:", kinds,
          "| model:", m.model)
except Exception as e:
    print("OPUS ERROR:", type(e).__name__, str(e)[:300])
