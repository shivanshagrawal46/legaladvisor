"""
FastAPI server — Legal Advisor RAG backend.

Endpoints:
  POST  /api/auth/login          → JWT token
  GET   /api/auth/me             → current user info
  GET   /api/sessions            → list user's chat sessions
  POST  /api/sessions            → create new session
  GET   /api/sessions/{id}       → get full session with messages
  DELETE /api/sessions/{id}      → delete session
  WS    /ws/chat                 → streaming chat (JWT in first message)

Run with:
  python server.py
  or
  uvicorn server:app --host 0.0.0.0 --port 8000 --reload
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import WebSocket
from pydantic import BaseModel
from typing import List, Optional

from api.auth import (
    Token, User,
    authenticate_user,
    create_access_token,
    get_current_user,
)
from api.sessions import SessionStore
from api.rag_singleton import get_mongo
from api.websocket_chat import handle_chat_ws

# ── app ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Legal Advisor RAG API",
    description="Fraud investigation assistant backed by email corpus + Claude Sonnet 4.6",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        # Production server — raw IP + frontend port
        "http://139.59.39.65:5015",
        "http://139.59.39.65",
    ],
    # Any localhost / 127.0.0.1 port in dev (Vite may pick 5174, 5175, … if 5173 is busy)
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── session store (initialised lazily on first request) ───────────────────────
_store: Optional[SessionStore] = None


def get_store() -> SessionStore:
    global _store
    if _store is None:
        _store = SessionStore(get_mongo())
    return _store


# ── auth routes ───────────────────────────────────────────────────────────────

@app.post("/api/auth/login", response_model=Token)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form.username, form.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": user["email"]})
    return Token(
        access_token=token,
        token_type="bearer",
        name=user["name"],
        email=user["email"],
    )


@app.get("/api/auth/me", response_model=User)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


# ── session routes ────────────────────────────────────────────────────────────

class SessionOut(BaseModel):
    session_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: Optional[int] = None


class NewSessionOut(BaseModel):
    session_id: str


@app.get("/api/sessions", response_model=List[SessionOut])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    store: SessionStore = Depends(get_store),
):
    docs = store.list_sessions(current_user.email)
    out = []
    for d in docs:
        out.append(SessionOut(
            session_id=d["session_id"],
            title=d.get("title", "Conversation"),
            created_at=d["created_at"].isoformat(),
            updated_at=d["updated_at"].isoformat(),
        ))
    return out


@app.post("/api/sessions", response_model=NewSessionOut, status_code=201)
async def create_session(
    current_user: User = Depends(get_current_user),
    store: SessionStore = Depends(get_store),
):
    sid = store.create_session(current_user.email)
    return NewSessionOut(session_id=sid)


@app.get("/api/sessions/{session_id}")
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    store: SessionStore = Depends(get_store),
):
    doc = store.get_session(session_id, current_user.email)
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    return doc


@app.delete("/api/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    store: SessionStore = Depends(get_store),
):
    deleted = store.delete_session(session_id, current_user.email)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")


# ── websocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket):
    store = get_store()
    await handle_chat_ws(websocket, store)


# ── health ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "model": "claude-sonnet-4-6"}


# ── run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
