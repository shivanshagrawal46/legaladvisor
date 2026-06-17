import sys
from collections import Counter
import api.rag_singleton as S

QUESTIONS = [
    # 1) entity-network reasoning (graph)
    "Who is David DeRosa and which LLCs and entities does he control? List them.",
    # 2) bitemporal ownership chain (the new as_of/until work)
    "Who has owned 230 Ralph Ave over time, with the dates each owner held title?",
    # 3) flow-of-funds tracing
    "Trace the money associated with 12 Mallard Path, Coram - payments, transfers, and amounts.",
    # 4) cross-portfolio fraud detection
    "What are the most suspicious or potentially voidable transfers across David's portfolio?",
    # 5) cross-source factual + negative-evidence honesty
    "Is there insurance coverage on 91 West Shore Road, Huntington? Give insurer and policy details if any.",
]
REPORT = "_q5_test.md"
with open(REPORT, "w", encoding="utf-8") as fh:
    fh.write("# 5-question system probe\n\n")
for i, q in enumerate(QUESTIONS, 1):
    chat = S.make_chat()
    try:
        t = chat.ask(q)
        ans, vo = t.answer or "", t.verification_outcome
        nv = sum(1 for v in (t.fact_verdicts or []) if v.get("verdict") == "VERIFIED")
        nf = len(t.facts or [])
        st = Counter((c.source_type or "?") for c in (t.chunks or []))
    except Exception as exc:  # noqa: BLE001
        ans, vo, nv, nf, st = f"ERROR {exc}", "ERR", 0, 0, {}
    with open(REPORT, "a", encoding="utf-8") as fh:
        fh.write(f"### Q{i}. {q}\n- verify={vo} v{nv}/{nf} sources={dict(st)}\n\n{ans}\n\n---\n\n")
    print(f"[{i}/5] {vo} v{nv}/{nf} {dict(st)}")
    sys.stdout.flush()
print("Q5 DONE")
