from pathlib import Path
from typing import Iterator, Tuple

# Define which file types we support for now
SUPPORTED = {".txt", ".md"}

def walk_text_files(root: str) -> Iterator[Tuple[str, str, float]]:
   
    
    base = Path(root).expanduser().resolve()

    for fp in base.rglob("*"):  # recursively walk all files and subfolders
        if fp.is_file() and fp.suffix.lower() in SUPPORTED:
            try:
                # Try reading with UTF-8 (normal encoding)
                text = fp.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                # Fallback for unusual encodings
                text = fp.read_text(encoding="latin-1", errors="ignore")

            yield str(fp), text, fp.stat().st_mtime
