from __future__ import annotations
from typing import List, Dict, Any, Optional
import numpy as np

from ..db.database import get_connection
from ..utils.embeddings import embed_text

MIN_SIMILARITY = 0.30


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    # Flattens array
    a = a.ravel()
    b = b.ravel()

    # Compute vector lengths (||a|| and ||b||)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    # Handle zero-length vectors to avoid division by zero
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    # Compute cosine similarity
    return float(np.dot(a, b) / (norm_a * norm_b))


def _load_chunk_embeddings(conn) -> List[Dict[str, Any]]:
    """
    Load all chunks and their embeddings from DuckDB.

    Uses the current schema:
      documents(id, path, ...)
      chunks(id, document_id, chunk_index, text, embedding DOUBLE[])
    """
    # SQL Query to get all chunks joined with their document path
    rows = conn.execute(
        """
        SELECT c.id, d.path, c.text, c.embedding
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        """
    ).fetchall()

    chunks: List[Dict[str, Any]] = []

    # Loop through each row and unpack it
    for row in rows:
        chunk_id, file_path, text, embedding_array = row

        # Skip if embedding is None
        if embedding_array is None:
            continue

        # DuckDB returns DOUBLE[] as a Python list of floats; turn into numpy vector
        vec = np.asarray(embedding_array, dtype=np.float32)

        # Add chunk info to list
        chunks.append(
            {
                "chunk_id": chunk_id,
                "file_path": file_path,
                "text": text,
                "vector": vec,
            }
        )

    return chunks


def search_chunks(
    query: str,
    top_k: int = 5,
    conn: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """
    Search for the chunks most similar to the query text.
    Returns a list of dicts: {chunk_id, file_path, text, score}.
    """
    # Ensure query is not empty
    if not query.strip():
        return []

    # Get vector for query (convert to numpy array)
    query_vec = np.asarray(embed_text(query), dtype=np.float32)

    # Get connection to DB
    own_conn = False
    if conn is None:
        conn = get_connection()
        own_conn = True

    try:
        # Load all chunk embeddings from DB
        chunks = _load_chunk_embeddings(conn)
        if not chunks:
            return []

        results: List[Dict[str, Any]] = []

        # Go through each chunk
        for ch in chunks:
            # Find the chunk's similarity to the query
            score = _cosine_similarity(query_vec, ch["vector"])

            # Add the result
            results.append(
                {
                    "chunk_id": ch["chunk_id"],
                    "file_path": ch["file_path"],
                    "text": ch["text"],
                    "score": score,
                }
            )

        # Sort results by score descending
        results.sort(key=lambda r: r["score"], reverse=True)

        results = [r for r in results if r["score"] >= MIN_SIMILARITY]

        # Return only top_k results
        if top_k > 0:
            results = results[:top_k]

        return results

    # Close the DB connection if you created it inside the function
    finally:
        if own_conn:
            conn.close()


def search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Simple wrapper so other code (and your tests) can call search()
    instead of search_chunks().
    """
    return search_chunks(query, top_k=top_k)
