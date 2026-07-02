import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from anthropic import Anthropic

s = Settings.load()
c = Anthropic(api_key=s.anthropic_api_key, timeout=60.0, max_retries=0)
try:
    r = c.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=50,
        messages=[{"role": "user", "content": "Say 'ok' and nothing else."}],
    )
    print("SUCCESS:", "".join(getattr(b, "text", "") for b in r.content))
    print("usage:", r.usage)
except Exception as e:
    print("ERROR TYPE:", type(e).__name__)
    print("ERROR:", str(e)[:500])
