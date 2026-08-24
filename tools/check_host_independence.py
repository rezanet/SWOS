"""Fail when SWOS core encodes vendor identity as scholarly validity.

This first slice targets release/gate leakage. Adapter/provider modules may mention
vendors; the orchestrator/core may not use vendor tokens as pass/fail criteria.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE_FILES = [ROOT / "swos_runtime" / "orchestrator.py"]
FORBIDDEN_GATE_PATTERNS = [
    re.compile(r"rerank_record\.get\([\"']method[\"']\)\s*!=\s*[\"']openai_", re.I),
    re.compile(r"blocking_reasons.*(?:openai|anthropic|claude|gemini|gpt-)", re.I),
]


def main() -> int:
    failures: list[str] = []
    for path in CORE_FILES:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_GATE_PATTERNS:
            match = pattern.search(text)
            if match:
                failures.append(
                    f"{path.relative_to(ROOT)} encodes vendor identity in a core validity gate: {match.group(0)!r}"
                )
    if failures:
        print("Host Independence Rule violations:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Host Independence Rule: no vendor-specific core validity gates found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
