from __future__ import annotations
from typing import List, Dict, Any, Optional
import json

import numpy as np

from db.database import get_connection
from utils.embeddings import embed_text

def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    # Flattens array
    a = a.ravel()
    b = b.ravel()

    # Computer vector lengths (||a|| and ||b||)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    # Handle zero-length vectors to avoid division by zero
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    
    # Compute cosine similarity
    return float(np.dot(a, b) / (norm_a * norm_b))

def _load_chunk_embeddings(conn) -> [Dict[str, Any]]:
    
    # SQL Query to get all chunks. Returns a Python list of rows
    rows = conn.execute(
        """
        SELECT id, file_path, text, embeddings
        FROM chunks
        """
    ).fetchall()

    chunks: List[Dict[str,Any]] = []

    # Loop through each row and unpack it
    for row in rows:
        chunk_id, file_path, text, embedding_str = row

        # Skip if embedding is None
        if embedding_str is None:
            continue
        
        
        try:
            # Convert JSON into a python list
            data = json.loads(embedding_str)
            # Convert list into numpy array
            vec = np.asarray(data, dtype=np.float32)
        
        # Skip if something goes wrong
        except Exception:
            continue
        
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
        top_k: int =5,
        conn: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    
    # Ensure query is not empty
    if not query.strip():
        return []
    
    # Get vector for query
    query_vec = embed_text(query)


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

            #Find the chunks similarity to the query
            score = _cosine_similarity(query_vec, ch["vector"])

            # Add the results
            results.append(
                {
                    "chunk_id": ch["chunk_id"],
                    "file_path": ch["file_path"],
                    "text": ch["text"],
                    "score": score,
                }
            )
        
        # Sort results by score descending
        results.sort(key=lambda r: r["score"], reverse = True)
        
        # Return only top_k results
        if top_k > 0:
            results = results[:top_k]
        
        return results
    
    # Close the DB ocnnection if you created it inside the function
    finally:
        if own_conn:
            conn.close()