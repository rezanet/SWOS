"""Rewrite orchestration for SWOS Prose.

``polish`` remains the only user-facing mode in this milestone. A generated
candidate is released automatically only after semantic PASS. Milestone 1 adds
bounded local-span repair: a candidate with only high-confidence, machine-
actionable lexical semantic deltas may be repaired at most twice, with every
mutation mechanically span-confined and fully re-verified.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, cast

from .anchors import extract_anchors
from .diagnostics import PolishDiagnostics, diagnose_polish
from .models import RepairAttempt, VerificationResult, VerificationStatus
from .pipeline import verify_rewrite_with_repair
from .providers.base import SemanticVerifierProvider
from .providers.rewrite_base import RewriteCandidate, RewriteProvider
from .repair import RepairProvider

ASSURANCE_LEVELS = {"standard", "strict", "review"}
_DEGREE_MARKERS = (
    "somewhat",
    "slightly",
    "marginally",
    "moderately",
    "considerably",
    "substantially",
    "significantly",
    "highly",
    "strongly",
    "partly",
    "partially",
    "largely",
    "mostly",
    "nearly",
    "almost",
    "barely",
    "hardly",
)
_MODAL_MARKERS = ("may", "might", "can", "could", "should", "would", "must")


def _present_markers(source: str, markers: tuple[str, ...]) -> list[str]:
    return [m for m in markers if re.search(rf"\b{re.escape(m)}\b", source, re.IGNORECASE)]


def _semantic_force_profile(source: str) -> dict[str, list[str]]:
    return {
        "degree_markers": _present_markers(source, _DEGREE_MARKERS),
        "modal_markers": _present_markers(source, _MODAL_MARKERS),
    }


@dataclass
class PolishResult:
    source: str
    candidate: str
    final_text: str
    assurance: str
    verification: VerificationResult | None
    used_source_fallback: bool
    diagnostics_before: PolishDiagnostics | None = None
    repair_attempts: list[RepairAttempt] = field(default_factory=list)
    repair_success: bool = False
    repair_failure_reason: str | None = None
    notes: list[str] = field(default_factory=list)
    rewrite_token_usage: dict[str, int] | None = None
    rewrite_cost_estimate: float | None = None

    @property
    def safe_for_automatic_use(self) -> bool:
        if (
            not self.source.strip()
            and self.candidate == self.source
            and self.final_text == self.source
            and self.verification is None
            and not self.used_source_fallback
        ):
            return True
        if self.diagnostics_before is not None and self.diagnostics_before.no_change_recommended:
            return True
        return self.verification is not None and self.verification.status is VerificationStatus.PASS

    @property
    def verification_status(self) -> str | None:
        return self.verification.status.value if self.verification is not None else None

    @property
    def generation_skipped_by_diagnostics(self) -> bool:
        return (
            self.diagnostics_before is not None
            and self.diagnostics_before.no_change_recommended
            and self.candidate == self.source
            and self.rewrite_token_usage is None
        )

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
            "diagnostics_before": self.diagnostics_before.to_dict()
            if self.diagnostics_before is not None
            else None,
            "generation_skipped_by_diagnostics": self.generation_skipped_by_diagnostics,
            "repair_attempts": [attempt.to_dict() for attempt in self.repair_attempts],
            "repair_success": self.repair_success,
            "repair_failure_reason": self.repair_failure_reason,
            "notes": self.notes,
            "rewrite_token_usage": self.rewrite_token_usage,
            "rewrite_cost_estimate": self.rewrite_cost_estimate,
        }


def _polish_plan(source: str) -> dict[str, Any]:
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
            "degree and scalar force",
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
            "degree-to-modality substitution",
            "modal-force substitution",
            "ambiguity resolution by guess",
        ],
        "semantic_force_profile": _semantic_force_profile(source),
    }


def _implicit_repair_provider(rewrite_provider: RewriteProvider) -> RepairProvider | None:
    return (
        cast(RepairProvider, rewrite_provider)
        if callable(getattr(rewrite_provider, "repair", None))
        else None
    )


def polish_text(
    *,
    source: str,
    rewrite_provider: RewriteProvider,
    verifier_provider: SemanticVerifierProvider | None,
    assurance: str = "strict",
    native_swos_context: dict | None = None,
    context_before: str | None = None,
    context_after: str | None = None,
    run_diagnostics: bool = True,
    repair_provider: RepairProvider | None = None,
) -> PolishResult:
    """Diagnose, generate, verify, optionally repair locally, and fail safe."""
    if assurance not in ASSURANCE_LEVELS:
        raise ValueError(f"Unknown assurance level: {assurance}")
    if not isinstance(source, str):
        raise TypeError("source must be a string")
    if not isinstance(run_diagnostics, bool):
        raise TypeError("run_diagnostics must be a boolean")
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

    diagnostics_before = (
        diagnose_polish(
            source,
            context_before=context_before,
            context_after=context_after,
        )
        if run_diagnostics
        else None
    )
    if diagnostics_before is not None and diagnostics_before.no_change_recommended:
        return PolishResult(
            source=source,
            candidate=source,
            final_text=source,
            assurance=assurance,
            verification=None,
            used_source_fallback=False,
            diagnostics_before=diagnostics_before,
            notes=[
                "Pre-generation diagnostics found positive evidence for a narrow already-good prose shape; generation and semantic verification were skipped."
            ],
        )

    protected_anchors = [a.to_dict() for a in extract_anchors(source) if a.protected]
    try:
        proposal = rewrite_provider.rewrite(
            source=source,
            mode="polish",
            protected_anchors=protected_anchors,
            rewrite_plan=_polish_plan(source),
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
            diagnostics_before=diagnostics_before,
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
            diagnostics_before=diagnostics_before,
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
            diagnostics_before=diagnostics_before,
            notes=["Rewrite provider returned a non-string candidate; source preserved."],
        )

    execution = verify_rewrite_with_repair(
        source=source,
        candidate=candidate,
        assurance=assurance,
        verifier_provider=verifier_provider,
        repair_provider=repair_provider or _implicit_repair_provider(rewrite_provider),
        native_swos_context=native_swos_context,
    )
    verification, verified_candidate = execution.verification, execution.candidate
    if verification.verifier_skip_reason == "terminal_newline_only":
        final_text, used_source_fallback = source, False
        decision_note = "Candidate differed only by terminal line-ending whitespace; the original source representation was preserved."
    elif verification.status is VerificationStatus.PASS:
        final_text, used_source_fallback = verified_candidate, False
        decision_note = (
            "Bounded repair succeeded and the repaired candidate passed semantic re-verification."
            if execution.success
            else "Candidate passed semantic verification and is safe for automatic use."
        )
    else:
        final_text, used_source_fallback = source, True
        suffix = f" Repair detail: {execution.failure_reason}" if execution.failure_reason else ""
        decision_note = f"Candidate verification returned {verification.status.value}; the original source was preserved.{suffix}"

    repair_provider_notes = [
        note for attempt in execution.attempts for note in attempt.provider_notes
    ]
    return PolishResult(
        source=source,
        candidate=verified_candidate,
        final_text=final_text,
        assurance=assurance,
        verification=verification,
        used_source_fallback=used_source_fallback,
        diagnostics_before=diagnostics_before,
        repair_attempts=execution.attempts,
        repair_success=execution.success,
        repair_failure_reason=execution.failure_reason,
        notes=[*proposal.notes, *repair_provider_notes, decision_note],
        rewrite_token_usage=proposal.token_usage,
        rewrite_cost_estimate=proposal.cost_estimate,
    )
