import api.rag_singleton as S
from src.rag.v3.hardening import apply_hardening

client = S.get_anthropic_client()
mongo = S.get_mongo()
model = S.get_settings().rag_v3_agent_model

# a deliberately speculative answer (mirrors the 183 Mark Tree inference)
answer = ("183 Mark Tree Rd is owned by 183MA LLC, which is controlled by David DeRosa. "
          "The 2024 deed transferred a 90% interest for $2,500 — a fraudulent conveyance. "
          "FAKECO HOLDINGS LLC also appears in the chain. No notice of pendency was found on file.")
facts = [{"claim": "183MA LLC is controlled by David DeRosa"},
         {"claim": "2024 transfer was $2,500 for 90%"}]

rep = apply_hardening(client, model, query="Who owns 183 Mark Tree and is it David's?",
                      answer=answer, facts=facts, mongo=mongo)
dc = rep["defense_critique"]
print("DEFENSE CRITIQUE:", dc.get("severity"), "|", dc.get("category"))
print("  gap:", dc.get("gap"))
print("ENTITY VALIDATION not_in_graph:", rep["entity_validation"]["not_in_graph"])
print("states_negative_evidence:", rep["states_negative_evidence"])
print("\nANNOTATED ANSWER TAIL:\n", rep["annotated_answer"][-400:])
