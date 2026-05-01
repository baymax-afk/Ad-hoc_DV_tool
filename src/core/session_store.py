import uuid
import time
from typing import Any, Optional

from src.core.config import settings
from src.core.exceptions import SessionNotFoundError


class InMemorySessionStore:
    """Simple in-memory store for MVP. Replace with Redis for production."""

    def __init__(self, ttl: int = settings.session_ttl_seconds):
        self._store: dict[str, dict] = {}
        self._ttl = ttl

    def create(self) -> str:
        session_id = str(uuid.uuid4())
        self._store[session_id] = {"created_at": time.time(), "data": {}}
        return session_id

    def get(self, session_id: str) -> dict:
        self._evict_expired()
        if session_id not in self._store:
            raise SessionNotFoundError(f"Session '{session_id}' not found or expired.")
        return self._store[session_id]["data"]

    def set(self, session_id: str, key: str, value: Any) -> None:
        self._evict_expired()
        if session_id not in self._store:
            raise SessionNotFoundError(f"Session '{session_id}' not found or expired.")
        self._store[session_id]["data"][key] = value

    def delete(self, session_id: str) -> None:
        self._store.pop(session_id, None)

    def exists(self, session_id: str) -> bool:
        self._evict_expired()
        return session_id in self._store

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [sid for sid, v in self._store.items() if now - v["created_at"] > self._ttl]
        for sid in expired:
            del self._store[sid]


session_store = InMemorySessionStore()
