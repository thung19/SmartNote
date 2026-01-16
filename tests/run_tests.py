import os
import sys
from pathlib import Path

# Make project root importable
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

TEST_FILES_DIR = r"C:\Users\thoma\Projects\SmartNote_TestFiles"

# Import your modules
from backend.app.utils.embeddings import embed_text
from backend.app.services.indexer import index_directory
from backend.app.services.searcher import search
from backend.app.services.summarizer import summarize_answer
from backend.app.db.database import get_connection

def print_header(title: str):
    print("\n" + "="*60)
    print(title)
    print("="*60)

def test_embeddings():
    print_header("TEST 1: Embeddings")

    try:
        vec = embed_text("Hello world test")
        assert isinstance(vec, list) or hasattr(vec, "__len__")
        print("✅ Embeddings: PASS")
        return True
    except Exception as e:
        print("❌ Embeddings: FAIL")
        print("Error:", e)
        return False

def test_indexer():
    print_header("TEST 2: Indexer")

    try:
        index_directory(TEST_FILES_DIR)

        # Ensure DB has some rows
        conn = get_connection()
        count = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        assert count > 0

        print("✅ Indexer: PASS")
        return True
    except Exception as e:
        print("❌ Indexer: FAIL")
        print("Error:", e)
        return False

def test_searcher():
    print_header("TEST 3: Searcher")

    try:
        results = search("gradient")
        assert isinstance(results, list) and len(results) > 0
        print("Found", len(results), "results")
        print("✅ Searcher: PASS")
        return True
    except Exception as e:
        print("❌ Searcher: FAIL")
        print("Error:", e)
        return False

def test_summarizer():
    print_header("TEST 4: Summarizer")

    try:
        answer = summarize_answer("What is the gradient?", "The gradient points uphill.")
        assert isinstance(answer, str)
        print("Summary:", answer[:60], "...")
        print("✅ Summarizer: PASS")
        return True
    except Exception as e:
        print("❌ Summarizer: FAIL")
        print("Error:", e)
        return False

if __name__ == "__main__":
    print_header("RUNNING SMARTNOTE TEST SUITE")

    tests = [
        test_embeddings(),
        test_indexer(),
        test_searcher(),
        test_summarizer()
    ]

    print("\n" + "="*60)
    if all(tests):
        print("🎉 ALL TESTS PASSED!")
    else:
        print("❗ SOME TESTS FAILED — SEE ABOVE")
    print("="*60)
