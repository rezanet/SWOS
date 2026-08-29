"""Explicit cross-encoder reranking for public-source retrieval."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

from .models import SourceRecord

DEFAULT_CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class RerankingError(RuntimeError):
    """Raised when cross-encoder execution cannot produce trustworthy scores."""


class CrossEncoderReranker:
    """Score each query-document pair with a declared cross-encoder model."""

    def __init__(self, *, model: Any | None = None, model_name: str = DEFAULT_CROSS_ENCODER_MODEL):
        self.model_name = model_name
        self._model = model

    def _load_model(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError as exc:
                raise RerankingError(
                    "cross-encoder reranking requires the optional 'retrieval' dependency"
                ) from exc
            self._model = CrossEncoder(self.model_name)
        return self._model

    def rerank(
        self, query: str, sources: list[SourceRecord], *, top_k: int = 10
    ) -> tuple[list[SourceRecord], dict[str, Any]]:
        if not sources:
            return [], {
                "implementation": "sentence-transformers.CrossEncoder",
                "reranker_model": self.model_name,
                "scores": {},
            }
        pairs = [(query, source.text) for source in sources]
        raw_scores = self._load_model().predict(pairs)
        if not isinstance(raw_scores, Sequence) and not hasattr(raw_scores, "__len__"):
            raise RerankingError("cross-encoder returned a non-sequence score result")
        if len(raw_scores) != len(sources):
            raise RerankingError("cross-encoder score count does not match source count")

        scores: list[float] = []
        for raw_score in raw_scores:
            if isinstance(raw_score, (bool, str, bytes, complex)):
                raise RerankingError("cross-encoder scores must be finite numbers")
            try:
                score = float(raw_score)
            except (TypeError, ValueError, OverflowError) as exc:
                raise RerankingError("cross-encoder scores must be finite numbers") from exc
            if not math.isfinite(score):
                raise RerankingError("cross-encoder scores must be finite numbers")
            scores.append(score)

        scored = []
        for index, (source, score) in enumerate(zip(sources, scores, strict=True)):
            source.rerank_score = score
            scored.append((score, index, source))
        scored.sort(key=lambda item: (-item[0], item[1]))
        ranked = [item[2] for item in scored[: max(0, top_k)]]
        evidence = {
            "implementation": "sentence-transformers.CrossEncoder",
            "reranker_model": self.model_name,
            "scores": {
                source.source_id: score for source, score in zip(sources, scores, strict=True)
            },
        }
        return ranked, evidence
