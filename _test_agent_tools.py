"""Verify the new entity-graph agent tools work end-to-end against Mongo
(no LLM calls — these tools hit the graph + chunks directly)."""
import api.rag_singleton as S
from src.rag.v3.tools import ToolBox, build_tool_specs
from src.rag.v3.scratchpad import AgentScratchpad

retr = S.get_retriever()
v2 = S._get_v2_pipeline()
box = ToolBox(v2_pipeline=v2, retriever=retr)
pad = AgentScratchpad(query="test")
box.attach_scratchpad(pad)

specs = build_tool_specs(box)
print("registered tools:", list(specs.keys()))
assert "search_entity_cluster" in specs
assert "list_documents_for_entity" in specs
assert "graph_query" in specs

print("\n--- tool_search_entity_cluster('1091 Gardiner Dr') ---")
r = box.tool_search_entity_cluster(query="1091 Gardiner Dr Bay Shore", limit=40)
print(r.summary)
print("  source_breakdown:", r.payload.get("source_breakdown"))
print("  entity_names:", r.payload.get("entity_names"))

print("\n--- tool_list_documents_for_entity('IPA Asset Management') ---")
r = box.tool_list_documents_for_entity(entity_query="IPA Asset Management")
print(r.summary)

print("\n--- tool_graph_query('1091 Gardiner Dr Bay Shore') ---")
r = box.tool_graph_query(entity_query="1091 Gardiner Dr Bay Shore")
print(r.summary)
for e in r.payload.get("edges", [])[:8]:
    print("   ", e["type"], "|", e["from"], "->", e["to"], e.get("as_of"))
print("\nALL TOOL TESTS PASSED")
