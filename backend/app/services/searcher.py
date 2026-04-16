from __future__ import annotations

import logging
from collections import OrderedDict
from typing import List, Dict, Any, Set, Tuple

import numpy as np

from ..utils.embeddings import embed_text, rerank
from ..store.memory_store import get_store

logger = logging.getLogger(__name__)

MIN_SIMILARITY = 0.25  # lowered slightly since RRF + re-ranking handle precision
RRF_K = 60  # standard constant for Reciprocal Rank Fusion
RERANK_CANDIDATE_MULTIPLIER = 4  # fetch this many × top_k candidates for re-ranking
DEDUP_JACCARD_THRESHOLD = 0.85  # near-duplicate detection threshold


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search_chunks(
    session_id: str,
    query: str,
    top_k: int = 5,
    expand_neighbors: bool = False,
    neighbor_window: int = 1,
    diversify: bool = False,
    use_reranker: bool = False,
) -> List[Dict[str, Any]]:
    """
    Hybrid search pipeline:
      1. Dense vector retrieval  (semantic similarity)
      2. BM25 keyword retrieval  (exact terms, acronyms, rare tokens)
      3. Reciprocal Rank Fusion  (merge both ranked lists)
      4. Cross-encoder re-ranking (optional, more accurate relevance)
      5. Near-duplicate removal
      6. File diversity
      7. Neighbor expansion
    """
    if not (query or "").strip():
        return []

    store = get_store(session_id)
    stored_chunks = store.all_chunks()
    if not stored_chunks:
        return []

    # --- Phase 1: Dense vector retrieval ---
    q_vec = np.asarray(embed_text(query), dtype=np.float32).ravel()
    if q_vec.size == 0:
        return []

    mat = np.vstack([ch.vector.ravel() for ch in stored_chunks]).astype(
        np.float32, copy=False
    )
    dense_scores = mat @ q_vec

    # Build dense ranking (filtered by min similarity)
    dense_idxs = np.where(dense_scores >= MIN_SIMILARITY)[0]
    dense_ranked = dense_idxs[np.argsort(dense_scores[dense_idxs])[::-1]]

    # --- Phase 2: BM25 keyword retrieval ---
    bm25_results = store.bm25_search(query, top_k=0)  # all matches
    bm25_ranked = [idx for idx, _score in bm25_results]

    # --- Phase 3: Reciprocal Rank Fusion ---
    candidate_limit = top_k * RERANK_CANDIDATE_MULTIPLIER
    fused = _reciprocal_rank_fusion(dense_ranked.tolist(), bm25_ranked)

    # Take top candidates for re-ranking (or final selection)
    candidate_idxs = [
        idx for idx, _score in sorted(fused.items(), key=lambda x: x[1], reverse=True)
    ][:candidate_limit]

    if not candidate_idxs:
        return []

    # --- Phase 4: Cross-encoder re-ranking (optional) ---
    if use_reranker and len(candidate_idxs) > 1:
        candidate_idxs = _rerank_candidates(
            query, candidate_idxs, stored_chunks
        )

    # --- Phase 5: Near-duplicate removal ---
    candidate_idxs = _deduplicate(candidate_idxs, stored_chunks)

    # --- Phase 6: File diversity ---
    if diversify and top_k > 0:
        selected_idxs = _diversify_results(candidate_idxs, stored_chunks, top_k)
    else:
        selected_idxs = candidate_idxs[:top_k] if top_k > 0 else candidate_idxs

    # --- Phase 7: Build results with optional neighbor expansion ---
    results: List[Dict[str, Any]] = []
    seen_chunk_ids: Set[str] = set()

    for i in selected_idxs:
        ch = stored_chunks[i]
        if ch.chunk_id in seen_chunk_ids:
            continue
        seen_chunk_ids.add(ch.chunk_id)

        entry: Dict[str, Any] = {
            "chunk_id": ch.chunk_id,
            "file_path": ch.file_path,
            "text": ch.text,
            "score": float(dense_scores[i]) if i < len(dense_scores) else 0.0,
            "heading_breadcrumb": ch.heading_breadcrumb,
            "chunk_index": ch.chunk_index,
            "section_id": ch.section_id,
            "doc_type": ch.doc_type,
        }

        if expand_neighbors:
            neighbors = store.get_neighbors(
                ch.file_path, ch.chunk_index, window=neighbor_window
            )
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
            for n in neighbors:
                seen_chunk_ids.add(n.chunk_id)

        results.append(entry)

    return results


def search(session_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    return search_chunks(session_id, query, top_k=top_k, diversify=True)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _reciprocal_rank_fusion(
    dense_ranked: List[int], bm25_ranked: List[int]
) -> Dict[int, float]:
    """
    Merge two ranked lists using Reciprocal Rank Fusion.
    RRF(d) = Σ 1 / (k + rank_i(d))
    """
    scores: Dict[int, float] = {}
    for rank, idx in enumerate(dense_ranked):
        scores[idx] = scores.get(idx, 0.0) + 1.0 / (RRF_K + rank + 1)
    for rank, idx in enumerate(bm25_ranked):
        scores[idx] = scores.get(idx, 0.0) + 1.0 / (RRF_K + rank + 1)
    return scores


def _rerank_candidates(
    query: str, candidate_idxs: List[int], stored_chunks: list
) -> List[int]:
    """Re-rank candidates using a cross-encoder for more accurate relevance."""
    texts = [stored_chunks[i].text for i in candidate_idxs]
    try:
        scores = rerank(query, texts)
    except Exception:
        logger.warning("Cross-encoder re-ranking failed, falling back to RRF order")
        return candidate_idxs

    paired = list(zip(candidate_idxs, scores))
    paired.sort(key=lambda x: x[1], reverse=True)
    return [idx for idx, _s in paired]


def _deduplicate(
    candidate_idxs: List[int], stored_chunks: list
) -> List[int]:
    """Remove near-duplicate chunks using Jaccard similarity on word sets."""
    if len(candidate_idxs) <= 1:
        return candidate_idxs

    result: List[int] = []
    kept_word_sets: List[set] = []

    for idx in candidate_idxs:
        words = set(stored_chunks[idx].text.lower().split())
        if not words:
            continue
        is_dup = False
        for kept_words in kept_word_sets:
            intersection = len(words & kept_words)
            union = len(words | kept_words)
            if union > 0 and intersection / union > DEDUP_JACCARD_THRESHOLD:
                is_dup = True
                break
        if not is_dup:
            result.append(idx)
            kept_word_sets.append(words)

    return result


def _diversify_results(
    candidate_idxs: List[int], stored_chunks: list, top_k: int
) -> List[int]:
    """
    Select top_k results with file diversity via round-robin.
    Ensures each file gets a slot before any file gets a second.
    """
    file_queues: OrderedDict[str, list] = OrderedDict()
    for idx in candidate_idxs:
        fp = stored_chunks[idx].file_path
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

    return selected