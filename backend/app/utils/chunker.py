from typing import List


"""
Split text into paragraphs based on double newlines, cleaning up extra whitespace.
"""
def _split_into_paragraphs(text: str) -> List[str]:
    
    # Splits text into a list of paragraphs based on double newlines
    raw_parts = text.split("\n\n")

    
    paragraphs: List[str] = []
    
    #Loop through parts
    for part in raw_parts:
        # Remove leading and trailing whitespace from each part
        stripped_part = part.strip()
        # Split the stripped part into individual lines
        lines = stripped_part.splitlines()

        cleaned_lines = []
        for line in lines:
            # Strip whitespace from each line 
            stripped_line = line.strip()

            # Only keep non-empty lines.
            if stripped_line:  
                cleaned_lines.append(stripped_line)

         # Reassemble cleaned lines with a single new line between.
        cleaned = "\n".join(cleaned_lines)

        # Add cleaned paragraph to list of paragraphs if not empty
        if cleaned:
            paragraphs.append(cleaned)

    return paragraphs

# Takes long text and splits it into chunks of specified max character length with optional overlap.
def chunk_text(text: str, max_chars: int = 800, overlap: int = 200,) -> List[str]:
    # Return nothing if empty
    if not text:
        return []
    
    # Split text into paragraphs
    paragraphs = _split_into_paragraphs(text)

    rough_chunks: List[str] = []
    current: List[str] = []
    current_len = 0

    #Loop through each paragraph
    for para in paragraphs:
        para_len = len(para)
        
        # Check if adding this paragraph would exceed max_chars
        if current and current_len + para_len + 2 > max_chars:

            # If so, add the current chunk and set the new one
            rough_chunks.append("\n\n".join(current))
            current = [para]
            current_len = para_len
        else:

            # Otherwise, add paragraph to current chunk
            current.append(para)
            current_len += para_len + 2

    # Add any remaining paragraphs as the last chunk. We now have non-overlapped chunks
    if current:
        rough_chunks.append("\n\n".join(current))

    # If no overlap is needed, return the rough chunks
    if overlap <= 0 or len(rough_chunks) == 1:
        return rough_chunks
    
    final_chunks: List[str] = []
    
    #Loop through rough chunks to create overlapped chunks
    for i, chunk in enumerate(rough_chunks):

        # Add the first chunk as is
        if i == 0:
            final_chunks.append(chunk)
            continue
        
        # For subsequent chunks, add overlap from previous chunk
        # Get the last chunk added to final chunks
        prev_chunk = final_chunks[-1]

        # Get the last 'overlap' characters from the previous chunk
        overlap_text = prev_chunk[-overlap:]
        # Combine overlap with current chunk
        combined = overlap_text + "\n\n" + chunk

        # Add the combined chunk to final chuns
        final_chunks.append(combined)

    return final_chunks


