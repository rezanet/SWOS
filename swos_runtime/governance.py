"""Deterministic governance primitives for Autonomous SWOS."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .capabilities import capability_satisfied
from .models import SourceRecord

INJECTION_PATTERNS = (
    r"\bignore (?:all |the )?(?:previous|prior) instructions?\b",
    r"\bsystem (?:message|note|instruction)\b",
    r"\bskip (?:citation|source|evidence) verification\b",
    r"\bdo not report (?:this|the instruction)\b",
    r"\bmark (?:all|them) as (?:verified|directly supporting)\b",
    r"\byou are (?:chatgpt|an? ai|the assistant)\b",
)

VALID_FINAL_STATUSES = {"APPROVED", "REVIEW_REQUIRED", "BLOCKED", "FAILED"}


def detect_prompt_injection(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in INJECTION_PATTERNS)


def exact_quote_supported(quote: str, source: SourceRecord) -> bool:
    """Evidence spans must actually occur in the retrieved source."""
    if not quote or len(quote.strip()) < 12:
        return False

    def normal(value: str) -> str:
        return " ".join(value.split()).strip()

    return normal(quote) in normal(source.text)


def citation_markers(article: str) -> list[str]:
    return re.findall(r"\[(S\d+)\]", article)


def article_body(article: str) -> str:
    marker = re.search(r"(?im)^\s*##\s+References\s*$", article)
    return article[: marker.start()] if marker else article


def body_word_count(article: str) -> int:
    return len(re.findall(r"\b[\w’'-]+\b", article_body(article)))


def cross_encoder_executed(record: dict[str, Any]) -> bool:
    """Return whether the SWOS semantic-rerank capability contract was satisfied.

    Core governance never checks a provider method or vendor identity. Replay
    adapters are responsible for normalising historical implementation records
    into current SWOS capability evidence before governance sees them.
    """
    return isinstance(record, dict) and capability_satisfied(record, "semantic_rerank")


class IntegrityChain:
    """Append-only hash chain for material runtime events."""

    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    def append(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        previous = self.entries[-1]["hash"] if self.entries else "GENESIS"
        material = {
            "sequence": len(self.entries) + 1,
            "event_type": event_type,
            "payload": payload,
            "previous_hash": previous,
        }
        digest = hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        entry = {**material, "hash": digest}
        self.entries.append(entry)
        return entry

    def verify(self) -> bool:
        previous = "GENESIS"
        for expected_sequence, entry in enumerate(self.entries, start=1):
            material = {
                "sequence": entry.get("sequence"),
                "event_type": entry.get("event_type"),
                "payload": entry.get("payload"),
                "previous_hash": entry.get("previous_hash"),
            }
            digest = hashlib.sha256(
                json.dumps(
                    material, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                ).encode()
            ).hexdigest()
            if (
                entry.get("sequence") != expected_sequence
                or entry.get("previous_hash") != previous
                or entry.get("hash") != digest
            ):
                return False
            previous = digest
        return True

    def write(self, path: Path) -> None:
        path.write_text(
            "".join(json.dumps(entry, sort_keys=True) + "\n" for entry in self.entries),
            encoding="utf-8",
        )


def can_write_durable_rpm(
    *,
    source_grounded: bool,
    epg_refs: list[str],
    sdl_id: str | None,
    human_approver: str | None,
) -> bool:
    """Frozen RPM governance requires provenance plus human approval for durable writes."""
    return bool(source_grounded and epg_refs and sdl_id and human_approver)


def canonical_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_manifest(output_dir: Path, manifest: dict[str, Any]) -> bool:
    files = manifest.get("files", {})
    if not isinstance(files, dict) or not files:
        return False
    for rel, expected in files.items():
        path = output_dir / rel
        if not path.is_file() or canonical_sha256(path) != expected:
            return False
    return True
