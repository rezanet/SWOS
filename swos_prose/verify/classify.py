"""Decision classification for SWOS Prose verification results."""

from __future__ import annotations

from ..models import SemanticDelta, Severity, VerificationStatus


def classify_deltas(deltas: list[SemanticDelta]) -> VerificationStatus:
    nonrepairable_blocker = any(
        delta.severity is Severity.BLOCKER and not delta.repairable for delta in deltas
    )
    if nonrepairable_blocker:
        return VerificationStatus.REJECT

    repairable_blocker = any(
        delta.severity is Severity.BLOCKER and delta.repairable for delta in deltas
    )
    if repairable_blocker:
        return VerificationStatus.REPAIR

    if any(delta.severity is Severity.WARNING for delta in deltas):
        return VerificationStatus.REVIEW

    return VerificationStatus.PASS
