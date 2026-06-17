import sys
from collections import Counter
import api.rag_singleton as S

QUESTIONS = [
    "When did IPA purchase and sell 8 Goose Hill Rd? Give owner name, dates and amounts.",
    "What are the names of properties in which IPA is the current owner per the latest title report?",
    "Give me a summary of 170 Hamlet Dr as per the latest title report.",
    "How many properties has IPA sold since 2020?",
]
REPORT = "_user_q.md"
with open(REPORT, "w", encoding="utf-8") as fh:
    fh.write("# User question test — system answers\n\n")
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
        fh.write(f"### UQ{i}. {q}\n- verify={vo} v{nv}/{nf} sources={dict(st)}\n\n{ans}\n\n---\n\n")
    print(f"[{i}/4] {vo} v{nv}/{nf} {dict(st)}")
    sys.stdout.flush()
print("USER Q DONE")
