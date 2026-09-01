from .documents import (
    read_text_document,
    chunk_text,
)

from .retrieval import retrieve

from .evidence import (
    EvidenceItem,
    EvidenceManager,
)

from .semantic import (
    cosine_similarity,
    semantic_score,
)

from .hybrid import (
    HybridRetriever,
    RankedEvidence,
)

from .embeddings import (
    EmbeddingProvider as LegacyEmbeddingProvider,
    NullEmbeddingProvider,
)

from .embedding_provider import (
    EmbeddingProvider,
    EmbeddingResult,
    EmbeddingError,
)

from .embedding_deterministic import (
    DeterministicEmbeddingProvider,
)

from .embedding_registry import (
    EmbeddingRegistry,
)

from .embedding_service import (
    EmbeddingService,
)

from .vector_index import (
    PersistentVectorIndex,
)

from .indexing import (
    index_directory,
)


__all__ = [
    "read_text_document",
    "chunk_text",
    "retrieve",
    "EvidenceItem",
    "EvidenceManager",
    "cosine_similarity",
    "semantic_score",
    "HybridRetriever",
    "RankedEvidence",
    "LegacyEmbeddingProvider",
    "NullEmbeddingProvider",
    "EmbeddingProvider",
    "EmbeddingResult",
    "EmbeddingError",
    "DeterministicEmbeddingProvider",
    "EmbeddingRegistry",
    "EmbeddingService",
    "PersistentVectorIndex",
    "index_directory",
]
