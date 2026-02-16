from __future__ import annotations

from typing import List, Dict, Any
import numpy as np

from ..utils.embeddings import embed_text
from ..store.memory_store import STORE

MIN_SIMILARITY = 0.30


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a = a.ravel()
    b = b.ravel()

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return float(np.dot(a, b) / (norm_a * norm_b))


def search_chunks(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Search for the chunks most similar to the query text.
    Returns: {chunk_id, file_path, text, score}
    """
    if not query.strip():
        return []

    query_vec = np.asarray(embed_text(query), dtype=np.float32)

    stored_chunks = STORE.all_chunks()
    if not stored_chunks:
        return []

    results: List[Dict[str, Any]] = []
    for ch in stored_chunks:
        score = _cosine_similarity(query_vec, ch.vector)
        if score >= MIN_SIMILARITY:
            results.append(
                {
                    "chunk_id": ch.chunk_id,
                    "file_path": ch.file_path,
                    "text": ch.text,
                    "score": score,
                }
            )

    results.sort(key=lambda r: r["score"], reverse=True)

    if top_k > 0:
        results = results[:top_k]

    return results


def search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    return search_chunks(query, top_k=top_k)