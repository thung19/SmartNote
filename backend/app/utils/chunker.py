import re
from typing import List, Tuple

# Matches markdown headers: #, ##, ###, etc.
_HEADER_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

# Splits on sentence-ending punctuation followed by whitespace
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _split_by_headers(text: str) -> List[Tuple[str, str]]:
    """
    Split markdown text into (heading, content) sections.
    heading is the full header line, e.g. "## Goals".
    Non-header content before the first header gets an empty heading.
    """
    sections: List[Tuple[str, str]] = []
    last_end = 0
    last_heading = ""

    for match in _HEADER_RE.finditer(text):
        if match.start() > last_end:
            content = text[last_end:match.start()].strip()
            if content:
                sections.append((last_heading, content))
        last_heading = match.group(0)
        last_end = match.end()

    remaining = text[last_end:].strip()
    if remaining:
        sections.append((last_heading, remaining))

    return sections if sections else [("", text.strip())]


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
    if not text:
        return []

    sections = _split_by_headers(text)
    all_chunks: List[str] = []

    for heading, content in sections:
        prefix = f"{heading}\n\n" if heading else ""
        paragraphs = _split_into_paragraphs(content)

        current: List[str] = []
        current_len = len(prefix)

        for para in paragraphs:
            para_len = len(para)

            if current and current_len + para_len + 2 > max_chars:
                # Flush
                all_chunks.append(prefix + "\n\n".join(current))

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
            all_chunks.append(prefix + "\n\n".join(current))

    return all_chunks
