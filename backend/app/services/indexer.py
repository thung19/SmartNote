from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import List, Tuple

from ..utils.file_loader import walk_text_files
from ..utils.chunker import chunk_text
from ..utils.embeddings import embed_batch
from ..db.database import get_connection, init_db

from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)

def index_directory(root_dir: str) -> None:
    """
    Index all supported text files under the given root directory
    into the DuckDB database (documents + chunks tables).
    Used by tests and by the API.
    """
    logging.basicConfig(level=logging.INFO)
    init_db()

    conn = get_connection()
    indexed = 0
    skipped_empty = 0

    try:
        for path, text, mtime in walk_text_files(root_dir):
            path_str = str(path)

            # If file is empty -> remove any existing entries
            if not text.strip():
                logger.info("File %s is empty; removing from index if present.", path_str)
                row = conn.execute(
                    "SELECT id FROM documents WHERE path = ?",
                    (path_str,),
                ).fetchone()
                if row:
                    doc_id = row[0]
                    conn.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
                    conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
                skipped_empty += 1
                continue

            logger.info("Indexing file: %s", path_str)

            # Delete any existing document/chunks for this path
            row = conn.execute(
                "SELECT id FROM documents WHERE path = ?",
                (path_str,),
            ).fetchone()
            if row:
                old_id = row[0]
                conn.execute("DELETE FROM chunks WHERE document_id = ?", (old_id,))
                conn.execute("DELETE FROM documents WHERE id = ?", (old_id,))

            # Insert new document row
            title = Path(path_str).name
            conn.execute(
                "INSERT INTO documents (path, title, mtime) VALUES (?, ?, ?)",
                (path_str, title, mtime),
            )
            doc_id = conn.execute(
                "SELECT id FROM documents WHERE path = ?",
                (path_str,),
            ).fetchone()[0]

            # Chunk + embed
            chunks = chunk_text(text)
            if not chunks:
                logger.info("No chunks produced for %s; skipping.", path_str)
                continue

            vectors = embed_batch(chunks)

            rows: List[Tuple[int, int, str, list]] = []
            for idx, (chunk_text_value, vec) in enumerate(zip(chunks, vectors)):
                rows.append((doc_id, idx, chunk_text_value, vec))

            conn.executemany(
                """
                INSERT INTO chunks (document_id, chunk_index, text, embedding)
                VALUES (?, ?, ?, ?)
                """,
                rows,
            )

            indexed += 1

        conn.commit()
    finally:
        conn.close()

    logger.info(
        "Indexing complete. Indexed: %d, skipped_empty: %d",
        indexed,
        skipped_empty,
    )
