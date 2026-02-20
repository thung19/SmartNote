from __future__ import annotations

import logging
from typing import Any, Dict, List

import numpy as np

from ..utils.chunker import chunk_text
from ..utils.embeddings import embed_batch
from ..store.memory_store import get_store, StoredChunk

logger = logging.getLogger(__name__)

MAX_DOCS_PER_INGEST = 50
MAX_CHARS_PER_DOC = 200_000
MAX_TOTAL_CHARS_PER_REQUEST = 500_000
MAX_CHUNKS_PER_DOC = 2_000


def ingest_docs(session_id: str, docs: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Ingest docs into the session-scoped in-memory store (RAM).

    Each doc:
      { "path": str, "text": str, "title"?: str, "mtime"?: float }

    Overwrite semantics per path.
    Server restart clears everything (no persistence).
    """
    store = get_store(session_id)

    ingested = 0
    skipped_empty = 0
    rejected = 0

    if not docs:
        return {"ingested": 0, "skipped_empty": 0, "rejected": 0}

    if len(docs) > MAX_DOCS_PER_INGEST:
        docs = docs[:MAX_DOCS_PER_INGEST]
        rejected += 1  # indicates truncation occurred

    total_chars = 0

    for d in docs:
        path_str = str(d.get("path", "") or "").strip()
        text = str(d.get("text", "") or "")

        if not path_str:
            logger.warning("Skipping doc with missing path.")
            skipped_empty += 1
            continue

        if not text.strip():
            store.upsert_file_chunks(path_str, [])
            skipped_empty += 1
            continue

        if len(text) > MAX_CHARS_PER_DOC:
            text = text[:MAX_CHARS_PER_DOC]
            rejected += 1

        total_chars += len(text)
        if total_chars > MAX_TOTAL_CHARS_PER_REQUEST:
            rejected += 1
            break

        chunks = chunk_text(text)
        if not chunks:
            skipped_empty += 1
            continue

        if len(chunks) > MAX_CHUNKS_PER_DOC:
            chunks = chunks[:MAX_CHUNKS_PER_DOC]
            rejected += 1

        vectors = embed_batch(chunks)
        if vectors is None or len(vectors) == 0:
            skipped_empty += 1
            continue

        if len(vectors) != len(chunks):
            logger.warning("Embedding count mismatch: got %d vectors for %d chunks", len(vectors), len(chunks))
            skipped_empty += 1
            continue

        stored: List[StoredChunk] = []
        for idx, (chunk_text_value, vec_list) in enumerate(zip(chunks, vectors)):
            vec = np.asarray(vec_list, dtype=np.float32).ravel()
            if vec.size == 0:
                continue
            stored.append(
                StoredChunk(
                    chunk_id=f"{path_str}::chunk::{idx}",
                    file_path=path_str,
                    text=chunk_text_value,
                    vector=vec,
                )
            )

        store.upsert_file_chunks(path_str, stored)
        ingested += 1

    return {"ingested": ingested, "skipped_empty": skipped_empty, "rejected": rejected}