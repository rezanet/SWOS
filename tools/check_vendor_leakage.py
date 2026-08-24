#!/usr/bin/env python3
"""Architectural lint: vendor identity must not leak into SWOS scholarly core modules."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# These roots are architectural authority zones. Executable/configuration files in
# them must remain vendor-neutral. Markdown is intentionally excluded because
# governance documents may discuss providers when defining portability policy.
FORBIDDEN_ROOTS = {
    "core",
    "governance",
    "schemas",
    "state",
    "evidence",
    "argument",
    "audit",
}
FORBIDDEN_SUFFIXES = {".py", ".json", ".yaml", ".yml", ".toml"}

# The current v2 core is still physically grouped under swos_runtime. These files
# are treated exactly like a future core/ package until the repository layout is
# split further.
CURRENT_CORE_FILES = {
    Path("swos_runtime/orchestrator.py"),
    Path("swos_runtime/finalizer.py"),
    Path("swos_runtime/governance.py"),
    Path("swos_runtime/work_orders.py"),
    Path("swos_runtime/broker.py"),
    Path("swos_runtime/capabilities.py"),
    Path("swos_runtime/models.py"),
    Path("swos_runtime/schema_validation.py"),
    Path("swos_runtime/instructions.py"),
}

VENDOR_PATTERNS = {
    "OpenAI": re.compile(r"\bOpenAI\b", re.IGNORECASE),
    "Anthropic": re.compile(r"\bAnthropic\b", re.IGNORECASE),
    "Claude": re.compile(r"\bClaude\b", re.IGNORECASE),
    "Gemini": re.compile(r"\bGemini\b", re.IGNORECASE),
    "GPT model family": re.compile(r"\bGPT-[A-Za-z0-9._-]+\b", re.IGNORECASE),
    "OPENAI_API_KEY": re.compile(r"\bOPENAI_API_KEY\b"),
    "ANTHROPIC_API_KEY": re.compile(r"\bANTHROPIC_API_KEY\b"),
    "Responses API call": re.compile(r"\bresponses\.create\b", re.IGNORECASE),
}


def _is_forbidden(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if relative in CURRENT_CORE_FILES:
        return True
    if path.suffix.lower() not in FORBIDDEN_SUFFIXES:
        return False
    return any(part in FORBIDDEN_ROOTS for part in relative.parts[:-1])


def main() -> int:
    failures: list[str] = []
    checked = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or not _is_forbidden(path):
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        for label, pattern in VENDOR_PATTERNS.items():
            match = pattern.search(text)
            if match:
                line = text.count("\n", 0, match.start()) + 1
                failures.append(
                    f"{path.relative_to(ROOT)}:{line}: vendor leakage [{label}] {match.group(0)!r}"
                )

    if failures:
        print("SWOS VENDOR LEAKAGE GATE: FAIL")
        for failure in failures:
            print(f"- {failure}")
        print(
            "Vendor-specific implementation belongs behind adapters; scholarly core validity may only name SWOS capabilities and contracts."
        )
        return 1

    print(f"SWOS VENDOR LEAKAGE GATE: PASS ({checked} authority files checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
