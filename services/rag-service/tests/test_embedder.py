"""Tests for embedder — runs without GCP credentials using stub fallback."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Ensure GCP not set so stub is used
os.environ.pop("GCP_PROJECT_ID", None)

from src.embeddings.embedder import embed_text, embed_batch, EMBEDDING_DIM


class TestEmbedText:
    def test_returns_correct_dimension(self):
        vec = embed_text("Hello bank")
        assert len(vec) == EMBEDDING_DIM

    def test_returns_floats(self):
        vec = embed_text("Test")
        assert all(isinstance(v, float) for v in vec)

    def test_deterministic(self):
        vec1 = embed_text("same text")
        vec2 = embed_text("same text")
        assert vec1 == vec2

    def test_different_texts_differ(self):
        vec1 = embed_text("cloud architecture")
        vec2 = embed_text("banking compliance")
        assert vec1 != vec2

    def test_normalised(self):
        vec = embed_text("normalisation check")
        norm = sum(v ** 2 for v in vec) ** 0.5
        assert abs(norm - 1.0) < 1e-6


class TestEmbedBatch:
    def test_batch_length_matches(self):
        texts = ["doc one", "doc two", "doc three"]
        vecs = embed_batch(texts)
        assert len(vecs) == len(texts)

    def test_each_vector_correct_dim(self):
        vecs = embed_batch(["a", "b"])
        for v in vecs:
            assert len(v) == EMBEDDING_DIM

    def test_empty_batch(self):
        vecs = embed_batch([])
        assert vecs == []
