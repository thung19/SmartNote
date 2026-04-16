import re
from dataclasses import dataclass, field
from typing import List, Tuple

# Matches markdown headers: #, ##, ###, etc.
_HEADER_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

# Splits on sentence-ending punctuation followed by whitespace
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass
class ChunkResult:
    """A chunk of text with contextual metadata."""
    text: str
    heading_breadcrumb: str = ""  # e.g. "## Architecture > ### Details"
    chunk_index: int = 0
    total_chunks: int = 0


def _split_by_headers(text: str) -> List[Tuple[str, int, str]]:
    """
    Split markdown text into (heading_line, heading_level, content) sections.
    heading_line is e.g. "## Goals", heading_level is 2.
    Non-header content before the first header gets heading_level 0.
    """
    sections: List[Tuple[str, int, str]] = []
    last_end = 0
    last_heading = ""
    last_level = 0

    for match in _HEADER_RE.finditer(text):
        if match.start() > last_end:
            content = text[last_end:match.start()].strip()
            if content:
                sections.append((last_heading, last_level, content))
        last_heading = match.group(0)
        last_level = len(match.group(1))  # number of # chars
        last_end = match.end()

    remaining = text[last_end:].strip()
    if remaining:
        sections.append((last_heading, last_level, remaining))

    return sections if sections else [("", 0, text.strip())]


def _build_breadcrumb(header_stack: List[str]) -> str:
    """Build a breadcrumb string from the current header stack."""
    return " > ".join(header_stack) if header_stack else ""


def _split_sentences(text: str) -> List[str]:
    parts = _SENTENCE_SPLIT_RE.split(text.strip())
    return [p.strip() for p in parts if p.strip()]


def _sentence_overlap(text: str, overlap_chars: int) -> str:
    """
    Return the last complete sentence(s) from text that fit within overlap_chars.
    Falls back to the last sentence if none fit cleanly.
    """
    if not text or overlap_chars <= 0:
        return ""

    sentences = _split_sentences(text)
    if not sentences:
        return text[-overlap_chars:]

    result: List[str] = []
    total = 0
    for sentence in reversed(sentences):
        needed = len(sentence) + (1 if result else 0)
        if total + needed <= overlap_chars:
            result.insert(0, sentence)
            total += needed
        else:
            break

    # Always include at least the last sentence so overlap is never empty
    if not result:
        result = [sentences[-1]]

    return " ".join(result)


def _split_into_paragraphs(text: str) -> List[str]:
    paragraphs: List[str] = []
    for part in text.split("\n\n"):
        lines = [line.strip() for line in part.strip().splitlines() if line.strip()]
        cleaned = "\n".join(lines)
        if cleaned:
            paragraphs.append(cleaned)
    return paragraphs


def chunk_text(text: str, max_chars: int = 800, overlap: int = 200) -> List[str]:
    """Backward-compatible wrapper that returns plain text chunks."""
    results = chunk_text_rich(text, max_chars=max_chars, overlap=overlap)
    return [r.text for r in results]


def chunk_text_rich(text: str, max_chars: int = 800, overlap: int = 200) -> List[ChunkResult]:
    """
    Chunk text into pieces with hierarchical header context.

    Each chunk carries a heading_breadcrumb showing its full section path,
    e.g. "## Architecture > ### Components > #### Database".
    """
    if not text:
        return []

    sections = _split_by_headers(text)
    all_chunks: List[ChunkResult] = []

    # Track header hierarchy: stack of (level, heading_line) pairs
    header_stack: List[Tuple[int, str]] = []

    for heading, level, content in sections:
        # Update header stack: pop any headers at the same or deeper level
        if heading:
            while header_stack and header_stack[-1][0] >= level:
                header_stack.pop()
            header_stack.append((level, heading))

        breadcrumb = _build_breadcrumb([h for _, h in header_stack])

        # The immediate heading is prefixed to chunk text for embedding quality
        prefix = f"{heading}\n\n" if heading else ""
        paragraphs = _split_into_paragraphs(content)

        current: List[str] = []
        current_len = len(prefix)

        for para in paragraphs:
            para_len = len(para)

            if current and current_len + para_len + 2 > max_chars:
                # Flush
                all_chunks.append(ChunkResult(
                    text=prefix + "\n\n".join(current),
                    heading_breadcrumb=breadcrumb,
                ))

                # Sentence-level overlap from flushed content
                overlap_text = _sentence_overlap("\n\n".join(current), overlap)

                if overlap_text:
                    current = [overlap_text, para]
                    current_len = len(prefix) + len(overlap_text) + 2 + para_len
                else:
                    current = [para]
                    current_len = len(prefix) + para_len
            else:
                current.append(para)
                current_len += para_len + 2

        if current:
            all_chunks.append(ChunkResult(
                text=prefix + "\n\n".join(current),
                heading_breadcrumb=breadcrumb,
            ))

    # Assign indices
    total = len(all_chunks)
    for i, chunk in enumerate(all_chunks):
        chunk.chunk_index = i
        chunk.total_chunks = total

    return all_chunks
