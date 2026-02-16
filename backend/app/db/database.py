from pathlib import Path
import duckdb
import os

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "rag.duckdb"

def _get_db_path() -> Path:
    # Allow overriding DB path via environment variable
    override = os.getenv("SMARTNOTE_DB_PATH")
    if override:
        return Path(override)
    else:
        return DEFAULT_DB_PATH

def get_connection():
    # Opens or creates the local DuckDB file
    return duckdb.connect(str(_get_db_path()))


def init_db():
    con = get_connection()

    # Sequences for auto-incrementing IDs (instead of GENERATED ALWAYS AS IDENTITY)
    con.execute("CREATE SEQUENCE IF NOT EXISTS documents_id_seq START 1;")
    con.execute("CREATE SEQUENCE IF NOT EXISTS chunks_id_seq START 1;")

    # Documents we ingest (one row per file)
    con.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id BIGINT PRIMARY KEY DEFAULT nextval('documents_id_seq'),
            path TEXT UNIQUE,
            title TEXT,
            mtime DOUBLE
        );
    """)

    # Text chunks per document + their embedding vector
    con.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id BIGINT PRIMARY KEY DEFAULT nextval('chunks_id_seq'),
            document_id BIGINT REFERENCES documents(id),
            chunk_index INTEGER,
            text TEXT,
            embedding DOUBLE[]   -- DuckDB array of doubles
        );
    """)

    # Helpful index
    con.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);")

    con.close()
