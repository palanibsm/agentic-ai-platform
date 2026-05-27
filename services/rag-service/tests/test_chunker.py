"""Tests for text chunker — pytest tests/test_chunker.py -v"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.ingestion.chunker import chunk_text


class TestChunkText:
    def test_empty_returns_empty(self):
        assert chunk_text("") == []

    def test_whitespace_returns_empty(self):
        assert chunk_text("   \n  ") == []

    def test_short_text_single_chunk(self):
        text = "This is a short document."
        chunks = chunk_text(text, chunk_size=512)
        assert len(chunks) == 1
        assert chunks[0]["text"] == text
        assert chunks[0]["chunk_index"] == 0

    def test_source_attached(self):
        chunks = chunk_text("Hello world.", source="gs://bucket/doc.txt")
        assert chunks[0]["source"] == "gs://bucket/doc.txt"

    def test_metadata_attached(self):
        meta = {"role": "admin"}
        chunks = chunk_text("Hello world.", metadata=meta)
        assert chunks[0]["metadata"] == meta

    def test_long_text_multiple_chunks(self):
        # Generate text longer than chunk_size
        sentence = "This is a test sentence. "
        text = sentence * 50   # ~1250 chars
        chunks = chunk_text(text, chunk_size=200, overlap=20)
        assert len(chunks) > 1
        # All chunks have text
        for c in chunks:
            assert c["text"].strip()
            assert "chunk_index" in c

    def test_chunk_indices_sequential(self):
        text = "Sentence one. Sentence two. Sentence three. " * 30
        chunks = chunk_text(text, chunk_size=100, overlap=10)
        indices = [c["chunk_index"] for c in chunks]
        assert indices == list(range(len(indices)))

    def test_no_chunk_exceeds_size_by_much(self):
        text = "Word " * 500
        chunks = chunk_text(text, chunk_size=100, overlap=10)
        for c in chunks:
            # Allow some slack for overlap and sentence boundary logic
            assert len(c["text"]) <= 300
