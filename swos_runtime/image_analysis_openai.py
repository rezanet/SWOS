"""OpenAI multimodal provider boundary for the research-grade runtime.

The implementation lives in :mod:`swos_runtime.image_analysis`; this module
keeps the provider import path explicit for integrations and capability
registries without creating a second adapter with different policy semantics.
"""

from .image_analysis import OpenAIImageAnalysisProvider as _OpenAIImageAnalysisProvider


class OpenAIImageAnalysisProvider(_OpenAIImageAnalysisProvider):
    """Registered v2 import path for the opt-in OpenAI image adapter.

    The provider-neutral module owns the shared contract and policy logic so
    callers importing either public path receive identical fail-closed
    behaviour.  Keeping this concrete registration here makes the capability
    contract's adapter path explicit without duplicating the implementation.
    """

    pass

__all__ = ["OpenAIImageAnalysisProvider"]
