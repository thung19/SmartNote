import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# Matches markdown headers: #, ##, ###, etc.
_HEADER_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

# Fenced code blocks: opening ``` (with optional language) through closing ```
_CODE_BLOCK_RE = re.compile(r"^```[^\n]*\n.*?^```", re.MULTILINE | re.DOTALL)

# Table separator row (e.g. |---|---|)
_TABLE_SEP_RE = re.compile(r"\|[\s:]*-{2,}[\s:]*\|")

# Splits on sentence-ending punctuation followed by whitespace
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass
class ChunkResult:
    """A chunk of text with contextual metadata."""
    text: str
    heading_breadcrumb: str = ""  # e.g. "## Architecture > ### Details"
    chunk_index: int = 0
    total_chunks: int = 0
    section_id: str = ""  # parent section ID for expansion


@dataclass
class ChunkingResult:
    """Full output of the chunking pipeline."""
    chunks: List[ChunkResult]
    sections: Dict[str, str]  # section_id -> full section text (for parent expansion)


# ---------------------------------------------------------------------------
# Structure detection helpers
# ---------------------------------------------------------------------------

def _looks_like_table(text: str) -> bool:
    lines = text.strip().splitlines()
    if len(lines) < 2:
        return False
    pipe_lines = sum(1 for line in lines if "|" in line)
    has_sep = any(_TABLE_SEP_RE.search(line) for line in lines)
    return has_sep and pipe_lines >= len(lines) * 0.5


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


# ---------------------------------------------------------------------------
# Structure-aware block splitting
# ---------------------------------------------------------------------------

def _split_into_blocks(text: str) -> List[str]:
    """
    Split text into semantic blocks, keeping code fences and tables atomic.

    Code blocks (``` ... ```) are never split internally — even if they
    contain blank lines.  Tables (detected by separator rows) are kept
    as single units too.
    """
    blocks: List[str] = []
    pos = 0

    for m in _CODE_BLOCK_RE.finditer(text):
        # Plain text before this code block
        before = text[pos:m.start()]
        blocks.extend(_split_plain_text(before))
        # The code block itself — atomic
        code = m.group().strip()
        if code:
            blocks.append(code)
        pos = m.end()

    # Remaining text after the last code block
    if pos < len(text):
        blocks.extend(_split_plain_text(text[pos:]))

    return blocks


def _split_plain_text(text: str) -> List[str]:
    """Split non-code text by \\n\\n, keeping tables as atomic units."""
    result: List[str] = []
    for para in text.split("\n\n"):
        cleaned = para.strip()
        if not cleaned:
            continue
        if _looks_like_table(cleaned):
            # Keep the table exactly as-is
            result.append(cleaned)
        else:
            lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
            if lines:
                result.append("\n".join(lines))
    return result


# ---------------------------------------------------------------------------
# Sentence-level overlap
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def chunk_text(text: str, max_chars: int = 800, overlap: int = 200) -> List[str]:
    """Backward-compatible wrapper that returns plain text chunks."""
    result = chunk_text_rich(text, max_chars=max_chars, overlap=overlap)
    return [c.text for c in result.chunks]


def chunk_text_rich(
    text: str, max_chars: int = 800, overlap: int = 200
) -> ChunkingResult:
    """
    Chunk text into pieces with hierarchical header context and
    parent-section tracking.

    Each chunk carries:
    - heading_breadcrumb: full section path (e.g. "## Arch > ### DB")
    - section_id: key into ``sections`` dict for parent expansion

    Returns a ChunkingResult with both the chunks and a mapping of
    section_id -> full section text.
    """
    if not text:
        return ChunkingResult(chunks=[], sections={})

    sections = _split_by_headers(text)
    all_chunks: List[ChunkResult] = []
    sections_map: Dict[str, str] = {}

    # Track header hierarchy: stack of (level, heading_line) pairs
    header_stack: List[Tuple[int, str]] = []

    for sect_idx, (heading, level, content) in enumerate(sections):
        # Update header stack: pop any headers at the same or deeper level
        if heading:
            while header_stack and header_stack[-1][0] >= level:
                header_stack.pop()
            header_stack.append((level, heading))

        breadcrumb = _build_breadcrumb([h for _, h in header_stack])
        section_id = f"section::{sect_idx}"

        # Store full section text for parent expansion
        full_section = f"{heading}\n\n{content}" if heading else content
        sections_map[section_id] = full_section

        # The immediate heading is prefixed to chunk text for embedding quality
        prefix = f"{heading}\n\n" if heading else ""
        blocks = _split_into_blocks(content)

        current: List[str] = []
        current_len = len(prefix)

        for block in blocks:
            block_len = len(block)

            if current and current_len + block_len + 2 > max_chars:
                # Flush
                all_chunks.append(ChunkResult(
                    text=prefix + "\n\n".join(current),
                    heading_breadcrumb=breadcrumb,
                    section_id=section_id,
                ))

                # Sentence-level overlap from flushed content
                overlap_text = _sentence_overlap("\n\n".join(current), overlap)

                if overlap_text:
                    current = [overlap_text, block]
                    current_len = len(prefix) + len(overlap_text) + 2 + block_len
                else:
                    current = [block]
                    current_len = len(prefix) + block_len
            else:
                current.append(block)
                current_len += block_len + 2

        if current:
            all_chunks.append(ChunkResult(
                text=prefix + "\n\n".join(current),
                heading_breadcrumb=breadcrumb,
                section_id=section_id,
            ))

    # Assign indices
    total = len(all_chunks)
    for i, chunk in enumerate(all_chunks):
        chunk.chunk_index = i
        chunk.total_chunks = total

    return ChunkingResult(chunks=all_chunks, sections=sections_map)
