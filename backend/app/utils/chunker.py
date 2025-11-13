
"""
Split text into paragraphs based on double newlines, cleaning up extra whitespace.
"""
def _split_into_paragraphs(text: str) -> List[str]:
    raw_parts = text.split("\n\n")

    paragraphs: List[str] = []
    for part in raw_parts:
        stripped_part = part.strip()
        lines = stripped_part.splitlines()

        cleaned_lines = []
        for line in lines:
            stripped_line = line.strip()
            if stripped_line:  
                cleaned_lines.append(stripped_line)

        cleaned = "\n".join(cleaned_lines)

        if cleaned:
            paragraphs.append(cleaned)

    return paragraphs

def chunk_text(text: str, max_chars: int = 800, overlap: int = 200,) -> List[str]:
    """
    Chunk text into overlapping segments based on character limits.
    """
    if not text:
        return []
    
    paragraphs = _split_into_paragraphs(text)

    rough_chunks: List[str] = []
    current: List[str] = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)
        
        if current and current_len + para_len + 2 > max_chars:
            rough_chunks.append("\n\n".join(current))

            current = [para]
            curren_len = para_len
        else:
            current.append(para)
            curren_len += para_len + 2

    if current:
        rough_chunks.append("\n\n".join(current))

    if overlap <= 0 or len(rough_chunks) == 1:
        return rough_chunks
    
    final_chunks: List[str] = []
    for i, chunk in enumerate(rough_chunks):
        if i == 0:
            final_chunks.append(chunk)
            continue

        prev_chunk = final_chunks[-1]

        overlap_text = prev_chunk[-overlap:]
        combined = overlap_text + "\n\n" + chunk

        final_chunks.append(combined)

    return final_chunks


