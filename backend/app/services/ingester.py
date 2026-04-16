from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

import numpy as np

from ..utils.chunker import chunk_text_rich
from ..utils.embeddings import embed_batch
from ..store.memory_store import get_store, StoredChunk

logger = logging.getLogger(__name__)

MAX_DOCS_PER_INGEST = 50
MAX_CHARS_PER_DOC = 200_000
MAX_TOTAL_CHARS_PER_REQUEST = 500_000
MAX_CHUNKS_PER_DOC = 2_000

_CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".c", ".cpp", ".h",
    ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".cs", ".sh", ".bash",
    ".sql", ".r", ".lua", ".pl", ".m", ".scala", ".zig",
}
_MARKDOWN_EXTENSIONS = {".md", ".markdown", ".mdx"}


def _detect_doc_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in _MARKDOWN_EXTENSIONS:
        return "markdown"
    if ext in _CODE_EXTENSIONS:
        return "code"
    if ext in {".txt", ".text", ".log"}:
        return "text"
    if ext in {".html", ".htm", ".xml"}:
        return "html"
    if ext in {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"}:
        return "config"
    if ext in {".csv", ".tsv"}:
        return "tabular"
    return "unknown"


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
        title = str(d.get("title", "") or "").strip()
        mtime = float(d.get("mtime", 0) or 0)

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

        doc_type = _detect_doc_type(path_str)

        chunking_result = chunk_text_rich(text)
        chunks = chunking_result.chunks
        section_texts = chunking_result.sections

        if not chunks:
            skipped_empty += 1
            continue

        if len(chunks) > MAX_CHUNKS_PER_DOC:
            chunks = chunks[:MAX_CHUNKS_PER_DOC]
            rejected += 1

        # Prefix section_ids with the file path so they are globally unique
        prefixed_sections = {
            f"{path_str}::{sid}": txt
            for sid, txt in section_texts.items()
        }

        chunk_texts = [c.text for c in chunks]
        vectors = embed_batch(chunk_texts)
        if vectors is None or len(vectors) == 0:
            skipped_empty += 1
            continue

        if len(vectors) != len(chunks):
            logger.warning("Embedding count mismatch: got %d vectors for %d chunks", len(vectors), len(chunks))
            skipped_empty += 1
            continue

        stored: List[StoredChunk] = []
        total_chunk_count = len(chunks)
        for idx, (chunk_result, vec_list) in enumerate(zip(chunks, vectors)):
            vec = np.asarray(vec_list, dtype=np.float32).ravel()
            if vec.size == 0:
                continue
            stored.append(
                StoredChunk(
                    chunk_id=f"{path_str}::chunk::{idx}",
                    file_path=path_str,
                    text=chunk_result.text,
                    vector=vec,
                    chunk_index=idx,
                    total_chunks=total_chunk_count,
                    heading_breadcrumb=chunk_result.heading_breadcrumb,
                    section_id=f"{path_str}::{chunk_result.section_id}",
                    doc_type=doc_type,
                    title=title,
                    mtime=mtime,
                )
            )

        store.upsert_file_chunks(path_str, stored, section_texts=prefixed_sections)
        ingested += 1

    return {"ingested": ingested, "skipped_empty": skipped_empty, "rejected": rejected}