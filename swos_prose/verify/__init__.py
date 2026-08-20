"""Verification primitives for SWOS Prose."""

from .classify import classify_deltas
from .deterministic import deterministic_deltas
from .propositions import deltas_from_proposition_report

__all__ = [
    "classify_deltas",
    "deterministic_deltas",
    "deltas_from_proposition_report",
]
