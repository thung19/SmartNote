from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List
import threading
import numpy as np


@dataclass
class StoredChunk:
    chunk_id: str
    file_path: str
    text: str
    vector: np.ndarray  # shape: (d,)


class MemoryStore:
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


STORE = MemoryStore()