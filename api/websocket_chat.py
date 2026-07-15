"""
WebSocket chat handler.

Protocol (JSON messages):

  Client → Server:
    { "type": "question", "text": "...", "session_id": "...", "mode": "analysis"|"clean" }
    { "type": "interrupt", "session_id": "..." }   ← Sprint-4 stop button
    { "type": "ping" }

  Server → Client (streamed) — EVERY frame carries "session_id" so the UI can
  route it to the right conversation even when multiple answers stream at once:
    { "type": "start",        "session_id": "...", "agent_enabled": bool, ... }
    { "type": "agent_plan"|"agent_step"|"agent_done"|"agent_*", "session_id": "..." }
    { "type": "token",        "session_id": "...", "text": "..." }
    { "type": "sources",      "session_id": "...", "items": [...] }
    { "type": "verification", "session_id": "...", ... }
    { "type": "agent_trace",  "session_id": "...", "trace": {...} }
    { "type": "done",         "session_id": "..." }
    { "type": "error",        "session_id": "...", "message": "..." }
    { "type": "pong" }

Concurrency model (Sprint — multi-conversation):
  The receive loop NEVER blocks on answering. Each question is dispatched to a
  background asyncio task, so new questions (and interrupts) are read
  immediately while an answer streams. Each SESSION gets its own chat object
  (isolated history) and its own lock (questions within one session serialize;
  different sessions run concurrently). Answers are persisted to the DB on
  completion regardless of socket state, so a page reload never loses an
  in-flight answer — the finished answer is simply reloaded from the session.
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
    instance anywhere inside the payload would raise ``TypeError``.
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
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


async def _safe_send(ws: WebSocket, payload: Dict[str, Any]) -> bool:
    """Send a frame, tolerating a closed/broken socket (e.g. after a page
    reload). Returns True if delivered, False if the socket is gone. Never
    raises — so a disconnected client can't abort an in-flight answer before
    it is persisted to the DB."""
    try:
        await _send_json_safe(ws, payload)
        return True
    except Exception:
        return False


def _trim_agent_trace(trace: Dict[str, Any]) -> Dict[str, Any]:
    """Trim the agent_trace to a size suitable for persistence + replay."""
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
        ti = st.get("tool_input") or {}
        if isinstance(ti, dict):
            ti = {k: (v[:300] if isinstance(v, str) and len(v) > 300 else v)
                  for k, v in ti.items()}
            st["tool_input"] = ti
        if isinstance(st.get("summary"), str) and len(st["summary"]) > 800:
            st["summary"] = st["summary"][:797] + "..."
        trimmed_steps.append(st)
    out["steps"] = trimmed_steps
    return _json_safe(out)


def _hydrate_history(chat: Any, store: SessionStore, session_id: str, email: str) -> None:
    """Seed a fresh per-session chat with the conversation's prior turns from
    the DB so follow-up questions keep context."""
    try:
        doc = store.get_session(session_id, email)
        if not doc:
            return
        from src.rag.chat import Turn
        chat.history = []
        last_q = None
        for m in doc.get("messages", []):
            if m["role"] == "user":
                last_q = m["content"]
            elif m["role"] == "assistant" and last_q:
                chat.history.append(Turn(question=last_q, answer=m["content"]))
                last_q = None
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"history hydrate failed for {session_id}: {exc}")


async def _run_question(
    *,
    ws: WebSocket,
    store: SessionStore,
    email: str,
    chat: Any,
    lock: asyncio.Lock,
    loop: asyncio.AbstractEventLoop,
    session_id: str,
    question: str,
    ask_mode: str,
) -> None:
    """Process ONE question end-to-end. Runs as a background task so the
    receive loop stays free. Serialized per-session via `lock`. Persists the
    answer to the DB even if the socket has closed."""
    async with lock:
        try:
            store.append_message(session_id, email, role="user", content=question)
            doc = store.get_session(session_id, email)
            if doc and len(doc.get("messages", [])) <= 2:
                store.set_title(session_id, email, question[:80])

            agent_event_queue: asyncio.Queue = asyncio.Queue()
            agent_enabled = getattr(chat, "use_agent", False) and \
                getattr(chat, "agent_v2_pipeline", None) is not None

            def _on_agent_event(event_type: str, payload: Dict[str, Any]) -> None:
                try:
                    loop.call_soon_threadsafe(
                        agent_event_queue.put_nowait, (event_type, payload))
                except RuntimeError:
                    pass

            chat.on_agent_event = _on_agent_event if agent_enabled else None

            await _safe_send(ws, {
                "type": "start", "mode": "normal", "chunks": 0,
                "session_id": session_id, "agent_enabled": agent_enabled,
            })

            ask_task = loop.run_in_executor(
                None, lambda: chat.ask(question, mode=ask_mode))
            try:
                while not ask_task.done():
                    try:
                        et, p = await asyncio.wait_for(agent_event_queue.get(), timeout=0.5)
                        await _safe_send(ws, {"type": et, **p, "session_id": session_id})
                    except asyncio.TimeoutError:
                        pass
                while not agent_event_queue.empty():
                    et, p = agent_event_queue.get_nowait()
                    await _safe_send(ws, {"type": et, **p, "session_id": session_id})
                turn = await ask_task
            finally:
                chat.on_agent_event = None

            mode = "timeline" if any(
                "timeline" in (c.text or "").lower() for c in turn.chunks[:1]
            ) else "normal"

            # Stream answer word-by-word (session-tagged + socket-safe).
            words = (turn.answer or "").split(" ")
            buf = ""
            for i, word in enumerate(words):
                buf += ("" if i == 0 else " ") + word
                if len(buf) >= 6 or i == len(words) - 1:
                    await _safe_send(ws, {"type": "token", "text": buf, "session_id": session_id})
                    buf = ""
                    await asyncio.sleep(0.012)

            # Sources (+ per-chunk verification state + bodies for the drawer).
            verdicts_by_chunk: Dict[int, List[Dict[str, Any]]] = {}
            for v in (getattr(turn, "fact_verdicts", None) or []):
                cid = v.get("source_chunk_id")
                if isinstance(cid, int):
                    verdicts_by_chunk.setdefault(cid, []).append(v)

            sources = []
            for i, c in enumerate(turn.chunks):
                idx = i + 1
                item = _chunk_to_source_item(c, idx)
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
            await _safe_send(ws, {"type": "sources", "items": sources, "session_id": session_id})

            verification_payload: Dict[str, Any] | None = None
            if getattr(turn, "verification_outcome", None):
                verification_payload = {
                    "outcome": turn.verification_outcome,
                    "n_facts": len(turn.fact_verdicts),
                    "n_verified": sum(
                        1 for v in turn.fact_verdicts
                        if v.get("verdict") == "VERIFIED"),
                    "facts": turn.facts,
                    "verdicts": turn.fact_verdicts,
                }
                await _safe_send(ws, {"type": "verification", "session_id": session_id,
                                      **verification_payload})

            agent_trace_payload = None
            if getattr(turn, "agent_trace", None):
                agent_trace_payload = _trim_agent_trace(turn.agent_trace)
                await _safe_send(ws, {"type": "agent_trace", "trace": agent_trace_payload,
                                      "session_id": session_id})

            await _safe_send(ws, {"type": "done", "session_id": session_id})

            # DURABLE save — happens even if the socket closed mid-answer, so a
            # page reload reloads the finished answer from the session.
            store.append_message(
                session_id, email, role="assistant", content=turn.answer,
                chunks_used=len(turn.chunks), mode=mode, sources=sources,
                verification=verification_payload, agent_trace=agent_trace_payload)
        except Exception as exc:  # noqa: BLE001
            logger.exception(f"question processing error [{session_id}]: {exc}")
            await _safe_send(ws, {"type": "error", "message": str(exc),
                                  "session_id": session_id})


async def handle_chat_ws(ws: WebSocket, store: SessionStore) -> None:
    await ws.accept()
    email: str | None = None
    loop = asyncio.get_running_loop()
    # Per-connection, per-session state.
    chats: Dict[str, Any] = {}
    locks: Dict[str, asyncio.Lock] = {}
    tasks: set = set()

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

        # ── step 2: message loop (NON-BLOCKING — dispatches to tasks) ────────
        while True:
            raw = await ws.receive_json()
            msg_type = raw.get("type", "")

            if msg_type == "ping":
                await _safe_send(ws, {"type": "pong"})
                continue

            # Interrupt targets the running agent for a SPECIFIC session.
            if msg_type == "interrupt":
                sid = raw.get("session_id") or ""
                c = chats.get(sid)
                if c is not None:
                    budget = c.get_current_budget()
                    if budget is not None:
                        budget.interrupt_requested = True
                        logger.info(f"WS interrupt set on running agent [{sid}]")
                continue

            if msg_type != "question":
                continue

            question = (raw.get("text") or "").strip()
            if not question:
                await _safe_send(ws, {"type": "error", "message": "Empty question"})
                continue

            session_id = raw.get("session_id") or ""
            if not session_id:
                session_id = store.create_session(email)
            ask_mode = "clean" if str(raw.get("mode") or "").lower() == "clean" else "analysis"

            # Per-session chat (isolated history) + per-session lock.
            chat = chats.get(session_id)
            if chat is None:
                chat = make_chat()
                _hydrate_history(chat, store, session_id, email)
                chats[session_id] = chat
            lock = locks.get(session_id)
            if lock is None:
                lock = asyncio.Lock()
                locks[session_id] = lock

            # Dispatch — do NOT await, so the receive loop keeps reading.
            task = asyncio.create_task(_run_question(
                ws=ws, store=store, email=email, chat=chat, lock=lock, loop=loop,
                session_id=session_id, question=question, ask_mode=ask_mode))
            tasks.add(task)
            task.add_done_callback(tasks.discard)

    except WebSocketDisconnect:
        # Do NOT cancel in-flight tasks — let them finish and persist to the DB
        # so a reload can reload the completed answer.
        n = len([t for t in tasks if not t.done()])
        logger.info(f"WS disconnected: {email} ({n} in-flight answer(s) will finish & persist)")
    except asyncio.TimeoutError:
        await _safe_send(ws, {"type": "error", "message": "Auth timeout"})
        await ws.close(code=4002)
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"WS error: {exc}")
        await _safe_send(ws, {"type": "error", "message": "Internal server error"})
