"""Canonical SWOS stage-instruction assets.

Scholarly instructions belong to SWOS. Adapters may translate transport or host
formatting, but they must receive the same canonical instruction identity and
content for a given stage.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

INSTRUCTION_SET = "swos.stage-instructions.v1"


@lru_cache(maxsize=1)
def _load() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    path = root / "contracts" / "stage-instruction" / "stage-instructions-v1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("instruction_set") != INSTRUCTION_SET:
        raise RuntimeError(f"unexpected SWOS instruction set: {payload.get('instruction_set')!r}")
    if not isinstance(payload.get("instructions"), dict):
        raise RuntimeError("canonical SWOS instruction asset has no instructions object")
    return payload


def instruction_record(stage: str) -> dict[str, Any]:
    raw = _load()["instructions"].get(stage)
    if not isinstance(raw, dict):
        raise KeyError(f"unknown canonical SWOS stage instruction: {stage}")
    text = str(raw.get("text") or "").strip()
    if not text:
        raise RuntimeError(f"canonical SWOS stage instruction {stage!r} is empty")
    return {
        "instruction_set": INSTRUCTION_SET,
        "instruction_id": str(raw["instruction_id"]),
        "capability": str(raw["capability"]),
        "text": text,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def instruction_text(stage: str) -> str:
    return instruction_record(stage)["text"]
