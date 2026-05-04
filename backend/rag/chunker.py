import re
from typing import List


CHUNK_SIZE    = 400   # characters per chunk
CHUNK_OVERLAP = 80    # overlap to preserve context across boundaries


def chunk_text(text: str, filename: str) -> List[dict]:
    """
    Split text into overlapping chunks with metadata.
    Returns a list of {content, metadata} dicts.
    """
    text   = _clean(text)
    chunks = _split(text)

    return [
        {
            "content":  chunk,
            "metadata": {"filename": filename, "chunk_index": i, "total_chunks": len(chunks)},
        }
        for i, chunk in enumerate(chunks)
    ]


def _clean(text: str) -> str:
    """Normalize whitespace while preserving paragraph breaks."""
    text = re.sub(r'\r\n|\r', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def _split(text: str) -> List[str]:
    """Sliding-window split that tries to break on sentence/paragraph boundaries."""
    if len(text) <= CHUNK_SIZE:
        return [text]

    chunks   = []
    start    = 0

    while start < len(text):
        end = start + CHUNK_SIZE

        if end >= len(text):
            chunks.append(text[start:].strip())
            break

        # Prefer splitting at paragraph, then sentence, then space
        split_at = (
            _last_index(text, '\n\n', start, end) or
            _last_index(text, '. ',   start, end) or
            _last_index(text, ' ',    start, end) or
            end
        )

        chunks.append(text[start:split_at].strip())
        new_start = split_at - CHUNK_OVERLAP
        # Always advance forward to prevent infinite loop
        start = new_start if new_start > start else start + (CHUNK_SIZE - CHUNK_OVERLAP)

    return [c for c in chunks if c]


def _last_index(text: str, sep: str, start: int, end: int):
    """Return the rightmost occurrence of sep within [start, end], or None."""
    idx = text.rfind(sep, start, end)
    return (idx + len(sep)) if idx != -1 else None
