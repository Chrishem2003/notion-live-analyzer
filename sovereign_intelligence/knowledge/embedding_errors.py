class EmbeddingProviderError(Exception):
    """Base exception for embedding-provider failures."""


class EmbeddingConfigurationError(
    EmbeddingProviderError
):
    """Raised when a provider is incorrectly configured."""


class EmbeddingRequestError(
    EmbeddingProviderError
):
    """Raised when an embedding request fails."""


class EmbeddingDimensionError(
    EmbeddingProviderError
):
    """Raised when vectors have incompatible dimensions."""
