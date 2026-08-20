"""Milestone 2 rewrite orchestration for SWOS Prose.

This first vertical slice implements only ``polish`` and deliberately has no
repair loop. A generated candidate is returned automatically only when the
existing semantic verifier returns PASS; every other outcome falls back to the
source text.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .anchors import extract_anchors
from .models import VerificationResult, VerificationStatus
from .pipeline import verify_rewrite
from .providers.base import SemanticVerifierProvider
from .providers.rewrite_base import RewriteCandidate, RewriteProvider

ASSURANCE_LEVELS = {"standard", "strict", "review"}


@dataclass
class PolishResult:
    source: str
    candidate: str
    final_text: str
    assurance: str
    verification: VerificationResult | None
    used_source_fallback: bool
    notes: list[str] = field(default_factory=list)
    rewrite_token_usage: dict[str, int] | None = None
    rewrite_cost_estimate: float | None = None

    @property
    def safe_for_automatic_use(self) -> bool:
        return self.verification is not None and self.verification.status is VerificationStatus.PASS

    @property
    def verification_status(self) -> str | None:
        return self.verification.status.value if self.verification is not None else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": "polish",
            "assurance": self.assurance,
            "source": self.source,
            "candidate": self.candidate,
            "final_text": self.final_text,
            "used_source_fallback": self.used_source_fallback,
            "safe_for_automatic_use": self.safe_for_automatic_use,
            "verification_status": self.verification_status,
            "verification": self.verification.to_dict() if self.verification is not None else None,
            "notes": self.notes,
            "rewrite_token_usage": self.rewrite_token_usage,
            "rewrite_cost_estimate": self.rewrite_cost_estimate,
        }


def _polish_plan() -> dict[str, Any]:
    return {
        "mode": "polish",
        "objectives": [
            "improve clarity and sentence construction",
            "reduce unnecessary repetition and wordiness",
            "improve local flow and natural readability",
        ],
        "must_preserve": [
            "material propositions",
            "attribution",
            "uncertainty and modality",
            "negation",
            "causal force",
            "scope and quantifiers",
            "chronology, conditions, and exceptions",
            "epistemic status and normative stance",
            "protected anchors verbatim",
        ],
        "forbidden": [
            "new factual claims",
            "new examples or explanations",
            "new citations or evidence",
            "certainty strengthening",
            "causal strengthening",
            "ambiguity resolution by guess",
        ],
    }


def polish_text(
    *,
    source: str,
    rewrite_provider: RewriteProvider,
    verifier_provider: SemanticVerifierProvider | None,
    assurance: str = "strict",
    native_swos_context: dict | None = None,
    context_before: str | None = None,
    context_after: str | None = None,
) -> PolishResult:
    """Generate one polish candidate, verify it, and fail back to source.

    No repair loop exists in this slice. Therefore REPAIR, REVIEW and REJECT are
    all non-releasable outcomes and return the original source as ``final_text``.
    """
    if assurance not in ASSURANCE_LEVELS:
        raise ValueError(f"Unknown assurance level: {assurance}")
    if not isinstance(source, str):
        raise TypeError("source must be a string")
    if not source.strip():
        return PolishResult(
            source=source,
            candidate=source,
            final_text=source,
            assurance=assurance,
            verification=None,
            used_source_fallback=False,
            notes=["No source prose supplied; no change recommended."],
        )

    protected_anchors = [anchor.to_dict() for anchor in extract_anchors(source) if anchor.protected]

    try:
        proposal = rewrite_provider.rewrite(
            source=source,
            mode="polish",
            protected_anchors=protected_anchors,
            rewrite_plan=_polish_plan(),
            context_before=context_before,
            context_after=context_after,
        )
    except (TypeError, ValueError, RuntimeError) as exc:
        return PolishResult(
            source=source,
            candidate=source,
            final_text=source,
            assurance=assurance,
            verification=None,
            used_source_fallback=True,
            notes=[f"Rewrite provider failed; source preserved: {exc}"],
        )

    if not isinstance(proposal, RewriteCandidate):
        return PolishResult(
            source=source,
            candidate=source,
            final_text=source,
            assurance=assurance,
            verification=None,
            used_source_fallback=True,
            notes=["Rewrite provider returned a malformed result object; source preserved."],
        )

    candidate = proposal.candidate_text
    if not isinstance(candidate, str):
        return PolishResult(
            source=source,
            candidate=source,
            final_text=source,
            assurance=assurance,
            verification=None,
            used_source_fallback=True,
            notes=["Rewrite provider returned a non-string candidate; source preserved."],
        )

    verification = verify_rewrite(
        source=source,
        candidate=candidate,
        assurance=assurance,
        verifier_provider=verifier_provider,
        native_swos_context=native_swos_context,
    )

    if verification.status is VerificationStatus.PASS:
        final_text = candidate
        used_source_fallback = False
        decision_note = "Candidate passed semantic verification and is safe for automatic use."
    else:
        final_text = source
        used_source_fallback = True
        decision_note = (
            f"Candidate verification returned {verification.status.value}; "
            "repair is not implemented in this slice, so the source was preserved."
        )

    return PolishResult(
        source=source,
        candidate=candidate,
        final_text=final_text,
        assurance=assurance,
        verification=verification,
        used_source_fallback=used_source_fallback,
        notes=[*proposal.notes, decision_note],
        rewrite_token_usage=proposal.token_usage,
        rewrite_cost_estimate=proposal.cost_estimate,
    )
