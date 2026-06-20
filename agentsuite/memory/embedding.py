"""Pluggable embedding seam for semantic retrieval (Phase 6, decision AS-023).

The vector index is built behind a small :class:`Embedder` interface so the backend is a swappable
seam, not a one-way door. The shipped default — :class:`HashingEmbedder` — is **deterministic and
dependency-free** (stdlib only): it hashes lowercased word tokens into a fixed-dimension, L2-norm
vector so lexical/semantic overlap drives cosine similarity. That keeps the memory layer offline,
reproducible, and its tests exact (the project's zero-dep, local-first posture), while a real
model / ``sqlite-vec`` backend can drop in later behind the same interface (architecture
§"Storage & access" names ``sqlite-vec`` as the future backend, not the MVP).
"""

from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric word tokens — the deterministic unit of the default embedder."""
    return _TOKEN_RE.findall(text.lower())


class Embedder(ABC):
    """A text → fixed-length vector encoder. The seam every vector backend implements."""

    name: str = "embedder"
    dim: int = 0

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Return a (preferably L2-normalized) vector for ``text``."""


class HashingEmbedder(Embedder):
    """Deterministic, dependency-free embedder: feature-hashing of word tokens (hashed bag-of-words).

    Each token is hashed to a bucket in ``[0, dim)``; term frequencies accumulate there and the
    vector is L2-normalized. Same text → same vector, always (reproducible), and texts that share
    words score higher under cosine. Unsigned (positive) weighting is deliberate: for short-text
    *retrieval ranking* a genuinely shared token must always *increase* similarity, never cancel —
    signed hashing keeps inner products unbiased for ML but lets an opposite-signed collision wipe
    out a real single-token match on short documents. Good enough for useful recall over the small
    AgentSuite corpus without any model download or network call.
    """

    def __init__(self, dim: int = 1024):
        if dim <= 0:
            raise ValueError("dim must be positive")
        self.dim = dim
        self.name = f"hashing-{dim}"

    def _bucket(self, token: str) -> int:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        return int.from_bytes(digest, "big") % self.dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in tokenize(text):
            vec[self._bucket(token)] += 1.0
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            return vec
        return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity. Vectors from :class:`HashingEmbedder` are unit-norm, so this is a dot
    product; we still divide by norms to stay correct for any embedder."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


_DEFAULT: Embedder | None = None


def default_embedder() -> Embedder:
    """The process-wide default embedder (the zero-dep :class:`HashingEmbedder`)."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = HashingEmbedder()
    return _DEFAULT
