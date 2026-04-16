from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import threading
import time

import numpy as np

from ..utils.bm25 import BM25Index


@dataclass
class StoredChunk:
    chunk_id: str
    file_path: str
    text: str
    vector: np.ndarray  # shape: (d,), expected float32 and normalized
    chunk_index: int = 0          # position within the file's chunks
    total_chunks: int = 0         # total chunks for this file
    heading_breadcrumb: str = ""  # e.g. "## Arch > ### DB"
    section_id: str = ""          # parent section ID for expansion
    doc_type: str = ""            # e.g. "markdown", "code", "text"
    title: str = ""               # document title
    mtime: float = 0.0            # last-modified timestamp


class MemoryStore:
    """
    Per-session in-memory store. Thread-safe.
    Overwrite semantics per file_path via upsert_file_chunks.
    Maintains both a vector index and a BM25 keyword index.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._chunks: List[StoredChunk] = []
        self._by_path: Dict[str, List[int]] = {}
        self._bm25 = BM25Index()
        self._bm25_dirty = True
        self._section_texts: Dict[str, str] = {}  # section_id -> full text

    def clear(self) -> None:
        with self._lock:
            self._chunks = []
            self._by_path = {}
            self._bm25 = BM25Index()
            self._bm25_dirty = True
            self._section_texts = {}

    def upsert_file_chunks(
        self,
        file_path: str,
        chunks: List[StoredChunk],
        section_texts: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Overwrite semantics: remove old chunks for file_path, then add new ones.
        Optionally store section texts for parent expansion.
        """
        with self._lock:
            old_idxs = set(self._by_path.get(file_path, []))
            if old_idxs:
                # Remove old section texts for this file
                old_section_ids = {
                    self._chunks[i].section_id
                    for i in old_idxs
                    if self._chunks[i].section_id
                }
                for sid in old_section_ids:
                    self._section_texts.pop(sid, None)

                self._chunks = [c for i, c in enumerate(self._chunks) if i not in old_idxs]
                self._rebuild_index_unlocked()

            start = len(self._chunks)
            self._chunks.extend(chunks)
            self._by_path[file_path] = list(range(start, start + len(chunks)))
            self._bm25_dirty = True

            if section_texts:
                self._section_texts.update(section_texts)

    def all_chunks(self) -> List[StoredChunk]:
        with self._lock:
            return list(self._chunks)

    def get_neighbors(self, file_path: str, chunk_index: int, window: int = 1) -> List[StoredChunk]:
        """
        Return neighboring chunks (by chunk_index) from the same file.
        Excludes the chunk at chunk_index itself.
        """
        with self._lock:
            idxs = self._by_path.get(file_path, [])
            neighbors: List[StoredChunk] = []
            for i in idxs:
                ch = self._chunks[i]
                if ch.chunk_index != chunk_index and abs(ch.chunk_index - chunk_index) <= window:
                    neighbors.append(ch)
            neighbors.sort(key=lambda c: c.chunk_index)
            return neighbors

    def get_section_text(self, section_id: str) -> Optional[str]:
        with self._lock:
            return self._section_texts.get(section_id)

    def bm25_search(self, query: str, top_k: int = 0) -> List[Tuple[int, float]]:
        """
        Keyword search using BM25. Returns (chunk_list_index, score) pairs.
        Rebuilds the BM25 index lazily if chunks have changed.
        """
        with self._lock:
            if self._bm25_dirty:
                texts = [ch.text for ch in self._chunks]
                self._bm25.index(texts)
                self._bm25_dirty = False
            return self._bm25.search(query, top_k=top_k)

    def stats(self) -> dict:
        with self._lock:
            return {"files": len(self._by_path), "chunks": len(self._chunks)}

    def _rebuild_index_unlocked(self) -> None:
        self._by_path = {}
        for idx, ch in enumerate(self._chunks):
            self._by_path.setdefault(ch.file_path, []).append(idx)
        self._bm25_dirty = True


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