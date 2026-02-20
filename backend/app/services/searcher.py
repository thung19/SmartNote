from __future__ import annotations

from typing import List, Dict, Any
import numpy as np

from ..utils.embeddings import embed_text
from ..store.memory_store import get_store

MIN_SIMILARITY = 0.30


def search_chunks(session_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Search for the chunks most similar to the query text within a session.
    Returns: {chunk_id, file_path, text, score}
    """
    if not (query or "").strip():
        return []

    store = get_store(session_id)
    stored_chunks = store.all_chunks()
    if not stored_chunks:
        return []

    q = np.asarray(embed_text(query), dtype=np.float32).ravel()
    if q.size == 0:
        return []

    # Stack vectors for fast dot product (embeddings are normalized)
    mat = np.vstack([ch.vector.ravel() for ch in stored_chunks]).astype(np.float32, copy=False)

    # dot product yields cosine if vectors are normalized
    scores = mat @ q

    # Filter by MIN_SIMILARITY
    idxs = np.where(scores >= MIN_SIMILARITY)[0]
    if idxs.size == 0:
        return []

    # Sort candidates by score desc
    sorted_idxs = idxs[np.argsort(scores[idxs])[::-1]]
    if top_k > 0:
        sorted_idxs = sorted_idxs[:top_k]

    results: List[Dict[str, Any]] = []
    for i in sorted_idxs:
        ch = stored_chunks[int(i)]
        results.append(
            {
                "chunk_id": ch.chunk_id,
                "file_path": ch.file_path,
                "text": ch.text,
                "score": float(scores[int(i)]),
            }
        )
    return results


def search(session_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    return search_chunks(session_id, query, top_k=top_k)