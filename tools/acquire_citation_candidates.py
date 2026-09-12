#!/usr/bin/env python3
"""CLI entry point for the pre-annotation citation candidate acquisition workflow."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from swos_runtime.citation_acquisition import main  # noqa: E402, I001


if __name__ == "__main__":
    raise SystemExit(main())
