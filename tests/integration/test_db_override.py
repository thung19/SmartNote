# tests/integration/test_db_override.py
from backend.app.db.database import get_connection, init_db

def test_db_override_creates_tables(temp_db_path):
    # temp_db_path fixture sets SMARTNOTE_DB_PATH
    init_db()
    conn = get_connection()
    try:
        tables = conn.execute("SHOW TABLES").fetchall()
        table_names = {t[0] for t in tables}
        assert "documents" in table_names
        assert "chunks" in table_names
    finally:
        conn.close()
