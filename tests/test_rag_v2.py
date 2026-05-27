"""
Comprehensive offline test suite for RAG v2.

Run with:  python -m pytest tests/test_rag_v2.py -v
Or:        python tests/test_rag_v2.py

Every test is self-contained — no MongoDB, no Anthropic API, no network.
We mock the external dependencies so the full pipeline is exercised
deterministically.
"""
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence
from unittest.mock import MagicMock

# Make src/ importable when running this file directly.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# =====================================================================
#  1. Query Understanding
# =====================================================================

class TestQueryUnderstanding(unittest.TestCase):
    """Pure-Python signal extraction. No I/O."""

    def setUp(self) -> None:
        from src.rag.v2.query_understanding import extract_signals
        self.extract = extract_signals

    def test_empty_input(self) -> None:
        s = self.extract("")
        self.assertEqual(s.text, "")
        self.assertEqual(s.primary_intent(), "general")

    def test_user_failing_query_global_stipulation(self) -> None:
        """The exact query that failed in production should now extract."""
        q = ("do you have this document Global Stipulation re Escrow and "
             "Appeal 01-20-26 v2? attached to email dated Jan 20-26 from william?")
        s = self.extract(q)
        # Title-case extraction must catch the document name.
        self.assertTrue(
            any("Global Stipulation" in p for p in s.quoted_strings),
            f"Expected 'Global Stipulation' in quoted_strings, got {s.quoted_strings}",
        )
        # 2-digit year date 01-20-26 must parse as 2026-01-20.
        self.assertIn(
            datetime(2026, 1, 20),
            s.explicit_dates,
            f"Expected 2026-01-20 in explicit_dates, got {s.explicit_dates}",
        )
        # Date window must be tight.
        self.assertEqual(s.date_from, datetime(2026, 1, 20, 0, 0, 0))
        # Boost terms must include the document name.
        self.assertTrue(any("Global Stipulation" in t for t in s.keyword_boost_terms))

    def test_compare_intent(self) -> None:
        s = self.extract("compare the figure across stipulations from 2024 to 2026")
        self.assertEqual(s.primary_intent(), "compare")
        self.assertEqual(s.date_from.year, 2024)
        self.assertEqual(s.date_to.year, 2026)
        self.assertTrue(s.is_complex())

    def test_timeline_intent(self) -> None:
        s = self.extract("show me the timeline of all payments over time")
        self.assertEqual(s.primary_intent(), "timeline")
        self.assertTrue(s.is_complex())

    def test_lookup_with_email_and_date(self) -> None:
        s = self.extract("who sent wheuer@example.com on January 20, 2026?")
        self.assertEqual(s.primary_intent(), "lookup")
        self.assertIn("wheuer@example.com", s.emails)
        self.assertIn(datetime(2026, 1, 20), s.explicit_dates)

    def test_dollar_amount_extraction(self) -> None:
        s = self.extract("compare $450,000 across the case")
        self.assertTrue(any("450,000" in m for m in s.money_terms))

    def test_bare_number_detected_with_money_context(self) -> None:
        """Bare 450,000 should be picked up when context says 'number' or 'amount'."""
        s = self.extract("find me reference where 450,000 number was mentioned")
        # We expect both the bare form AND the $-prefixed form for boost matching.
        joined = " ".join(s.money_terms)
        self.assertIn("450,000", joined)
        self.assertIn("$450,000", joined)

    def test_bare_number_NOT_detected_without_money_context(self) -> None:
        """Bare 450,000 in a non-money sentence should NOT be flagged as money."""
        s = self.extract("page 450,000 of the deposition was lost")
        # 'page' is not in money-context list → no false positive.
        # (But "$" detection still works — this is a true bare-number-only case.)
        # Note: the word "deposition" is also legal-context-neutral so we expect empty.
        self.assertEqual(s.money_terms, [])

    def test_docket_number(self) -> None:
        s = self.extract("what is Dkt. No. 149 about?")
        self.assertIn("149", s.docket_numbers)

    def test_filename_with_extension(self) -> None:
        s = self.extract("can you read Order_Approving_Sale.pdf?")
        self.assertTrue(any("pdf" in f.lower() for f in s.filenames))

    def test_no_signal_general_query(self) -> None:
        s = self.extract("hello how are you?")
        self.assertEqual(s.primary_intent(), "general")
        self.assertFalse(s.has_temporal_signal)
        self.assertFalse(s.has_explicit_target)


# =====================================================================
#  2. Query Rewriter — parsing only (no LLM calls)
# =====================================================================

class TestQueryRewriterParsing(unittest.TestCase):
    """Verify JSON salvaging is robust to common Claude output shapes."""

    def setUp(self) -> None:
        from src.rag.v2.query_rewriter import QueryRewriter
        self.QR = QueryRewriter

    def test_clean_json(self) -> None:
        raw = '{"hyde_answer":"X","alt_queries":["a","b","c"]}'
        out = self.QR._parse_response(raw)
        self.assertEqual(out["hyde_answer"], "X")
        self.assertEqual(out["alt_queries"], ["a", "b", "c"])

    def test_markdown_fenced_json(self) -> None:
        raw = '```json\n{"hyde_answer":"X","alt_queries":["a"]}\n```'
        out = self.QR._parse_response(raw)
        self.assertEqual(out["hyde_answer"], "X")
        self.assertEqual(out["alt_queries"], ["a"])

    def test_trailing_prose_after_json(self) -> None:
        raw = ('{"hyde_answer":"The court ordered $450,000",'
               '"alt_queries":["q1","q2"]} \n\n And here is some prose.')
        out = self.QR._parse_response(raw)
        self.assertIn("$450,000", out["hyde_answer"])
        self.assertEqual(out["alt_queries"], ["q1", "q2"])

    def test_malformed_json_regex_salvage(self) -> None:
        raw = 'broken { "hyde_answer": "salvaged answer here", "alt_queries": ['
        out = self.QR._parse_response(raw)
        self.assertEqual(out["hyde_answer"], "salvaged answer here")

    def test_empty_string(self) -> None:
        out = self.QR._parse_response("")
        self.assertIsNone(out["hyde_answer"])
        self.assertEqual(out["alt_queries"], [])

    def test_alt_query_length_cap(self) -> None:
        long = "x" * 500
        raw = f'{{"hyde_answer":"a","alt_queries":["{long}","short"]}}'
        out = self.QR._parse_response(raw)
        # 500-char alt should be filtered (cap is 240).
        self.assertEqual(out["alt_queries"], ["short"])

    def test_rewrite_failsafe_when_llm_raises(self) -> None:
        """When the underlying LLM raises, we should get original-only back."""
        client = MagicMock()
        client.messages.create.side_effect = RuntimeError("boom")
        rw = self.QR(client=client, model="claude-sonnet-4-6")
        out = rw.rewrite("test query", enable_hyde=True, enable_multi_query=True)
        self.assertEqual(out.original, "test query")
        self.assertIsNone(out.hyde_answer)
        self.assertEqual(out.alt_queries, [])

    def test_rewrite_no_op_shortcut(self) -> None:
        """Both flags off → no LLM call, return original."""
        client = MagicMock()
        rw = self.QR(client=client, model="claude-sonnet-4-6")
        out = rw.rewrite("q", enable_hyde=False, enable_multi_query=False)
        client.messages.create.assert_not_called()
        self.assertEqual(out.original, "q")


# =====================================================================
#  3. Hybrid Search — RRF fusion
# =====================================================================

class TestHybridSearcherChannels(unittest.TestCase):
    """Verify the new exact-phrase + body-substring channels exist and are wired."""

    def test_search_accepts_exact_phrases_and_body_substrings(self) -> None:
        """The new channels must be addressable from the orchestrator."""
        from src.rag.v2.hybrid_search import HybridSearcher
        mongo = MagicMock()
        mongo.chunks.aggregate.return_value = iter([])
        mongo.chunks.find.return_value.sort.return_value.limit.return_value = iter([])

        s = HybridSearcher(mongo=mongo, vector_index_name="test")
        # Must not raise even when both new params are populated.
        result = s.search(
            query_vectors=[[0.1] * 8],
            text_queries=["test query"],
            filenames=[],
            body_substrings=["$450,000", "$500,000"],
            exact_phrases=["$450,000", "$500,000"],
        )
        self.assertEqual(result.chunks, [])
        # Verify the regex body channel was actually invoked (it queries
        # chunks.find with a $regex predicate). One call per body_substring.
        regex_calls = [
            c for c in mongo.chunks.find.call_args_list
            if "body" in (c.args[0] if c.args else c.kwargs.get("filter", {}))
            or "$or" in (c.args[0] if c.args else c.kwargs.get("filter", {}))
        ]
        # 2 body_substrings + 2 phrase BM25 (no body field, but goes through find too)
        # We just need at least the body_substrings to have hit `find`.
        self.assertGreaterEqual(
            mongo.chunks.find.call_count, 2,
            "Body-substring channel must have queried Mongo at least twice",
        )

    def test_body_substring_uses_regex_with_dollar_escaped(self) -> None:
        """The $ sign in money tokens must be regex-escaped so it doesn't match end-of-string."""
        from src.rag.v2.hybrid_search import HybridSearcher
        mongo = MagicMock()
        mongo.chunks.find.return_value.sort.return_value.limit.return_value = iter([])
        s = HybridSearcher(mongo=mongo, vector_index_name="test")
        s._body_substring_lookup("$450,000")
        # First positional arg of find() is the filter dict.
        call = mongo.chunks.find.call_args
        filt = call.args[0] if call.args else call.kwargs.get("filter", {})
        # The regex pattern in the filter must contain the literal '$' escaped.
        body_clause = filt["$or"][0]["body"]["$regex"]
        self.assertIn(r"\$", body_clause, f"Regex must escape $ but got: {body_clause}")
        # And it must contain the literal '450,000' substring.
        self.assertIn("450,000", body_clause)


class TestRRFFusion(unittest.TestCase):
    """Reciprocal Rank Fusion math and dedup."""

    def setUp(self) -> None:
        from src.rag.v2.hybrid_search import _reciprocal_rank_fusion
        self.rrf = _reciprocal_rank_fusion

    def test_single_list_passthrough(self) -> None:
        docs = [{"_id": f"d{i}"} for i in range(5)]
        fused = self.rrf([docs], k=60)
        self.assertEqual(len(fused), 5)
        # Order preserved, top doc has highest score.
        self.assertEqual(fused[0][0]["_id"], "d0")
        self.assertGreater(fused[0][1], fused[-1][1])

    def test_doc_in_both_lists_ranks_higher(self) -> None:
        a = [{"_id": "shared"}, {"_id": "a_only"}]
        b = [{"_id": "shared"}, {"_id": "b_only"}]
        fused = self.rrf([a, b], k=60)
        # shared appears in both → highest score.
        self.assertEqual(fused[0][0]["_id"], "shared")

    def test_dedup_on_id(self) -> None:
        a = [{"_id": "x"}, {"_id": "y"}]
        b = [{"_id": "x"}, {"_id": "y"}]
        fused = self.rrf([a, b], k=60)
        self.assertEqual(len(fused), 2)

    def test_empty_input(self) -> None:
        self.assertEqual(self.rrf([], k=60), [])
        self.assertEqual(self.rrf([[]], k=60), [])


# =====================================================================
#  4. Temporal — re-scoring & diversification
# =====================================================================

class TestTemporal(unittest.TestCase):
    def setUp(self) -> None:
        from src.rag.v2.temporal import rescore, diversify, temporal_diversify
        self.rescore = rescore
        self.diversify = diversify
        self.temporal = temporal_diversify

        D = "$" + "450,000"
        self.D = D
        self.candidates = [
            {"_id": "c1", "filename": "Order Approving Sale.pdf",
             "attachment_id": "A", "body": f"court ordered {D}",
             "date": datetime(2026, 1, 20, tzinfo=timezone.utc)},
            {"_id": "c2", "filename": "Stipulation Draft.docx",
             "attachment_id": "B", "body": "$400,000 draft",
             "date": datetime(2024, 5, 1, tzinfo=timezone.utc)},
            {"_id": "c3", "filename": "Email", "email_id": "E1",
             "body": "random email", "date": datetime(2025, 3, 1, tzinfo=timezone.utc)},
            {"_id": "c4", "filename": "Order Approving Sale.pdf",
             "attachment_id": "A", "body": "more",
             "date": datetime(2026, 1, 20, tzinfo=timezone.utc)},
            {"_id": "c5", "filename": "Order Approving Sale.pdf",
             "attachment_id": "A", "body": "still more",
             "date": datetime(2026, 1, 20, tzinfo=timezone.utc)},
            {"_id": "c6", "filename": "Order Approving Sale.pdf",
             "attachment_id": "A", "body": "yet more",
             "date": datetime(2026, 1, 20, tzinfo=timezone.utc)},
            {"_id": "c7", "filename": "Settlement Agreement.pdf",
             "attachment_id": "C", "body": f"{D} match",
             "date": datetime(2023, 2, 2, tzinfo=timezone.utc)},
        ]
        self.base_scores = {c["_id"]: 1.0 / (60 + i + 1) for i, c in enumerate(self.candidates)}

    def test_rescore_boosts_recent_authoritative_exact(self) -> None:
        """c1 (newest court order containing exact $) should outrank c2 (older draft)."""
        scored = self.rescore(
            self.candidates, base_scores=self.base_scores,
            keyword_boost_terms=[self.D, "Stipulation"],
        )
        c1 = next(s for s in scored if s.doc["_id"] == "c1")
        c2 = next(s for s in scored if s.doc["_id"] == "c2")
        self.assertGreater(c1.final_score, c2.final_score)
        self.assertGreater(c1.recency, c2.recency)
        self.assertGreater(c1.authority, c2.authority)

    def test_rescore_disabled(self) -> None:
        """When all boosts off, final_score == base_score."""
        scored = self.rescore(
            self.candidates, base_scores=self.base_scores,
            enable_recency=False, enable_authority=False, enable_exact_match=False,
        )
        for s in scored:
            self.assertAlmostEqual(s.final_score, s.base_score)

    def test_cluster_diversify_caps_per_attachment(self) -> None:
        scored = self.rescore(self.candidates, base_scores=self.base_scores)
        div = self.diversify(scored, max_per_cluster=2, final_limit=10)
        # Order Approving Sale (att:A) has 4 chunks but should be capped to 2.
        a_chunks = [s for s in div if s.cluster_key == "att:A"]
        self.assertEqual(len(a_chunks), 2)

    def test_temporal_diversify_covers_all_years(self) -> None:
        scored = self.rescore(self.candidates, base_scores=self.base_scores)
        td = self.temporal(scored, final_limit=4, min_per_year=1)
        years = {s.doc["date"].year for s in td}
        # All four years (2023, 2024, 2025, 2026) represented in first pass.
        self.assertEqual(years, {2023, 2024, 2025, 2026})

    def test_authority_demotes_drafts(self) -> None:
        """A 'Draft' filename should get authority < 1.0."""
        from src.rag.v2.temporal import _authority_score
        self.assertLess(
            _authority_score({"filename": "Settlement Draft v3.docx"}),
            1.0,
        )
        self.assertGreater(
            _authority_score({"filename": "Court Order Final.pdf"}),
            1.0,
        )


# =====================================================================
#  5. Parent Doc Expansion — mocked Mongo
# =====================================================================

class TestParentDocExpansion(unittest.TestCase):
    def test_no_expansion_when_only_one_chunk_per_parent(self) -> None:
        from src.rag.v2.parent_doc import parent_document_expand
        mongo = MagicMock()
        retrieved = [
            {"_id": "1", "attachment_id": "A", "body": "x" * 400, "chunk_index": 0},
            {"_id": "2", "attachment_id": "B", "body": "y" * 400, "chunk_index": 0},
        ]
        result = parent_document_expand(mongo, retrieved_chunks=retrieved)
        self.assertEqual(len(result.chunks), 2)
        self.assertEqual(result.expanded_attachment_ids, [])
        # Mongo never queried.
        mongo.chunks.find.assert_not_called()

    def test_expansion_fires_when_two_chunks_share_parent(self) -> None:
        from src.rag.v2.parent_doc import parent_document_expand
        mongo = MagicMock()
        # The Mongo find().sort().limit() chain must yield extra chunks.
        extra = [
            {"_id": f"extra{i}", "attachment_id": "A",
             "body": "z" * 400, "chunk_index": i + 2}
            for i in range(3)
        ]
        cursor = MagicMock()
        cursor.__iter__ = lambda self: iter(extra)
        mongo.chunks.find.return_value.sort.return_value.limit.return_value = cursor

        retrieved = [
            {"_id": "1", "attachment_id": "A", "body": "x" * 400, "chunk_index": 0},
            {"_id": "2", "attachment_id": "A", "body": "y" * 400, "chunk_index": 1},
        ]
        result = parent_document_expand(
            mongo, retrieved_chunks=retrieved,
            min_chunks_for_expansion=2,
            token_budget_single=10_000,
        )
        # We started with 2; extras should have been added.
        self.assertGreater(len(result.chunks), 2)
        self.assertIn("A", result.expanded_attachment_ids)

    def test_expansion_respects_token_budget(self) -> None:
        from src.rag.v2.parent_doc import parent_document_expand
        mongo = MagicMock()
        # Each chunk is 4000 bytes ≈ 1000 tokens.
        extra = [
            {"_id": f"extra{i}", "attachment_id": "A",
             "body": "z" * 4000, "chunk_index": i + 2}
            for i in range(10)
        ]
        cursor = MagicMock()
        cursor.__iter__ = lambda self: iter(extra)
        mongo.chunks.find.return_value.sort.return_value.limit.return_value = cursor

        retrieved = [
            {"_id": "1", "attachment_id": "A", "body": "x" * 100, "chunk_index": 0},
            {"_id": "2", "attachment_id": "A", "body": "y" * 100, "chunk_index": 1},
        ]
        result = parent_document_expand(
            mongo, retrieved_chunks=retrieved,
            min_chunks_for_expansion=2,
            token_budget_single=2500,  # small budget — only 2 extras can fit
        )
        # tokens_added must respect budget (with 1-chunk overflow allowed
        # to avoid the empty-expansion edge case).
        self.assertLessEqual(result.tokens_added, 4000)


# =====================================================================
#  6. Conversation Summary Memory
# =====================================================================

class TestSummaryMemory(unittest.TestCase):
    def setUp(self) -> None:
        from src.rag.v2.memory import SummaryMemory, Turn
        self.SummaryMemory = SummaryMemory
        self.Turn = Turn

    def test_short_history_returns_verbatim(self) -> None:
        client = MagicMock()
        mem = self.SummaryMemory(
            client, summary_after_turns=8, keep_recent=5,
        )
        turns = [self.Turn(question=f"q{i}", answer=f"a{i}") for i in range(3)]
        msgs = mem.build_prior_messages(turns)
        # 3 turns × 2 messages each = 6.
        self.assertEqual(len(msgs), 6)
        # No summary message present.
        self.assertFalse(
            msgs[0]["content"].startswith("[Conversation memory")
        )

    def test_long_history_uses_summary(self) -> None:
        client = MagicMock()
        # Make Claude return a fake summary.
        fake_response = MagicMock()
        fake_response.content = [MagicMock(type="text", text="FAKE SUMMARY")]
        client.messages.create.return_value = fake_response

        mem = self.SummaryMemory(
            client, summary_after_turns=8, keep_recent=5,
        )
        turns = [self.Turn(question=f"q{i}", answer=f"a{i}") for i in range(20)]
        # Update the summary first.
        mem.maybe_update_summary(turns)
        self.assertEqual(mem.state.summary, "FAKE SUMMARY")
        self.assertEqual(mem.state.summarised_through, 15)  # 20 - keep_recent(5)

        msgs = mem.build_prior_messages(turns)
        # Summary message + 5 turns × 2 = 11 messages.
        self.assertEqual(len(msgs), 11)
        self.assertTrue(msgs[0]["content"].startswith("[Conversation memory"))
        self.assertIn("FAKE SUMMARY", msgs[0]["content"])

    def test_failsafe_when_llm_raises(self) -> None:
        client = MagicMock()
        client.messages.create.side_effect = RuntimeError("boom")
        mem = self.SummaryMemory(
            client, summary_after_turns=8, keep_recent=5,
        )
        turns = [self.Turn(question=f"q{i}", answer=f"a{i}") for i in range(15)]
        # Should not raise.
        mem.maybe_update_summary(turns)
        # State unchanged because LLM failed.
        self.assertEqual(mem.state.summary, "")


# =====================================================================
#  7. Enhanced Prompt
# =====================================================================

class TestPrompts(unittest.TestCase):
    def test_base_prompt_has_self_critique(self) -> None:
        from src.rag.v2.prompts import build_system_prompt
        p = build_system_prompt(intent="general")
        self.assertIn("Self-critique", p)
        self.assertIn("Reasoning protocol", p)
        self.assertIn("authority hierarchy", p)
        self.assertIn("[#N]", p)  # citation format must be in the prompt

    def test_timeline_prompt_includes_timeline_block(self) -> None:
        from src.rag.v2.prompts import build_system_prompt
        p = build_system_prompt(intent="timeline")
        self.assertIn("Timeline mode", p)

    def test_compare_prompt_includes_compare_block(self) -> None:
        from src.rag.v2.prompts import build_system_prompt
        p = build_system_prompt(intent="compare")
        self.assertIn("Compare", p)

    def test_today_block_inserted(self) -> None:
        from src.rag.v2.prompts import build_system_prompt
        p = build_system_prompt(today=datetime(2026, 5, 16))
        self.assertIn("2026-05-16", p)


# =====================================================================
#  8. Backward compatibility — v1 path when all flags off
# =====================================================================

class TestBackwardCompat(unittest.TestCase):
    """When RAG_V2_ENABLED=false, the retriever path must behave exactly like v1."""

    def test_retriever_v1_path_unchanged_when_v2_pipeline_none(self) -> None:
        from src.rag.retriever import Retriever
        mongo = MagicMock()
        embedder = MagicMock()
        embedder.embed_query.return_value = [0.1] * 1024
        reranker = MagicMock()
        reranker.rerank.return_value = []

        # No chunks in Mongo.
        mongo.chunks.aggregate.return_value = iter([])

        r = Retriever(
            mongo=mongo, embedder=embedder, reranker=reranker,
            vector_index_name="test_idx",
            v2_pipeline=None,  # explicitly off
        )
        out = r.retrieve("hello world")
        self.assertEqual(out, [])
        # v1 path called embed_query exactly once.
        embedder.embed_query.assert_called_once()

    def test_retriever_falls_back_to_v1_when_v2_returns_empty(self) -> None:
        from src.rag.retriever import Retriever
        mongo = MagicMock()
        embedder = MagicMock()
        embedder.embed_query.return_value = [0.1] * 1024
        reranker = MagicMock()
        reranker.rerank.return_value = []
        mongo.chunks.aggregate.return_value = iter([])

        v2 = MagicMock()
        v2.settings.enabled = True
        v2.retrieve.return_value = []  # empty → fallback

        r = Retriever(
            mongo=mongo, embedder=embedder, reranker=reranker,
            vector_index_name="test_idx",
            v2_pipeline=v2,
        )
        r.retrieve("hi")
        # v2 was tried, then v1 path also ran (embed_query called).
        v2.retrieve.assert_called_once()
        embedder.embed_query.assert_called_once()

    def test_retriever_falls_back_to_v1_when_v2_raises(self) -> None:
        from src.rag.retriever import Retriever
        mongo = MagicMock()
        embedder = MagicMock()
        embedder.embed_query.return_value = [0.1] * 1024
        reranker = MagicMock()
        reranker.rerank.return_value = []
        mongo.chunks.aggregate.return_value = iter([])

        v2 = MagicMock()
        v2.settings.enabled = True
        v2.retrieve.side_effect = RuntimeError("v2 broke")

        r = Retriever(
            mongo=mongo, embedder=embedder, reranker=reranker,
            vector_index_name="test_idx",
            v2_pipeline=v2,
        )
        # MUST NOT raise.
        r.retrieve("hi")
        v2.retrieve.assert_called_once()
        embedder.embed_query.assert_called_once()


# =====================================================================
#  9. End-to-end orchestrator (mocked) — proves the full pipeline composes
# =====================================================================

class TestOrchestratorE2E(unittest.TestCase):
    def test_full_pipeline_with_all_flags_on(self) -> None:
        from src.rag.v2.orchestrator import V2Pipeline, V2Settings

        mongo = MagicMock()
        embedder = MagicMock()
        embedder.embed_query.return_value = [0.1] * 1024
        reranker = MagicMock()
        anthropic_client = MagicMock()

        # Mock query rewriter (no real LLM call).
        rewrite_response = MagicMock()
        rewrite_response.content = [MagicMock(
            type="text",
            text='{"hyde_answer":"a hypothetical answer","alt_queries":["alt 1","alt 2"]}',
        )]
        anthropic_client.messages.create.return_value = rewrite_response

        # Mock the vector channel — return 3 fake chunks.
        fake_chunks = [
            {"_id": f"c{i}", "filename": f"f{i}.pdf",
             "attachment_id": f"A{i}", "body": f"body {i}",
             "date": datetime(2026, 1, 1, tzinfo=timezone.utc),
             "score": 0.9 - i * 0.1}
            for i in range(3)
        ]
        # aggregate is called by vector channel; find().sort().limit() by BM25/filename.
        def _aggregate(pipeline, *a, **kw):
            return iter(fake_chunks)
        mongo.chunks.aggregate.side_effect = _aggregate
        # BM25 and filename channels return empty → fine; vector still works.
        empty_cursor = MagicMock()
        empty_cursor.sort.return_value.limit.return_value = iter([])
        mongo.chunks.find.return_value = empty_cursor
        # index check
        mongo.chunks.index_information.return_value = {}

        # Reranker keeps order, returns top_k.
        def _rerank(query, docs, top_k):
            return [{"index": i, "score": 0.5 - i * 0.1}
                    for i in range(min(top_k, len(docs)))]
        reranker.rerank.side_effect = _rerank

        v2 = V2Pipeline.build(
            mongo=mongo, embedder=embedder, reranker=reranker,
            anthropic_client=anthropic_client,
            vector_index_name="email_chunks_vector",
            v2_settings=V2Settings(
                enabled=True,
                hybrid_search=True,
                filename_lookup=True,
                hyde=True,
                multi_query=True,
                date_filters=True,
                parent_doc=True,
                temporal_diversity=True,
                adaptive_k=True,
                rescoring=True,
            ),
        )

        out = v2.retrieve("compare $450,000 across the Global Stipulation")
        # Pipeline should produce *some* chunks via the vector channel.
        self.assertGreater(len(out), 0)
        # Query rewriter was called (HyDE+multi-query both on).
        anthropic_client.messages.create.assert_called()


# =====================================================================
#  10. Settings load — make sure the v2 fields are wired
# =====================================================================

class TestSettingsLoad(unittest.TestCase):
    """Verify the helper functions in settings.py — env-independent."""

    def test_get_bool_helper(self) -> None:
        """The _get_bool helper must default to False when env var is missing."""
        import os
        from config.settings import _get_bool
        # Pick a name that definitely doesn't exist.
        self.assertFalse(_get_bool("RAG_V2_NOT_A_REAL_VAR_XYZ", default=False))
        self.assertTrue(_get_bool("RAG_V2_NOT_A_REAL_VAR_XYZ", default=True))

        os.environ["RAG_V2_TEST_VAR"] = "true"
        try:
            self.assertTrue(_get_bool("RAG_V2_TEST_VAR"))
        finally:
            del os.environ["RAG_V2_TEST_VAR"]

        os.environ["RAG_V2_TEST_VAR"] = "false"
        try:
            self.assertFalse(_get_bool("RAG_V2_TEST_VAR"))
        finally:
            del os.environ["RAG_V2_TEST_VAR"]

    def test_no_haiku_in_default_models(self) -> None:
        """User explicit requirement — never Haiku for query rewrite or memory."""
        from config.settings import Settings
        s = Settings.load()
        self.assertNotIn(
            "haiku", s.rag_v2_query_rewriter_model.lower(),
            "v2 must NEVER use Haiku — user explicit requirement",
        )
        self.assertNotIn("haiku", s.rag_v2_summary_model.lower())


# =====================================================================
#  11. Pre-Sprint-3 (Sprint 2.5) regression tests
# =====================================================================

class TestComprehensiveSignal(unittest.TestCase):
    """is_comprehensive() — comprehensive-intent detection."""

    def setUp(self) -> None:
        from src.rag.v2.query_understanding import extract_signals
        self.extract = extract_signals

    def test_all_keyword_triggers_comprehensive(self) -> None:
        s = self.extract("show me all references to $450,000 in the corpus")
        self.assertTrue(s.is_comprehensive(),
                        "'all references' must mark query comprehensive")

    def test_every_keyword_triggers_comprehensive(self) -> None:
        s = self.extract("list every email Phil sent in 2026")
        self.assertTrue(s.is_comprehensive())

    def test_complete_list_triggers_comprehensive(self) -> None:
        s = self.extract("give me a complete list of payments made")
        self.assertTrue(s.is_comprehensive())

    def test_four_plus_signals_triggers_comprehensive(self) -> None:
        # 4 distinct signals: 1 money, 1 filename, 1 email, 1 quoted phrase
        s = self.extract(
            'find $450,000 in stipulation.pdf sent by wheuer@example.com '
            'in "Global Settlement"'
        )
        self.assertTrue(
            s.is_comprehensive(),
            f"Expected 4+ signals to mark comprehensive, got "
            f"money={s.money_terms}, files={s.filenames}, "
            f"quoted={s.quoted_strings}, emails={s.emails}",
        )

    def test_simple_lookup_is_not_comprehensive(self) -> None:
        s = self.extract("who sent the email?")
        self.assertFalse(s.is_comprehensive())


class TestInterleavedOrdering(unittest.TestCase):
    """interleave_for_attention — best signals at the extremes."""

    def setUp(self) -> None:
        from src.rag.v2.ordering import interleave_for_attention
        self.interleave = interleave_for_attention

    def test_empty_list(self) -> None:
        self.assertEqual(self.interleave([]), [])

    def test_single_element(self) -> None:
        self.assertEqual(self.interleave([7]), [7])

    def test_two_elements_unchanged(self) -> None:
        self.assertEqual(self.interleave([1, 2]), [1, 2])

    def test_six_elements_interleave(self) -> None:
        """Best at extremes: positions 0 and -1 get the top 2 by rank."""
        result = self.interleave([1, 2, 3, 4, 5, 6])
        # Position 0 must be the strongest (rank #1).
        self.assertEqual(result[0], 1)
        # Position -1 must be rank #2 (second strongest).
        self.assertEqual(result[-1], 2)
        # Weakest item (rank #6) must end up in the middle area.
        middle = result[len(result) // 2 - 1: len(result) // 2 + 2]
        self.assertIn(6, middle, f"Worst chunk should be middle-ish, got {result}")

    def test_preserves_all_items(self) -> None:
        n = 20
        out = self.interleave(list(range(n)))
        self.assertEqual(sorted(out), list(range(n)),
                         "interleave must not drop or duplicate items")


class TestParentDocAdaptiveBudget(unittest.TestCase):
    """parent_document_expand — adaptive per-parent budget."""

    def test_per_parent_budget_scales_down(self) -> None:
        from src.rag.v2.parent_doc import _per_parent_budget
        # 1 parent → full budget.
        self.assertEqual(_per_parent_budget(1, single_budget=8000), 8000)
        # 2 parents → ~62.5% of single (= 5000).
        self.assertEqual(_per_parent_budget(2, single_budget=8000), 5000)
        # 3 parents → 50% (= 4000).
        self.assertEqual(_per_parent_budget(3, single_budget=8000), 4000)
        # 4 or 5 parents → 37.5% (= 3000).
        self.assertEqual(_per_parent_budget(4, single_budget=8000), 3000)
        self.assertEqual(_per_parent_budget(5, single_budget=8000), 3000)


class TestAdaptiveKThreeTiers(unittest.TestCase):
    """orchestrator._adaptive_k routes to the three tiers correctly."""

    def _build(self, k_simple=50, k_complex=70, k_comp=80):
        from src.rag.v2.orchestrator import V2Pipeline, V2Settings
        return V2Pipeline(
            mongo=MagicMock(), embedder=MagicMock(), reranker=MagicMock(),
            anthropic_client=MagicMock(), hybrid_searcher=MagicMock(),
            query_rewriter=MagicMock(),
            settings=V2Settings(
                enabled=True, adaptive_k=True,
                adaptive_k_simple=k_simple,
                adaptive_k_complex=k_complex,
                adaptive_k_comprehensive=k_comp,
            ),
        )

    def test_simple_query_picks_simple_k(self) -> None:
        from src.rag.v2.query_understanding import extract_signals
        v2 = self._build()
        sigs = extract_signals("who sent the email?")
        self.assertEqual(v2._adaptive_k(sigs), 50)

    def test_complex_query_picks_complex_k(self) -> None:
        from src.rag.v2.query_understanding import extract_signals
        v2 = self._build()
        sigs = extract_signals(
            "compare the figure across stipulations from 2024 to 2026"
        )
        self.assertEqual(v2._adaptive_k(sigs), 70)

    def test_comprehensive_query_picks_comprehensive_k(self) -> None:
        from src.rag.v2.query_understanding import extract_signals
        v2 = self._build()
        sigs = extract_signals(
            "list all references to $450,000 in the corpus"
        )
        self.assertEqual(v2._adaptive_k(sigs), 80)


class TestEvidenceCap(unittest.TestCase):
    """_cap_by_tokens enforces total-evidence ceiling."""

    def test_cap_drops_overflow(self) -> None:
        from src.rag.v2.orchestrator import _cap_by_tokens
        # Each chunk has ~25 tokens (100 chars / 4).
        chunks = [{"_id": str(i), "body": "x" * 100} for i in range(10)]
        out = _cap_by_tokens(chunks, max_tokens=100)
        # 4 chunks fit at most (4 * 25 = 100). We keep at least one.
        self.assertGreaterEqual(len(out), 1)
        self.assertLess(len(out), len(chunks))

    def test_cap_zero_disables(self) -> None:
        from src.rag.v2.orchestrator import _cap_by_tokens
        chunks = [{"_id": str(i), "body": "x" * 100} for i in range(10)]
        out = _cap_by_tokens(chunks, max_tokens=0)
        self.assertEqual(len(out), len(chunks))


class TestXmlSourcesFormat(unittest.TestCase):
    """chat._build_user_message with xml_sources=True emits XML SOURCES."""

    def _make_chunk(self):
        from src.rag.retriever import RetrievedChunk
        return RetrievedChunk(
            chunk_id="C1",
            text="The amount is $450,000 per Schedule A.",
            body="The amount is $450,000 per Schedule A.",
            source_type="attachment",
            email_id="E1",
            attachment_id="A1",
            filename="stip.pdf",
            page_start=12,
            page_end=12,
            date=datetime(2026, 1, 20),
            from_email="phil@example.com",
            to_emails=["bill@example.com"],
            subject="Re: Settlement",
            folder_path=None,
            vector_score=0.9,
            rerank_score=0.95,
        )

    def test_xml_format_wraps_in_doc_tag(self) -> None:
        from src.rag.chat import _build_user_message
        msg = _build_user_message(
            "where is $450,000?", [self._make_chunk()], xml_sources=True,
        )
        self.assertIn("<sources count=\"1\"", msg)
        self.assertIn("<doc id=\"1\"", msg)
        self.assertIn("filename=\"stip.pdf\"", msg)
        self.assertIn("$450,000", msg)
        self.assertIn("</sources>", msg)

    def test_xml_format_has_tail_reminder(self) -> None:
        from src.rag.chat import _build_user_message, _TAIL_REMINDER
        msg = _build_user_message(
            "where is $450,000?", [self._make_chunk()], xml_sources=True,
        )
        # Tail reminder must appear AFTER the question (best-practice
        # placement for long-context recall).
        q_idx = msg.find("<question>")
        r_idx = msg.find(_TAIL_REMINDER[:30])
        self.assertGreater(q_idx, 0)
        self.assertGreater(r_idx, q_idx,
                           "Reminder must come AFTER the question block")

    def test_plain_format_unchanged_when_xml_off(self) -> None:
        """Backward compat — xml_sources=False must keep the legacy format."""
        from src.rag.chat import _build_user_message
        msg = _build_user_message(
            "where is $450,000?", [self._make_chunk()], xml_sources=False,
        )
        self.assertIn("SOURCES (numbered, cite as [#N]):", msg)
        self.assertNotIn("<doc id=", msg)


# =====================================================================
# Runner
# =====================================================================

if __name__ == "__main__":
    # Ensure logger output doesn't drown the test results.
    import logging
    logging.basicConfig(level=logging.ERROR)
    unittest.main(verbosity=2)
