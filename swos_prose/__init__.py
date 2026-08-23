"""SWOS Prose — semantic-safe prose editing primitives."""

from .modes import SUPPORTED_MODES, SUPPORTED_PRESETS, writer_policy
from .pipeline import verify_rewrite
from .rewrite import edit_text, polish_text

__all__ = [
    "SUPPORTED_MODES",
    "SUPPORTED_PRESETS",
    "edit_text",
    "polish_text",
    "verify_rewrite",
    "writer_policy",
]
__version__ = "0.4.0-dev"
