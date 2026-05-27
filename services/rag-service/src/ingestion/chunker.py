"""
Text chunker — splits documents into overlapping chunks for embedding.
Strategy: fixed-size with overlap, respecting sentence boundaries where possible.
"""

import re


def chunk_text(
    text: str,
    chunk_size: int = 512,
    overlap: int = 64,
    source: str = "",
    metadata: dict | None = None,
) -> list[dict]:
    """
    Split text into overlapping chunks.

    Returns list of dicts:
      {
        "text": str,
        "chunk_index": int,
        "source": str,
        "char_start": int,
        "char_end": int,
        "metadata": dict,
      }
    """
    metadata = metadata or {}
    text = text.strip()
    if not text:
        return []

    # Split on sentence boundaries first for cleaner chunks
    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks: list[dict] = []
    current = ""
    current_start = 0
    char_pos = 0
    chunk_idx = 0

    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= chunk_size:
            current += (" " if current else "") + sentence
        else:
            if current:
                chunks.append({
                    "text": current,
                    "chunk_index": chunk_idx,
                    "source": source,
                    "char_start": current_start,
                    "char_end": current_start + len(current),
                    "metadata": metadata,
                })
                chunk_idx += 1
                # Overlap: keep last `overlap` chars as context
                overlap_text = current[-overlap:] if len(current) > overlap else current
                current = overlap_text + " " + sentence
                current_start = current_start + len(current) - len(overlap_text)
            else:
                # Single sentence longer than chunk_size — hard split
                for i in range(0, len(sentence), chunk_size - overlap):
                    part = sentence[i : i + chunk_size]
                    chunks.append({
                        "text": part,
                        "chunk_index": chunk_idx,
                        "source": source,
                        "char_start": char_pos + i,
                        "char_end": char_pos + i + len(part),
                        "metadata": metadata,
                    })
                    chunk_idx += 1
                current = ""

        char_pos += len(sentence) + 1

    if current.strip():
        chunks.append({
            "text": current,
            "chunk_index": chunk_idx,
            "source": source,
            "char_start": current_start,
            "char_end": current_start + len(current),
            "metadata": metadata,
        })

    return chunks
