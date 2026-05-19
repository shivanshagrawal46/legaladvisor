"""
Chat session storage in MongoDB.

Collection: chat_sessions
Schema per document:
  {
    _id:          ObjectId
    session_id:   str  (uuid4)
    user_email:   str
    title:        str  (first question, truncated to 60 chars)
    created_at:   datetime
    updated_at:   datetime
    messages: [
      { role: "user"|"assistant", content: str, timestamp: datetime,
        chunks_used: int, mode: "normal"|"timeline" }
    ]
  }
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pymongo import DESCENDING

from src.db.mongo import MongoClientWrapper


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SessionStore:
    def __init__(self, mongo: MongoClientWrapper) -> None:
        self.col = mongo.db["chat_sessions"]
        self.col.create_index("session_id", unique=True)
        self.col.create_index([("user_email", 1), ("updated_at", DESCENDING)])

    # ── create ────────────────────────────────────────────────────────────────

    def create_session(self, user_email: str) -> str:
        sid = str(uuid.uuid4())
        now = _now()
        self.col.insert_one({
            "session_id": sid,
            "user_email": user_email,
            "title": "New conversation",
            "created_at": now,
            "updated_at": now,
            "messages": [],
        })
        return sid

    # ── read ──────────────────────────────────────────────────────────────────

    def get_session(self, session_id: str, user_email: str) -> Optional[Dict[str, Any]]:
        doc = self.col.find_one(
            {"session_id": session_id, "user_email": user_email},
            {"_id": 0},
        )
        return doc

    def list_sessions(self, user_email: str, limit: int = 50) -> List[Dict[str, Any]]:
        cursor = self.col.find(
            {"user_email": user_email},
            {"_id": 0, "messages": 0},
            sort=[("updated_at", DESCENDING)],
            limit=limit,
        )
        return list(cursor)

    # ── write ─────────────────────────────────────────────────────────────────

    def append_message(
        self,
        session_id: str,
        user_email: str,
        *,
        role: str,
        content: str,
        chunks_used: int = 0,
        mode: str = "normal",
    ) -> None:
        msg = {
            "role": role,
            "content": content,
            "timestamp": _now(),
            "chunks_used": chunks_used,
            "mode": mode,
        }
        update: Dict[str, Any] = {
            "$push": {"messages": msg},
            "$set": {"updated_at": _now()},
        }
        self.col.update_one(
            {"session_id": session_id, "user_email": user_email},
            update,
        )

    def set_title(self, session_id: str, user_email: str, title: str) -> None:
        self.col.update_one(
            {"session_id": session_id, "user_email": user_email},
            {"$set": {"title": title[:80]}},
        )

    def delete_session(self, session_id: str, user_email: str) -> bool:
        result = self.col.delete_one(
            {"session_id": session_id, "user_email": user_email}
        )
        return result.deleted_count > 0
