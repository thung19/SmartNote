# tests/conftest.py
import os
import pytest
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

@pytest.fixture()
def temp_db_path(tmp_path, monkeypatch):
    """
    Provides a temporary DuckDB path and forces SmartNote to use it
    via SMARTNOTE_DB_PATH.
    """
    db_path = tmp_path / "test_rag.duckdb"
    monkeypatch.setenv("SMARTNOTE_DB_PATH", str(db_path))
    return db_path


@pytest.fixture()
def sample_notes_dir(tmp_path):
    """
    Create a small deterministic corpus of notes for integration tests.
    """
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()

    (notes_dir / "duckdb.md").write_text(
        "DuckDB is a columnar analytical database. It is good for OLAP.\n",
        encoding="utf-8",
    )
    (notes_dir / "sqlite.md").write_text(
        "SQLite is a lightweight row-based embedded database.\n",
        encoding="utf-8",
    )
    (notes_dir / "empty.md").write_text("", encoding="utf-8")

    return str(notes_dir)
