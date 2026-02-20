from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
import threading
import time

import numpy as np


@dataclass
class StoredChunk:
    chunk_id: str
    file_path: str
    text: str
    vector: np.ndarray  # shape: (d,), expected float32 and normalized


class MemoryStore:
    """
    Per-session in-memory store. Thread-safe.
    Overwrite semantics per file_path via upsert_file_chunks.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._chunks: List[StoredChunk] = []
        self._by_path: Dict[str, List[int]] = {}

    def clear(self) -> None:
        with self._lock:
            self._chunks = []
            self._by_path = {}

    def upsert_file_chunks(self, file_path: str, chunks: List[StoredChunk]) -> None:
        """
        Overwrite semantics: remove old chunks for file_path, then add new ones.
        """
        with self._lock:
            old_idxs = set(self._by_path.get(file_path, []))
            if old_idxs:
                self._chunks = [c for i, c in enumerate(self._chunks) if i not in old_idxs]
                self._rebuild_index_unlocked()

            start = len(self._chunks)
            self._chunks.extend(chunks)
            self._by_path[file_path] = list(range(start, start + len(chunks)))

    def all_chunks(self) -> List[StoredChunk]:
        with self._lock:
            return list(self._chunks)

    def stats(self) -> dict:
        with self._lock:
            return {"files": len(self._by_path), "chunks": len(self._chunks)}

    def _rebuild_index_unlocked(self) -> None:
        self._by_path = {}
        for idx, ch in enumerate(self._chunks):
            self._by_path.setdefault(ch.file_path, []).append(idx)


# ---------------------------
# Session-scoped registry
# ---------------------------

_STORES_LOCK = threading.Lock()
STORES: Dict[str, MemoryStore] = {}

# session metadata for eviction / monitoring
SESSION_LAST_SEEN: Dict[str, float] = {}
SESSION_CREATED_AT: Dict[str, float] = {}


def get_store(session_id: str) -> MemoryStore:
    """
    Get or create the MemoryStore for a given session_id.
    """
    sid = (session_id or "").strip()
    if not sid:
        raise ValueError("session_id is required")

    now = time.time()
    with _STORES_LOCK:
        store = STORES.get(sid)
        if store is None:
            store = MemoryStore()
            STORES[sid] = store
            SESSION_CREATED_AT[sid] = now
        SESSION_LAST_SEEN[sid] = now
        return store


def touch_session(session_id: str) -> None:
    sid = (session_id or "").strip()
    if not sid:
        return
    with _STORES_LOCK:
        if sid in STORES:
            SESSION_LAST_SEEN[sid] = time.time()


def clear_session(session_id: str) -> None:
    """
    Clears the session store contents but keeps the session entry alive.
    """
    store = get_store(session_id)
    store.clear()
    touch_session(session_id)


def delete_session(session_id: str) -> None:
    """
    Removes session from registry entirely.
    """
    sid = (session_id or "").strip()
    if not sid:
        return
    with _STORES_LOCK:
        STORES.pop(sid, None)
        SESSION_LAST_SEEN.pop(sid, None)
        SESSION_CREATED_AT.pop(sid, None)


def evict_expired(ttl_seconds: int) -> int:
    """
    Evict sessions not seen within ttl_seconds. Returns evicted count.
    """
    if ttl_seconds <= 0:
        return 0

    now = time.time()
    to_evict: List[str] = []

    with _STORES_LOCK:
        for sid, last in SESSION_LAST_SEEN.items():
            if now - last > ttl_seconds:
                to_evict.append(sid)

        for sid in to_evict:
            STORES.pop(sid, None)
            SESSION_LAST_SEEN.pop(sid, None)
            SESSION_CREATED_AT.pop(sid, None)

    return len(to_evict)


def stats_all() -> dict:
    with _STORES_LOCK:
        return {
            "sessions": len(STORES),
            "last_seen_count": len(SESSION_LAST_SEEN),
        }