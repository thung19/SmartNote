# tests/test_imports.py
import sys
from pathlib import Path

# 1. Add project root to sys.path so "backend" is importable
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

# 2. Now this import will work
from backend.app.utils.embeddings import embed_text

print("Imports work!")
