"""
WebSocket chat handler.

Protocol (JSON messages):

  Client → Server:
    { "type": "question", "text": "...", "session_id": "..." }
    { "type": "interrupt", "session_id": "..." }   ← Sprint-4 stop button
    { "type": "ping" }

  Server → Client (streamed):
    { "type": "start",        "mode": "normal"|"timeline", "chunks": N,
                              "agent_enabled": true|false }
    { "type": "agent_plan",   "query": "...", "budget": {...},
                              "tools": [name, ...] }   ← Sprint-4
    { "type": "agent_step",   "step_num": N, "type": "...", "tool_name": "...",
                              "tool_input": {...}, "summary": "...",
                              "new_chunk_indices": [...], "elapsed_ms": N,
                              "tokens": {...} }        ← Sprint-4 (one per step)
    { "type": "agent_done",   "outcome": "...", "n_facts": N, ... }  ← Sprint-4
    { "type": "token",        "text": "..." }            ← one per word/phrase
    { "type": "sources",      "items": [ {index,title,date,type,page,
                                          rerank_score,body,body_truncated,
                                          verified_facts?[]}, ... ] }
    { "type": "verification", "outcome": "...", "n_facts": N,
                              "n_verified": N, "facts": [...],
                              "verdicts": [...] }       ← Sprint-3-finish
    { "type": "done",         "session_id": "..." }
    { "type": "error",        "message": "..." }
    { "type": "pong" }

The answer is streamed word-by-word so the UI can render progressively.
We split Claude's full response into tokens after receiving the complete
answer (Anthropic SDK non-streaming) — this gives a typewriter effect
without requiring an async streaming client.
"""
from __future__ import annotations

import asyncio
import json
from datetime import date, datetime
from typing import Any, Dict, List

from fastapi import WebSocket, WebSocketDisconnect

from api.auth import SECRET_KEY, ALGORITHM
from api.sessions import SessionStore
from api.rag_singleton import get_settings, make_chat
from jose import JWTError, jwt
from src.utils.logger import logger

_USERS = {"rakeshsir@mtreh.com"}  # authorised set


def _decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def _chunk_to_source_item(c: Any, idx: int) -> Dict[str, Any]:
    date_str = ""
    if c.date:
        try:
            date_str = c.date.strftime("%Y-%m-%d")
        except Exception:
            date_str = str(c.date)

    if c.source_type == "attachment":
        title = c.filename or "Attachment"
        kind = "attachment"
        page = f"p. {c.page_start}" if c.page_start else ""
    else:
        title = c.subject or "Email"
        kind = "email"
        page = ""

    return {
        "index": idx,
        "title": title,
        "date": date_str,
        "type": kind,
        "page": page,
        "from_email": c.from_email or "",
        "rerank_score": round(c.rerank_score, 3) if c.rerank_score is not None else None,
    }


def _json_safe(obj: Any) -> Any:
    """
    Recursively convert a payload into something the stdlib ``json`` module
    can serialize. ``starlette.WebSocket.send_json`` uses plain ``json.dumps``
    with no ``default=`` hook, so any ``datetime`` / ``date`` / ``ObjectId``
    instance anywhere inside the payload would raise ``TypeError``. Agent
    traces (``BudgetTracker.started_at``, ``AgentStep.started_at`` …) and
    verifier results (``VerificationReport.generated_at``) both ship with
    datetime fields, so we normalise them here at the API boundary.
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    # Last-resort: anything with an .isoformat() is probably a date-like.
    if hasattr(obj, "isoformat") and callable(obj.isoformat):
        try:
            return obj.isoformat()
        except Exception:
            pass
    return obj


async def _send_json_safe(ws: WebSocket, payload: Dict[str, Any]) -> None:
    """Drop-in safer alternative to ``ws.send_json`` for payloads that may
    contain datetimes or other non-JSON-native primitives."""
    await ws.send_text(json.dumps(_json_safe(payload), separators=(",", ":"), ensure_ascii=False))


def _trim_agent_trace(trace: Dict[str, Any]) -> Dict[str, Any]:
    """
    Trim the agent_trace to a size suitable for persistence and history
    replay. We drop nothing important — just cap any unbounded fields
    (very long tool_input strings, etc.) and remove the per-step
    duplicate of full_payload that the agent already streamed.

    Datetime fields are converted to ISO strings via :func:`_json_safe` so
    the resulting dict is JSON-serialisable for both WebSocket streaming
    and MongoDB persistence (where BSON does accept datetime, but mixed
    nesting is safer as strings for cross-component reuse).
    """
    if not isinstance(trace, dict):
        return trace
    out = dict(trace)
    steps = out.get("steps") or []
    trimmed_steps = []
    for s in steps:
        if not isinstance(s, dict):
            trimmed_steps.append(s)
            continue
        st = dict(s)
        # tool_input can contain long search queries; cap each value.
        ti = st.get("tool_input") or {}
        if isinstance(ti, dict):
            ti = {k: (v[:300] if isinstance(v, str) and len(v) > 300 else v)
                  for k, v in ti.items()}
            st["tool_input"] = ti
        # summary is usually short; cap defensively.
        if isinstance(st.get("summary"), str) and len(st["summary"]) > 800:
            st["summary"] = st["summary"][:797] + "..."
        trimmed_steps.append(st)
    out["steps"] = trimmed_steps
    return _json_safe(out)


async def _stream_text(ws: WebSocket, text: str) -> None:
    """Send text word-by-word with a tiny delay for typewriter effect."""
    words = text.split(" ")
    buf = ""
    for i, word in enumerate(words):
        buf += ("" if i == 0 else " ") + word
        if len(buf) >= 6 or i == len(words) - 1:
            await ws.send_json({"type": "token", "text": buf})
            buf = ""
            await asyncio.sleep(0.012)


async def handle_chat_ws(ws: WebSocket, store: SessionStore) -> None:
    await ws.accept()
    email: str | None = None
    chat = None

    try:
        # ── step 1: authentication handshake ────────────────────────────────
        auth_msg = await asyncio.wait_for(ws.receive_json(), timeout=30.0)
        token = auth_msg.get("token", "")
        email = _decode_token(token)
        if not email or email not in _USERS:
            await ws.send_json({"type": "error", "message": "Unauthorised"})
            await ws.close(code=4001)
            return

        await ws.send_json({"type": "auth_ok", "email": email})
        logger.info(f"WS auth OK: {email}")

        # ── step 2: initialise per-session chat ──────────────────────────────
        chat = make_chat()
        s = get_settings()

        # Restore history from DB if session_id provided later.
        current_session_id: str | None = None

        # ── step 3: message loop ─────────────────────────────────────────────
        while True:
            raw = await ws.receive_json()
            msg_type = raw.get("type", "")

            if msg_type == "ping":
                await ws.send_json({"type": "pong"})
                continue

            # Interrupt — out-of-band stop signal from the user. We
            # set the flag on the current chat's running budget. The
            # agent loop polls budget.exhausted() before each iteration
            # so the answer terminates at the next safe point.
            if msg_type == "interrupt":
                if chat is not None:
                    budget = chat.get_current_budget()
                    if budget is not None:
                        budget.interrupt_requested = True
                        logger.info("WS interrupt set on running agent")
                continue

            if msg_type != "question":
                continue

            question = (raw.get("text") or "").strip()
            session_id = raw.get("session_id") or ""

            if not question:
                await ws.send_json({"type": "error", "message": "Empty question"})
                continue

            # Create session if not provided.
            if not session_id:
                session_id = store.create_session(email)

            # If the session changed (or this is the first question on the
            # WS), wipe and re-hydrate chat.history from the DB. Without
            # this, switching sessions in the UI leaks context from the
            # previous conversation into the new one's prompts.
            if session_id != current_session_id:
                chat.history = []
                doc = store.get_session(session_id, email)
                if doc:
                    from src.rag.chat import Turn
                    last_q = None
                    for m in doc.get("messages", []):
                        if m["role"] == "user":
                            last_q = m["content"]
                        elif m["role"] == "assistant" and last_q:
                            chat.history.append(
                                Turn(question=last_q, answer=m["content"])
                            )
                            last_q = None
                current_session_id = session_id

            # Save user message to DB.
            store.append_message(
                session_id, email, role="user", content=question
            )

            # Set session title from first question.
            doc = store.get_session(session_id, email)
            if doc and len(doc.get("messages", [])) <= 2:
                store.set_title(session_id, email, question[:80])

            # ── RAG call ──────────────────────────────────────────────────────
            # The agent (if enabled) is synchronous + long-running. We run
            # it on the default executor and have it stream events back
            # through an asyncio.Queue so the WS can forward them live.
            loop = asyncio.get_running_loop()
            agent_event_queue: asyncio.Queue = asyncio.Queue()
            agent_enabled = getattr(chat, "use_agent", False) and \
                            getattr(chat, "agent_v2_pipeline", None) is not None

            def _on_agent_event(event_type: str, payload: Dict[str, Any]) -> None:
                # Called from the worker thread. Hand off to the loop
                # via call_soon_threadsafe (Queue.put_nowait is loop-thread-only).
                try:
                    loop.call_soon_threadsafe(
                        agent_event_queue.put_nowait, (event_type, payload)
                    )
                except RuntimeError:
                    pass  # loop closed mid-shutdown

            # Tell the chat object where to send agent events for THIS call.
            if agent_enabled:
                chat.on_agent_event = _on_agent_event
            else:
                chat.on_agent_event = None

            # Send the start frame BEFORE kicking off so the FE can
            # mount the AgentReasoningPanel immediately. We can't yet
            # know the mode until retrieval runs, but `start` doesn't
            # have to be perfect.
            await ws.send_json({
                "type": "start",
                "mode": "normal",
                "chunks": 0,
                "session_id": session_id,
                "agent_enabled": agent_enabled,
            })

            # Kick the synchronous chat.ask() onto a thread executor.
            ask_task = loop.run_in_executor(None, chat.ask, question)

            # Pump agent events out to the WS until ask_task completes.
            try:
                while not ask_task.done():
                    try:
                        event_type, payload = await asyncio.wait_for(
                            agent_event_queue.get(), timeout=0.5
                        )
                        await ws.send_json({"type": event_type, **payload})
                    except asyncio.TimeoutError:
                        pass
                # Drain any final events the agent emitted after returning.
                while not agent_event_queue.empty():
                    event_type, payload = agent_event_queue.get_nowait()
                    await ws.send_json({"type": event_type, **payload})
                turn = await ask_task
            except Exception as exc:
                logger.exception("RAG error")
                await ws.send_json({"type": "error", "message": str(exc)})
                continue
            finally:
                # Clear the per-question callback to avoid leakage into
                # later questions' calls.
                if chat is not None:
                    chat.on_agent_event = None

            mode = "timeline" if any(
                "timeline" in (c.text or "").lower()
                for c in turn.chunks[:1]
            ) else "normal"

            # Stream answer tokens.
            await _stream_text(ws, turn.answer)

            # Send sources, optionally enriched with per-chunk verification
            # state if the verified-answer pipeline ran. We also build a
            # `chunk_bodies` map so the frontend evidence drawer can show
            # the FULL chunk text on demand (one round-trip total).
            verdicts_by_chunk: Dict[int, List[Dict[str, Any]]] = {}
            for v in (getattr(turn, "fact_verdicts", None) or []):
                cid = v.get("source_chunk_id")
                if isinstance(cid, int):
                    verdicts_by_chunk.setdefault(cid, []).append(v)

            sources = []
            for i, c in enumerate(turn.chunks):
                idx = i + 1
                item = _chunk_to_source_item(c, idx)
                # Always ship the chunk body so the evidence drawer can
                # render the source text. Capped to 8000 chars to keep
                # the WS frame reasonable; truncation flagged for UI.
                body = (getattr(c, "body", None) or getattr(c, "text", None) or "")
                if len(body) > 8000:
                    item["body"] = body[:8000]
                    item["body_truncated"] = True
                else:
                    item["body"] = body
                    item["body_truncated"] = False
                vs = verdicts_by_chunk.get(idx)
                if vs:
                    item["verified_facts"] = [
                        {
                            "fact_id": v.get("fact_id"),
                            "claim": v.get("claim"),
                            "verbatim_quote": v.get("verbatim_quote"),
                            "matched_span": v.get("matched_span"),
                            "verdict": v.get("verdict"),
                            "score": v.get("score"),
                            "reason": v.get("reason"),
                        }
                        for v in vs
                    ]
                sources.append(item)
            await ws.send_json({"type": "sources", "items": sources})

            # Optional: full verification summary (frontend can render
            # global badge "X/Y verified" without iterating sources).
            verification_payload: Dict[str, Any] | None = None
            if getattr(turn, "verification_outcome", None):
                verification_payload = {
                    "outcome": turn.verification_outcome,
                    "n_facts": len(turn.fact_verdicts),
                    "n_verified": sum(
                        1 for v in turn.fact_verdicts
                        if v.get("verdict") == "VERIFIED"
                    ),
                    "facts": turn.facts,
                    "verdicts": turn.fact_verdicts,
                }
                await _send_json_safe(ws, {"type": "verification", **verification_payload})

            # Sprint 4: trim the agent trace before persisting/streaming
            # to keep document size sane. Step summaries already contain
            # everything the FE panel needs.
            agent_trace_payload = None
            if getattr(turn, "agent_trace", None):
                agent_trace_payload = _trim_agent_trace(turn.agent_trace)
                # Emit a final `agent_trace` frame so the frontend can
                # snapshot the complete reasoning panel (it built it
                # incrementally from agent_step events, but this frame
                # gives a deterministic final state including the
                # forced-reason / outcome).
                await _send_json_safe(ws, {
                    "type": "agent_trace",
                    "trace": agent_trace_payload,
                })

            # Done frame.
            await ws.send_json({"type": "done", "session_id": session_id})

            # Save assistant reply to DB — including sources + verification
            # so history replay shows the citation chips + evidence panel.
            store.append_message(
                session_id, email,
                role="assistant",
                content=turn.answer,
                chunks_used=len(turn.chunks),
                mode=mode,
                sources=sources,
                verification=verification_payload,
                agent_trace=agent_trace_payload,
            )

    except WebSocketDisconnect:
        logger.info(f"WS disconnected: {email}")
    except asyncio.TimeoutError:
        await ws.send_json({"type": "error", "message": "Auth timeout"})
        await ws.close(code=4002)
    except Exception as exc:
        logger.exception(f"WS error: {exc}")
        try:
            await ws.send_json({"type": "error", "message": "Internal server error"})
        except Exception:
            pass
