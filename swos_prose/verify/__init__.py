"""Verification primitives for SWOS Prose."""

from .classify import classify_deltas
from .deterministic import deterministic_deltas

__all__ = ["classify_deltas", "deterministic_deltas"]
