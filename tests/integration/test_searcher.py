from backend.app.db.database import init_db
from backend.app.services.indexer import index_directory
from backend.app.services.searcher import search

def test_search_finds_duckdb_note(temp_db_path, sample_notes_dir):
    init_db()
    index_directory(sample_notes_dir)

    results = search("columnar analytical database", top_k=1)

    assert isinstance(results, list)
    assert len(results) == 1
    assert "duckdb.md" in results[0]["file_path"].lower()
    assert results[0]["score"] > 0
