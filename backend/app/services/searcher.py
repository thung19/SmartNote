from __future__ import annotations

from typing import List, Dict, Any, Set
import numpy as np

from ..utils.embeddings import embed_text
from ..store.memory_store import get_store

MIN_SIMILARITY = 0.30


def search_chunks(
    session_id: str,
    query: str,
    top_k: int = 5,
    expand_neighbors: bool = False,
    neighbor_window: int = 1,
    diversify: bool = False,
) -> List[Dict[str, Any]]:
    """
    Search for the chunks most similar to the query text within a session.

    expand_neighbors: if True, include adjacent chunks from the same file
                      for each match (provides surrounding context).
    diversify:        if True, spread results across different files rather
                      than letting one file dominate.
    Returns: {chunk_id, file_path, text, score, heading_breadcrumb, chunk_index, neighbors?}
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

    if diversify and top_k > 0:
        # Round-robin across files to ensure diversity
        selected = _diversify_results(sorted_idxs, stored_chunks, scores, top_k)
    else:
        selected = sorted_idxs[:top_k] if top_k > 0 else sorted_idxs

    results: List[Dict[str, Any]] = []
    seen_chunk_ids: Set[str] = set()

    for i in selected:
        ch = stored_chunks[int(i)]
        if ch.chunk_id in seen_chunk_ids:
            continue
        seen_chunk_ids.add(ch.chunk_id)

        entry: Dict[str, Any] = {
            "chunk_id": ch.chunk_id,
            "file_path": ch.file_path,
            "text": ch.text,
            "score": float(scores[int(i)]),
            "heading_breadcrumb": ch.heading_breadcrumb,
            "chunk_index": ch.chunk_index,
        }

        # Optionally attach neighbor text for richer LLM context
        if expand_neighbors:
            neighbors = store.get_neighbors(ch.file_path, ch.chunk_index, window=neighbor_window)
            entry["neighbors"] = [
                {
                    "chunk_id": n.chunk_id,
                    "text": n.text,
                    "chunk_index": n.chunk_index,
                    "heading_breadcrumb": n.heading_breadcrumb,
                }
                for n in neighbors
                if n.chunk_id not in seen_chunk_ids
            ]
            # Mark neighbors as seen to avoid duplication
            for n in neighbors:
                seen_chunk_ids.add(n.chunk_id)

        results.append(entry)

    return results


def _diversify_results(
    sorted_idxs: np.ndarray,
    stored_chunks: list,
    scores: np.ndarray,
    top_k: int,
) -> np.ndarray:
    """
    Select top_k results with file diversity via round-robin.
    Ensures each file gets a slot before any file gets a second.
    """
    from collections import OrderedDict

    # Group candidates by file, preserving score order
    file_queues: OrderedDict[str, list] = OrderedDict()
    for idx in sorted_idxs:
        fp = stored_chunks[int(idx)].file_path
        if fp not in file_queues:
            file_queues[fp] = []
        file_queues[fp].append(idx)

    selected: list = []
    while len(selected) < top_k and file_queues:
        empty_files = []
        for fp, queue in file_queues.items():
            if len(selected) >= top_k:
                break
            if queue:
                selected.append(queue.pop(0))
            if not queue:
                empty_files.append(fp)
        for fp in empty_files:
            del file_queues[fp]

    return np.array(selected) if selected else np.array([], dtype=int)


def search(session_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    return search_chunks(session_id, query, top_k=top_k, diversify=True)