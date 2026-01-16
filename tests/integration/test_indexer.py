from backend.app.services.indexer import index_directory
from backend.app.db.database import get_connection, init_db

def test_indexer_writes_chunks(temp_db_path, sample_notes_dir):
    init_db()
    index_directory(sample_notes_dir)

    conn = get_connection()
    try:
        count = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        assert count > 0
    finally:
        conn.close()
