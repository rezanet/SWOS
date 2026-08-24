"""Enforce the SWOS Host Independence Rule in executable architecture."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE_NAMES = [
    "orchestrator.py",
    "finalizer.py",
    "governance.py",
    "work_orders.py",
    "broker.py",
    "capabilities.py",
    "models.py",
    "schema_validation.py",
    "instructions.py",
]
CORE_FILES = [ROOT / "swos_runtime" / name for name in CORE_NAMES]
ADAPTER_FILES = [
    ROOT / "swos_runtime" / "llm.py",
    ROOT / "swos_runtime" / "adapter_factory.py",
    ROOT / "swos_runtime" / "host_bundle.py",
]
VENDOR_TOKENS = re.compile(
    r"\b(?:OpenAI|Anthropic|Claude|Gemini|GPT-[0-9]|OpenAIStageProvider)\b|openai_",
    re.I,
)
VENDOR_GATE = re.compile(
    r"(?:if|unless|blocking|require|gate).{0,160}(?:openai|anthropic|claude|gemini|gpt-)",
    re.I | re.S,
)
INLINE_SWOS_PROMPT = re.compile(r"(?:You are|Act as) the SWOS", re.I)
BLINDNESS_INFERENCE = re.compile(
    r"blind_review\s*[=:].{0,160}independence|independence.{0,160}blind_review\s*[=:]",
    re.I | re.S,
)


def main() -> int:
    failures: list[str] = []

    for path in CORE_FILES:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        vendor = VENDOR_TOKENS.search(text)
        if vendor:
            failures.append(
                f"{path.relative_to(ROOT)} contains vendor identity in SWOS core: {vendor.group(0)!r}"
            )
        gate = VENDOR_GATE.search(text)
        if gate:
            failures.append(
                f"{path.relative_to(ROOT)} contains a vendor-sensitive validity gate: {gate.group(0)!r}"
            )
        blind = BLINDNESS_INFERENCE.search(text)
        if blind:
            failures.append(
                f"{path.relative_to(ROOT)} infers blind review instead of reading an explicit assurance declaration"
            )

    orchestrator = ROOT / "swos_runtime" / "orchestrator.py"
    if orchestrator.is_file():
        text = orchestrator.read_text(encoding="utf-8")
        if "CapabilityBroker" not in text:
            failures.append("core orchestrator does not depend on CapabilityBroker")
        if "from .llm" in text or "adapter_factory" in text:
            failures.append("core orchestrator imports an adapter/provider layer directly")

    llm = ROOT / "swos_runtime" / "llm.py"
    if llm.is_file():
        text = llm.read_text(encoding="utf-8")
        if INLINE_SWOS_PROMPT.search(text):
            failures.append("OpenAI adapter contains canonical SWOS scholarly prompt text")
        if "instruction_text" not in text:
            failures.append("OpenAI adapter does not consume canonical SWOS stage instructions")

    host_bundle = ROOT / "swos_runtime" / "host_bundle.py"
    if host_bundle.is_file():
        text = host_bundle.read_text(encoding="utf-8")
        if "replay_interchange_debug_reproducibility" not in text:
            failures.append("host bundle is not explicitly demoted to replay/interchange/debug/reproducibility")

    for path in ADAPTER_FILES:
        if path.is_file() and path.name != "llm.py":
            # Adapter files may mention vendors; they still must not redefine
            # scholarly personas/instructions.
            text = path.read_text(encoding="utf-8")
            if INLINE_SWOS_PROMPT.search(text):
                failures.append(
                    f"{path.relative_to(ROOT)} contains SWOS scholarly prompt text that belongs in canonical instructions"
                )

    if failures:
        print("Host Independence Rule violations:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Host Independence Rule: core is vendor-neutral; instructions and review assurance are SWOS-owned.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
