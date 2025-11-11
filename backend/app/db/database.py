from pathlib import Path
import duckdb

DB_PATH = Path(__file__).resolve().parent.parent / "rag.duckdb"

def get_conn():
    # Opens or creates the local DuckDB file
    return duckdb.connect(str(DB_PATH))

def init_db():
    con = get_conn()
    # Documents we ingest (one row per file)
    con.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            path TEXT UNIQUE,
            title TEXT,
            mtime DOUBLE
        );
    """)
    # Text chunks per document + their embedding vector
    con.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            document_id BIGINT REFERENCES documents(id),
            chunk_index INTEGER,
            text TEXT,
            embedding DOUBLE[]   -- DuckDB array of doubles
        );
    """)
    # Helpful indexes
    con.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);")
    con.close()
