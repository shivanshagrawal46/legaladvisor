"""
WebSocket chat handler.

Protocol (JSON messages):

  Client → Server:
    { "type": "question", "text": "...", "session_id": "..." }
    { "type": "ping" }

  Server → Client (streamed):
    { "type": "start",  "mode": "normal"|"timeline", "chunks": N }
    { "type": "token",  "text": "..." }          ← one per word/phrase
    { "type": "sources","items": [ {title,date,type,page,score}, ... ] }
    { "type": "done",   "session_id": "..." }
    { "type": "error",  "message": "..." }
    { "type": "pong" }

The answer is streamed word-by-word so the UI can render progressively.
We split Claude's full response into tokens after receiving the complete
answer (Anthropic SDK non-streaming) — this gives a typewriter effect
without requiring an async streaming client.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict

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
            try:
                turn = chat.ask(question)
            except Exception as exc:
                logger.exception("RAG error")
                await ws.send_json({"type": "error", "message": str(exc)})
                continue

            mode = "timeline" if any(
                "timeline" in (c.text or "").lower()
                for c in turn.chunks[:1]
            ) else "normal"

            # Send start frame.
            await ws.send_json({
                "type": "start",
                "mode": mode,
                "chunks": len(turn.chunks),
                "session_id": session_id,
            })

            # Stream answer tokens.
            await _stream_text(ws, turn.answer)

            # Send sources.
            sources = [
                _chunk_to_source_item(c, i + 1)
                for i, c in enumerate(turn.chunks)
            ]
            await ws.send_json({"type": "sources", "items": sources})

            # Done frame.
            await ws.send_json({"type": "done", "session_id": session_id})

            # Save assistant reply to DB.
            store.append_message(
                session_id, email,
                role="assistant",
                content=turn.answer,
                chunks_used=len(turn.chunks),
                mode=mode,
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
