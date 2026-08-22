"""SWOS Prose — semantic-safe prose editing primitives."""

from .pipeline import verify_rewrite
from .rewrite import polish_text

__all__ = ["verify_rewrite", "polish_text"]
__version__ = "0.3.0-dev"
