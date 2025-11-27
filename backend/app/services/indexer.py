from __future__ import annotations
import argparse
import logging
from typing import List

from ..utils.file_loader import walk_text_files
from ..utils.chunker import chunk_text
from ..utils.embeddings import embed_batch
from ..db.database import get_connection

logger = logging.getLogger(__name__)

# Check if a file needs to be reindexed
def needs_reindex(conn, path: str, mtime: float) -> bool:

    # Look for existing mtime in DB based on inputted path
    cur = conn.execute("SELECT mtime FROM files WHERE path = ?", (path,))
    # Get that row
    row = cur.fetchone()
    # If the row doesn't exist we need to reindex
    if row is None:
        return True
    
    # If the db modified time is older than the file modified time, we need to reindex
    db_mtime = row[0]
    return mtime > db_mtime


'''
Insert or update the chunks and file entry for a given file path
@param conn: Database connection
@param path: File path
@param mtime: File modified time
@param chunks: List of text chunks
@param vectors: List of embedding vectors corresponding to chunks
'''
def upsert_file_chunks(
        conn,
        path: str,
        mtime: float,
        chunks: List[str],
        vectors: List[object],
) -> None:
    
    # Ensure chunks and vectors lengths match
    if len(chunks) != len(vectors):
        raise ValueError(
            f"chunks and vectors length differ: {len(chunks)}  vs {len(vectors)}"
        )
    
    # Delete existing chunks for this file
    conn.execute("DELETE FROM chunks WHERE file_path = ?", (path,))

    # Prepare rows for insertion
    rows = []
    for idx in range(len(chunks)):
        chunk = chunks[idx]
        vec = vectors[idx]

        row = (path, idx, chunk, vec, mtime)
        rows.append(row)

    # Insert each row in "rows" into the chunks table
    conn.executemany(
        """
        INSERT INTO chunks (file_path, chunk_index, content, embeddings, mtime)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )

    # Insert file data into file table with upsert
    conn.execute(
        """
        INSERT INTO files (path, mtime)
        VALUES (?, ?)
        ON CONFLICT(path) DO UPDATE SET mtime = excluded.mtime
        """,
        (path, mtime),
    )


'''
@param path: File path
@param text: raw text content
@param mtime: File modified time
@param conn: Optional database connection

@return: True if file was indexed/updated, False if skipped
'''
def index_file(
        path: str,
        text: str,
        mtime: float,
        conn=None,
) -> bool:
    
    own_conn = False

    # No connection was passed, so create one
    if conn is None:
        conn = get_connection()
        own_conn = True

        logging.basicConfig(level=logging.INFO)
    try:
        # Handle empty files by removing from index
        if not text.strip():
            logger.info("File %s is empty; removing from index if present.", path)
            conn.execute("DELETE FROM chunks WHERE file_path = ?", (path,))
            conn.execute("DELETE FROM files WHERE path = ?", (path,))
            conn.commit()
            return True
        
        # Check if reindexing is needed
        if not needs_reindex(conn, path, mtime):
            logger.info("Skipping unchanged file: %s", path)
            return False

        logger.info("Indexing file: %s", path)

        # Chunk the text
        chunks = chunk_text(text)

        # If no chunks were produced, remove from index
        if not chunks:
            logger.info("No chunks produced for %s; removing from index.", path)
            conn.execute("DELETE FROM chunks WHERE file_path = ?", (path,))
            conn.execute("DELETE FROM files WHERE path = ?", (path,))
            conn.commit()
            return True

        # Get embeddings for chunks
        vectors = embed_batch(chunks)

        # Upsert file and chunk data into DB
        upsert_file_chunks(conn, path, mtime, chunks, vectors)
        conn.commit()

        return True
    finally:
        if own_conn:
            conn.close()

'''

Indexes all text files under the given root directory
@param root_dir: Root directory path
'''
def index_all(root_dir: str) -> None:
    # Get DB connection
    conn = get_connection()

    # Counters for logging
    indexed = 0
    skipped = 0
    removed_empty = 0

    try:
        # Unpacks each file path, text, mtime tuple from 'walk_text_files'
        for path, text, mtime in walk_text_files(root_dir):
            
            # Convert Path object to string
            path_str = str(path)

            # If file text is empty...
            if not text.strip():

                # Delete file from chunks and files tables
                conn.execute("DELETE FROM chunks WHERE file_path = ?", (path_str,))
                conn.execute("DELETE FROM files where path = ?", (path_str,))
                removed_empty += 1
                continue
            
            # Index the file and update counters based on the result
            changed = index_file(path_str, text, mtime, conn=conn)
            if changed:
                indexed += 1
            else:
                skipped += 1

        # Commit after each file
        conn.commit()
    finally:
        conn.close()

    logger.info(
        "Indexing compete. Indexed: %d, skipped: %d, removed_empty: %d",
        indexed,
        skipped,
        removed_empty,
    )

def main() -> None:
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Create command-line argument parser
    parser = argparse.ArgumentParser(
        description="Index all text files under a root directory into the vector database."
    )

    # Defines required argument
    parser.add_argument(
        "root_dir",
        help = "Root directory containing your notes/text files",
    )

    # Parse argument
    arg = parser.parse_args()

    # Run the indexer based on the given directory
    index_all(arg.root_dir)

if __name__ == "__main__":
    main()