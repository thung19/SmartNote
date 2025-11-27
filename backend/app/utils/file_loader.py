from pathlib import Path
from typing import Iterator, Tuple

# Define which file types we support for now
SUPPORTED = {".txt", ".md"}

def walk_text_files(root: str) -> Iterator[Tuple[str, str, float]]:
   
    # Expands root string to path object
    base = Path(root).expanduser().resolve()

    # Go through every file and folder
    for fp in base.rglob("*"):  
        
        # Make sure it is a supported file type
        if fp.is_file() and fp.suffix.lower() in SUPPORTED:
            try:
                # Try reading with UTF-8 (normal encoding)
                text = fp.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                # Fallback for unusual encodings (latin-1)
                text = fp.read_text(encoding="latin-1", errors="ignore")

            # Yield tuple with file path, text content, modification time
            # Yield used to send out one output at a time, rather than looking for all outputs first
            yield str(fp), text, fp.stat().st_mtime
