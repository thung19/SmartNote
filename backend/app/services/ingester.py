from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from ..utils.chunker import chunk_text
from ..utils.embeddings import embed_batch
from ..store.memory_store import STORE, StoredChunk

logger = logging.getLogger(__name__)


def ingest_docs(docs: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Ingest docs into the backend in-memory store (RAM).

    Each doc:
      { "path": str, "text": str, "title"?: str, "mtime"?: float }

    Overwrite semantics per path.
    Server restart clears everything (no persistence).
    """
    logging.basicConfig(level=logging.INFO)

    ingested = 0
    skipped_empty = 0

    for d in docs:
        path_str = str(d.get("path", "") or "").strip()
        text = str(d.get("text", "") or "")

        if not path_str:
            logger.warning("Skipping doc with missing path.")
            continue

        # Empty doc => remove from index (overwrite with 0 chunks)
        if not text.strip():
            STORE.upsert_file_chunks(path_str, [])
            skipped_empty += 1
            continue

        # Chunk + embed
        chunks = chunk_text(text)
        if not chunks:
            skipped_empty += 1
            continue

        vectors = embed_batch(chunks)
        if not vectors:
            skipped_empty += 1
            continue

        stored: List[StoredChunk] = []
        for idx, (chunk_text_value, vec_list) in enumerate(zip(chunks, vectors)):
            vec = np.asarray(vec_list, dtype=np.float32)
            stored.append(
                StoredChunk(
                    chunk_id=f"{path_str}::chunk::{idx}",
                    file_path=path_str,
                    text=chunk_text_value,
                    vector=vec,
                )
            )

        STORE.upsert_file_chunks(path_str, stored)
        ingested += 1

    return {"ingested": ingested, "skipped_empty": skipped_empty}